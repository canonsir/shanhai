"""Agent Runtime 核心类型。

定义生命周期状态与结构化运行记录（见 ADR 0006）。
运行过程被记录为 Step 序列，是后续评估与知识沉淀的数据源。
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StepType(str, Enum):
    THINK = "think"
    ACT = "act"
    OBSERVE = "observe"


class Plan(BaseModel):
    """think 阶段的产出：下一步打算做什么。"""

    thought: str = ""
    # 需要调用的工具名；为 None 表示直接给出答案
    tool: str | None = None
    tool_args: dict = Field(default_factory=dict)
    # 当 tool 为 None 时，直接作答内容
    answer: str | None = None


class Step(BaseModel):
    """单个执行步骤的结构化记录。"""

    index: int
    type: StepType
    content: str = ""
    tool: str | None = None
    tool_args: dict = Field(default_factory=dict)
    tool_result: Any = None


class RunResult(BaseModel):
    """一次 Agent 运行的完整结果。"""

    agent: str
    status: AgentStatus
    output: Any = None
    steps: list[Step] = Field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == AgentStatus.COMPLETED
