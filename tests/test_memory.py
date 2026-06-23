"""Memory Runtime Access Layer 测试（见 ADR 0012 Layer 1）。

运行：uv run python -m tests.test_memory
覆盖：
  1. Runtime scope：经 Service write/read/search（进程内 scratchpad）
  2. Knowledge scope：只读检索 KnowledgeService（get by id / search by text+type），不另存
  3. Experience scope：只读检索 ExperienceStore（get / list by agent/type/entity_id），不 append
  4. 只读 scope 拒写：KNOWLEDGE / EXPERIENCE write 抛 PermissionError
  5. 经 MemoryTool（action 派发）访问三层；read/search/write
  6. 经 AgentContext 授权访问：唯一通道 + 未授权 PermissionError；EXPERIENCE 经 Tool 写被拒（ok=False）
"""

from __future__ import annotations

from shanhai_agent_runtime.context import AgentContext
from shanhai_agent_runtime.memory import InMemoryMemory
from shanhai_experience import (
    ExperienceEvent,
    ExperienceEventType,
    ExperienceRefs,
    InMemoryExperienceStore,
)
from shanhai_tools.registry import ToolRegistry
from shanhai_wiki_engine import Entity, EntityType, KnowledgeService

from shanhai_memory import (
    ExperienceReadAdapter,
    KnowledgeReadAdapter,
    MemoryQuery,
    MemoryScope,
    MemoryService,
    MemoryTool,
    RuntimeMemoryAdapter,
)


def _knowledge() -> KnowledgeService:
    return KnowledgeService(
        [
            Entity(id="company:贵州茅台", type=EntityType.COMPANY, name="贵州茅台", aliases=["茅台"]),
            Entity(id="industry:白酒", type=EntityType.INDUSTRY, name="白酒"),
        ]
    )


def _experience() -> InMemoryExperienceStore:
    store = InMemoryExperienceStore()
    store.append(
        ExperienceEvent(
            event_id="d1",
            episode_id="ep-1",
            agent="research",
            type=ExperienceEventType.DECISION,
            refs=ExperienceRefs(entity_ids=["company:贵州茅台"], run_id="run-1"),
        )
    )
    store.append(
        ExperienceEvent(
            event_id="o1",
            episode_id="ep-1",
            agent="research",
            type=ExperienceEventType.OUTCOME,
            refs=ExperienceRefs(entity_ids=["company:贵州茅台"], parent_event_id="d1"),
        )
    )
    return store


def _service() -> MemoryService:
    return MemoryService(
        runtime=RuntimeMemoryAdapter(InMemoryMemory()),
        knowledge=KnowledgeReadAdapter(_knowledge()),
        experience=ExperienceReadAdapter(_experience()),
    )


def test_runtime_scope() -> None:
    svc = _service()
    rec = svc.write(MemoryScope.RUNTIME, "draft", {"step": 1})
    assert rec.scope == MemoryScope.RUNTIME

    got = svc.read(MemoryScope.RUNTIME, "draft")
    assert got is not None and got.content == {"step": 1}
    assert svc.read(MemoryScope.RUNTIME, "missing") is None

    found = svc.search(MemoryQuery(scope=MemoryScope.RUNTIME))
    assert any(r.key == "draft" for r in found)
    print("[OK] Runtime scope write/read/search")


def test_knowledge_scope_readonly_search() -> None:
    svc = _service()
    got = svc.read(MemoryScope.KNOWLEDGE, "company:贵州茅台")
    assert got is not None
    assert isinstance(got.content, Entity) and got.content.name == "贵州茅台"

    # 别名命中 + 类型过滤
    hits = svc.search(MemoryQuery(scope=MemoryScope.KNOWLEDGE, text="茅台", type="company"))
    assert {r.key for r in hits} == {"company:贵州茅台"}
    # 类型过滤排除
    assert svc.search(MemoryQuery(scope=MemoryScope.KNOWLEDGE, text="茅台", type="industry")) == []
    print("[OK] Knowledge scope 只读检索（id / text+type）")


def test_experience_scope_readonly_search() -> None:
    svc = _service()
    got = svc.read(MemoryScope.EXPERIENCE, "d1")
    assert got is not None and isinstance(got.content, ExperienceEvent)

    # 按 agent + entity_id（text 解释为 entity_id）
    by_entity = svc.search(
        MemoryQuery(scope=MemoryScope.EXPERIENCE, agent="research", text="company:贵州茅台")
    )
    assert {r.key for r in by_entity} == {"d1", "o1"}
    # 按 type 过滤
    decisions = svc.search(MemoryQuery(scope=MemoryScope.EXPERIENCE, type="decision"))
    assert {r.key for r in decisions} == {"d1"}
    print("[OK] Experience scope 只读检索（id / agent+entity_id / type）")


def test_readonly_scopes_reject_write() -> None:
    svc = _service()
    for scope in (MemoryScope.KNOWLEDGE, MemoryScope.EXPERIENCE):
        try:
            svc.write(scope, "x", {})
            raise AssertionError(f"{scope} 应拒绝写入")
        except PermissionError:
            pass
    print("[OK] 只读 scope 拒绝写入")


def test_memory_tool_dispatch() -> None:
    tool = MemoryTool(_service())

    w = tool.execute(action="write", scope="runtime", key="k", content=42)
    assert w.ok and w.data.content == 42
    r = tool.execute(action="read", scope="runtime", key="k")
    assert r.ok and r.data.content == 42

    s = tool.execute(action="search", scope="knowledge", text="茅台", type="company")
    assert s.ok and {rec.key for rec in s.data} == {"company:贵州茅台"}

    # 经验只读：经 Tool 写被拒（PermissionError → ok=False）
    bad = tool.execute(action="write", scope="experience", key="x", content={})
    assert bad.ok is False and bad.error
    # 非法 action / 缺字段
    assert tool.execute(action="nope", scope="runtime").ok is False
    assert tool.execute(action="read", scope="runtime").ok is False
    print("[OK] MemoryTool action 派发 + 只读拒写")


def test_access_via_agent_context() -> None:
    # 唯一通道：Agent 经授权的 MemoryTool 访问；未授权抛 PermissionError
    registry = ToolRegistry()
    registry.register(MemoryTool(_service()))

    ctx = AgentContext(
        agent_name="research",
        router=None,  # 本测试不触发模型
        tool_registry=registry,
        memory=InMemoryMemory(),
        granted_tools=["memory"],
    )
    res = ctx.use_tool("memory", action="read", scope="knowledge", key="industry:白酒")
    assert res.ok and res.data.content.name == "白酒"

    denied = AgentContext(
        agent_name="nogrant",
        router=None,
        tool_registry=registry,
        memory=InMemoryMemory(),
        granted_tools=[],
    )
    try:
        denied.use_tool("memory", action="read", scope="knowledge", key="industry:白酒")
        raise AssertionError("未授权应抛 PermissionError")
    except PermissionError:
        pass
    print("[OK] 经 AgentContext 授权访问 + 未授权拒绝")


def main() -> None:
    test_runtime_scope()
    test_knowledge_scope_readonly_search()
    test_experience_scope_readonly_search()
    test_readonly_scopes_reject_write()
    test_memory_tool_dispatch()
    test_access_via_agent_context()
    print("\nMemory Runtime Access Layer 测试全部通过 ✅")


if __name__ == "__main__":
    main()
