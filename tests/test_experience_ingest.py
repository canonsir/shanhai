"""Experience Outcome 回填基座测试（见 ADR 0015 Stage 2-a）。

运行：PYTHONPATH=. .venv/bin/python -m tests.test_experience_ingest
覆盖：
  Case 1  decision 创建：RunRecord → ExperienceRecorder → decision 事件
  Case 2  结果回填：decision 事件 → OutcomeIngestor → outcome 事件（parent_event_id 关联）
  Case 3  跨 run episode：run1/run2 decision + run3 outcome 同 episode_id，按 episode 查全量
  Case 4  权限边界：Agent 不能写 Experience（EXPERIENCE 对 Agent 只读，守 ADR 0012 不变量）
"""

from __future__ import annotations

from datetime import datetime

from shanhai_agent_runtime.context import AgentContext
from shanhai_agent_runtime.memory import InMemoryMemory
from shanhai_agent_runtime.store import InMemoryRunStore
from shanhai_agent_runtime.types import AgentStatus, RunResult, Step, StepType
from shanhai_experience import (
    ExperienceEventType,
    ExperienceRecorder,
    InMemoryExperienceStore,
    OutcomeIngestor,
    resolve_episode_id,
)
from shanhai_memory import (
    ExperienceReadAdapter,
    KnowledgeReadAdapter,
    MemoryService,
    MemoryTool,
    RuntimeMemoryAdapter,
)
from shanhai_tools.registry import ToolRegistry
from shanhai_wiki_engine import KnowledgeService


def _completed_run(agent: str = "research", output: str = "看多 A 公司") -> RunResult:
    return RunResult(
        agent=agent,
        status=AgentStatus.COMPLETED,
        output=output,
        steps=[
            Step(index=0, type=StepType.THINK, content="分析基本面"),
            Step(index=1, type=StepType.OBSERVE, content="营收同比 +20%"),
        ],
    )


def test_resolve_episode_id() -> None:
    assert resolve_episode_id("ep-1", "run-1") == "ep-1"  # 显式优先
    assert resolve_episode_id(None, "run-1") == "run-1"  # 回退 run_id
    try:
        resolve_episode_id(None, None)
        raise AssertionError("两者皆空应报错")
    except ValueError:
        pass
    print("[OK] resolve_episode_id：显式优先 / 回退 run_id / 皆空报错")


def test_case1_record_decision() -> None:
    run_store = InMemoryRunStore()
    rid = run_store.save_run(_completed_run())
    record = run_store.get_run(rid)

    store = InMemoryExperienceStore()
    recorder = ExperienceRecorder(store)
    decision = recorder.record_decision(record)

    assert decision.type == ExperienceEventType.DECISION
    assert decision.agent == "research"
    assert decision.refs.run_id == rid
    assert decision.episode_id == rid  # 缺省回退 run_id
    assert decision.payload["summary"] == "看多 A 公司"

    got = store.list(type=ExperienceEventType.DECISION)
    assert len(got) == 1 and got[0].event_id == decision.event_id
    print("[OK] Case 1：RunRecord → decision 事件（引用 run_id，不复制 Step 全量）")


def test_case1b_record_observations() -> None:
    run_store = InMemoryRunStore()
    rid = run_store.save_run(_completed_run())
    record = run_store.get_run(rid)

    store = InMemoryExperienceStore()
    recorder = ExperienceRecorder(store)
    obs = recorder.record_observations(record)

    assert len(obs) == 1  # 只有一个 OBSERVE step
    assert obs[0].type == ExperienceEventType.OBSERVATION
    assert obs[0].payload["content"] == "营收同比 +20%"
    print("[OK] Case 1b：observe 步骤 → observation 事件")


def test_case2_outcome_backfill() -> None:
    run_store = InMemoryRunStore()
    rid = run_store.save_run(_completed_run())
    record = run_store.get_run(rid)

    store = InMemoryExperienceStore()
    recorder = ExperienceRecorder(store)
    ingestor = OutcomeIngestor(store)

    decision = recorder.record_decision(record)
    outcome = ingestor.ingest(
        decision_event_id=decision.event_id,
        outcome={"return": 0.12, "direction": "up", "correct": True},
        occurred_at=datetime(2026, 9, 1),
    )

    # append-only：outcome 是新事件，挂回 decision，不改 decision 本身
    assert outcome.type == ExperienceEventType.OUTCOME
    assert outcome.refs.parent_event_id == decision.event_id
    assert outcome.episode_id == decision.episode_id
    assert outcome.agent == decision.agent
    assert outcome.payload["outcome"]["correct"] is True
    # occurred_at(真实发生) 与 recorded_at(写入) 分离
    assert outcome.occurred_at == datetime(2026, 9, 1)
    assert outcome.recorded_at != outcome.occurred_at

    # 经 parent_event_id 反查某决策的结果回填
    backfilled = store.list(parent_event_id=decision.event_id)
    assert len(backfilled) == 1 and backfilled[0].event_id == outcome.event_id

    # decision 事件未被修改（store 中仍可原样读到）
    assert store.get(decision.event_id).payload == decision.payload

    # 回填不存在/非 decision 的 parent 报错
    try:
        ingestor.ingest("nope", {"x": 1}, datetime(2026, 9, 1))
        raise AssertionError("不存在的 parent 应报错")
    except ValueError:
        pass
    print("[OK] Case 2：decision → outcome 回填（parent 关联 / append-only / 双时间戳分离）")


def test_case3_cross_run_episode() -> None:
    run_store = InMemoryRunStore()
    store = InMemoryExperienceStore()
    recorder = ExperienceRecorder(store)
    ingestor = OutcomeIngestor(store)

    episode = "Tesla 2026 Q1 Investment Research"

    # run1 初次分析、run2 财报更新 → 两条 decision，归同一 episode（跨 run）
    rid1 = run_store.save_run(_completed_run(output="初次分析：看多"))
    rid2 = run_store.save_run(_completed_run(output="财报更新：维持看多"))
    d1 = recorder.record_decision(run_store.get_run(rid1), episode_id=episode)
    d2 = recorder.record_decision(run_store.get_run(rid2), episode_id=episode)

    # run3 结果验证：对 run1 决策回填真实结果，沿用同 episode
    rid3 = run_store.save_run(_completed_run(output="结果验证"))
    _ = rid3
    out = ingestor.ingest(d1.event_id, {"return": 0.30, "correct": True}, datetime(2026, 4, 1))

    assert d1.episode_id == d2.episode_id == out.episode_id == episode
    assert d1.refs.run_id != d2.refs.run_id  # 不同 run

    events = store.list(episode_id=episode)
    assert len(events) == 3  # 两条 decision + 一条 outcome
    types = {e.type for e in events}
    assert types == {ExperienceEventType.DECISION, ExperienceEventType.OUTCOME}
    print("[OK] Case 3：跨 run episode 聚合，按 episode_id 查回全量事件")


def test_case4_agent_cannot_write_experience() -> None:
    store = InMemoryExperienceStore()
    # 预置一条 lesson 供只读读取验证
    run_store = InMemoryRunStore()
    rid = run_store.save_run(_completed_run())
    ExperienceRecorder(store).record_decision(run_store.get_run(rid))

    mem = MemoryService(
        runtime=RuntimeMemoryAdapter(InMemoryMemory()),
        knowledge=KnowledgeReadAdapter(KnowledgeService()),
        experience=ExperienceReadAdapter(store),
    )
    registry = ToolRegistry()
    registry.register(MemoryTool(mem))
    ctx = AgentContext(
        agent_name="research",
        router=None,
        tool_registry=registry,
        memory=InMemoryMemory(),
        granted_tools=["memory"],
    )

    # 只读可用：能 search 到 decision
    res = ctx.use_tool(
        "memory", action="search", scope="experience", agent="research", type="decision"
    )
    assert res.ok and len(res.data) == 1

    # 写被拒：EXPERIENCE 对 Agent 只读（ADR 0012 不变量）
    bad = ctx.use_tool(
        "memory", action="write", scope="experience", key="x", content={}
    )
    assert bad.ok is False and bad.error
    print("[OK] Case 4：Agent 经 MemoryTool 只读 Experience，写入被拒（不变量保持）")


def main() -> None:
    test_resolve_episode_id()
    test_case1_record_decision()
    test_case1b_record_observations()
    test_case2_outcome_backfill()
    test_case3_cross_run_episode()
    test_case4_agent_cannot_write_experience()
    print("\nExperience Outcome 回填基座测试全部通过 ✅")


if __name__ == "__main__":
    main()
