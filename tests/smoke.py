"""Phase 0 冒烟测试 —— 验证 Harness 装配与验收标准。

运行：uv run python -m tests.smoke
覆盖：
  1. Model Router 可切换模型
  2. Agent 可调用 Tool（Agent → Tool）
  3. Wiki Entity Schema 存在
"""

from __future__ import annotations

from pathlib import Path

from shanhai_agent_runtime import Agent, InMemoryMemory
from shanhai_harness_core import Workflow
from shanhai_model_router import ModelRegistry, ModelRouter
from shanhai_schemas import Message, Role, TaskType
from shanhai_tools import EchoTool, registry
from shanhai_wiki_engine import Document, Entity, EntityType, Relation, RelationType

MODELS_YAML = Path(__file__).resolve().parents[1] / "services" / "model-router" / "models.yaml"


def check_router() -> None:
    router = ModelRouter(ModelRegistry.from_yaml(MODELS_YAML))
    msgs = [Message(role=Role.USER, content="你好，山海")]

    # 显式指定不同模型 → 验证可切换
    r1 = router.complete(TaskType.GENERAL, msgs, model="gpt-5.5")
    r2 = router.complete(TaskType.GENERAL, msgs, model="deepseek")
    assert r1.model == "gpt-5.5" and r2.model == "deepseek", "模型切换失败"

    # 按能力自动选择：reasoning 任务应命中高 reasoning 模型
    reasoning = router.select(TaskType.REASONING)
    assert reasoning.capability.reasoning >= 9, "按能力选模型失败"

    # 成本偏好：extraction + 低成本
    cheap = router.select(TaskType.EXTRACTION, prefer_low_cost=True)
    assert cheap.capability.cost == "low", "成本偏好选择失败"
    print(f"[OK] Router 可切换模型：{r1.model} / {r2.model}；reasoning→{reasoning.name}；cheap→{cheap.name}")


def check_agent_tool() -> None:
    registry.register(EchoTool())
    router = ModelRouter(ModelRegistry.from_yaml(MODELS_YAML))

    wf = Workflow("demo").add_node("greet", lambda s: {**s, "greeted": True})
    agent = Agent(
        name="research",
        router=router,
        tools=["echo"],
        memory=InMemoryMemory(),
        workflow=wf,
    )

    result = agent.use_tool("echo", q="测试")
    assert result.ok and result.data == {"q": "测试"}, "Agent 调用 Tool 失败"

    # 未授权工具应被拒绝
    try:
        agent.use_tool("not_granted")
        raise AssertionError("未授权工具应抛出 PermissionError")
    except PermissionError:
        pass

    out = agent.run("hello")
    assert out["greeted"] is True, "Agent workflow 执行失败"
    print("[OK] Agent → Tool 调用链通过；workflow 执行通过")


def check_wiki_schema() -> None:
    company = Entity(id="c1", type=EntityType.COMPANY, name="示例公司")
    industry = Entity(id="i1", type=EntityType.INDUSTRY, name="示例行业")
    rel = Relation(
        id="r1",
        type=RelationType.BELONGS_TO_INDUSTRY,
        source_id=company.id,
        target_id=industry.id,
    )
    doc = Document(id="d1", title="示例", content="...", entities=[company, industry], relations=[rel])
    assert doc.entities[0].type == EntityType.COMPANY
    assert {e.value for e in EntityType} == {
        "company", "industry", "policy", "event", "person", "concept",
    }, "Wiki 实体类型不完整"
    print("[OK] Wiki Entity / Relation / Document Schema 存在")


def main() -> None:
    check_router()
    check_agent_tool()
    check_wiki_schema()
    print("\n全部冒烟检查通过 ✅  Phase 0 Harness 装配正确。")


if __name__ == "__main__":
    main()
