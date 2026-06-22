"""ShanHai Agent Runtime。

提供 Agent 生命周期与执行模型（think → act → observe，见 ADR 0006）。
约束（见 AGENTS.md）：
- Agent 禁止直接绑定/调用模型 → 必须经 ModelRouter。
- Agent 禁止直接访问数据库 → 必须经 Tool → Service。
"""

from shanhai_agent_runtime.agent import Agent, BaseAgent
from shanhai_agent_runtime.context import AgentContext
from shanhai_agent_runtime.examples import MultiStepToolAgent, ToolEchoAgent
from shanhai_agent_runtime.memory import InMemoryMemory, Memory
from shanhai_agent_runtime.runner import AgentRunner
from shanhai_agent_runtime.types import (
    AgentStatus,
    Plan,
    RunResult,
    Step,
    StepType,
)

__all__ = [
    "Agent",
    "BaseAgent",
    "ToolEchoAgent",
    "MultiStepToolAgent",
    "AgentContext",
    "AgentRunner",
    "Memory",
    "InMemoryMemory",
    "AgentStatus",
    "StepType",
    "Plan",
    "Step",
    "RunResult",
]
