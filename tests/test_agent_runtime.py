"""Agent Runtime 单元测试（Phase 1）。

运行：uv run python -m tests.test_agent_runtime
覆盖：
  1. think → act → observe 执行循环产出结构化 RunResult
  2. Agent → Tool 调用链经 ToolRegistry
  3. 未授权工具被拒绝并记为 FAILED
  4. 向后兼容：注入 Workflow 时 run() 走 workflow
"""

from __future__ import annotations

from pathlib import Path

from shanhai_agent_runtime import (
    AgentRunner,
    AgentStatus,
    BaseAgent,
    StepType,
    ToolEchoAgent,
)
from shanhai_harness_core import Workflow
from shanhai_model_router import ModelRegistry, ModelRouter
from shanhai_tools import EchoTool, registry

MODELS_YAML = Path(__file__).resolve().parents[1] / "services" / "model-router" / "models.yaml"


def _router() -> ModelRouter:
    return ModelRouter(ModelRegistry.from_yaml(MODELS_YAML))


def test_default_agent_lifecycle() -> None:
    agent = BaseAgent(name="researcher", router=_router())
    result = agent.run("分析山海")
    assert result.status == AgentStatus.COMPLETED and result.ok
    types = [s.type for s in result.steps]
    assert types == [StepType.THINK, StepType.ACT, StepType.OBSERVE], "执行循环顺序错误"
    assert isinstance(result.output, str) and result.output, "默认直答应返回文本"
    print("[OK] 默认 Agent think→act→observe 生命周期通过")


def test_tool_agent_chain() -> None:
    registry.register(EchoTool())
    agent = ToolEchoAgent(name="echo-agent", router=_router(), tools=["echo"])
    result = agent.run("hello")
    assert result.ok, "工具型 Agent 运行失败"
    act = next(s for s in result.steps if s.type == StepType.ACT)
    assert act.tool == "echo" and act.tool_result == {"q": "hello"}, "Agent → Tool 调用链失败"
    print("[OK] Agent → Tool 调用链（经 ToolRegistry）通过")


def test_unauthorized_tool_fails() -> None:
    agent = ToolEchoAgent(name="bad-agent", router=_router(), tools=[], tool_name="echo")
    result = agent.run("x")
    assert result.status == AgentStatus.FAILED and "PermissionError" in (result.error or "")
    print("[OK] 未授权工具被拒绝并结构化记为 FAILED")


def test_workflow_backward_compat() -> None:
    wf = Workflow("demo").add_node("greet", lambda s: {**s, "greeted": True})
    agent = BaseAgent(name="wf-agent", router=_router(), workflow=wf)
    out = agent.run("hi")
    assert out["greeted"] is True, "注入 Workflow 时应沿用 workflow 编排"
    print("[OK] 向后兼容：Workflow 路径不变")


def main() -> None:
    test_default_agent_lifecycle()
    test_tool_agent_chain()
    test_unauthorized_tool_fails()
    test_workflow_backward_compat()
    print("\nAgent Runtime 单元测试全部通过 ✅")


if __name__ == "__main__":
    main()
