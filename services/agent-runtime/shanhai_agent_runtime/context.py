"""Agent 运行上下文。

承载单次运行所需的依赖与累计状态。Agent 只能经此上下文触达模型与工具，
从结构上保证架构铁律（见 AGENTS.md §3.1 / §4、ADR 0006）：
- 模型调用：context.complete(...) → ModelRouter
- 外部能力：context.use_tool(...) → ToolRegistry → Service
Agent 不持有数据库或 Provider 的直接引用。
"""

from __future__ import annotations

from typing import Any

from shanhai_model_router import ModelRouter
from shanhai_model_router.providers.base import CompletionResult
from shanhai_schemas import Message, Role, TaskType
from shanhai_tools import ToolResult
from shanhai_tools.registry import ToolRegistry

from shanhai_agent_runtime.memory import Memory
from shanhai_agent_runtime.types import Step


class AgentContext:
    def __init__(
        self,
        agent_name: str,
        router: ModelRouter,
        tool_registry: ToolRegistry,
        memory: Memory,
        granted_tools: list[str],
        input: Any = None,
    ) -> None:
        self.agent_name = agent_name
        self.input = input
        self.memory = memory
        self.steps: list[Step] = []
        # 多步推理状态：当前迭代序号与历轮观察结果，供 think 基于上一轮规划
        self.iteration: int = 0
        self.observations: list[Any] = []
        self._router = router
        self._registry = tool_registry
        self._granted = set(granted_tools)

    @property
    def last_observation(self) -> Any:
        """上一轮 observe 记录的结果；首轮为 None。"""
        return self.observations[-1] if self.observations else None

    def complete(
        self,
        prompt: str,
        task: TaskType | str = TaskType.GENERAL,
        model: str | None = None,
        context: dict | None = None,
    ) -> CompletionResult:
        """经 ModelRouter 调用模型。Agent 不绑定具体模型。"""
        return self._router.complete(
            task=task,
            messages=[Message(role=Role.USER, content=prompt)],
            context=context,
            model=model,
        )

    def use_tool(self, tool_name: str, **kwargs: Any) -> ToolResult:
        """经 ToolRegistry 调用工具：Agent → Tool → Service。"""
        if tool_name not in self._granted:
            raise PermissionError(f"Agent[{self.agent_name}] 未被授予工具: {tool_name}")
        return self._registry.get(tool_name).execute(**kwargs)

    def record(self, step: Step) -> Step:
        step.index = len(self.steps)
        self.steps.append(step)
        return step
