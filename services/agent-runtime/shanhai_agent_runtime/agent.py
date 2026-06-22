"""Agent 基类。"""

from __future__ import annotations

from typing import Any

from shanhai_harness_core import Workflow
from shanhai_model_router import ModelRouter
from shanhai_tools import ToolResult, registry as default_registry
from shanhai_tools.registry import ToolRegistry

from shanhai_agent_runtime.memory import InMemoryMemory, Memory


class Agent:
    """所有 Agent 的基类。

    Agent 通过注入的 ModelRouter 调用模型、通过 ToolRegistry 调用工具，
    绝不直接绑定模型或访问数据库。
    """

    def __init__(
        self,
        name: str,
        router: ModelRouter,
        tools: list[str] | None = None,
        tool_registry: ToolRegistry | None = None,
        memory: Memory | None = None,
        workflow: Workflow | None = None,
    ) -> None:
        self.name = name
        self.router = router
        self.tools = tools or []
        self._registry = tool_registry or default_registry
        self.memory = memory or InMemoryMemory()
        self.workflow = workflow

    def use_tool(self, tool_name: str, **kwargs: Any) -> ToolResult:
        """Agent 触达外部能力的唯一入口：Agent → Tool → Service。"""
        if tool_name not in self.tools:
            raise PermissionError(f"Agent[{self.name}] 未被授予工具: {tool_name}")
        return self._registry.get(tool_name).execute(**kwargs)

    def run(self, input: Any) -> Any:
        """Agent 执行入口。基类提供 workflow 默认实现，子类可覆写。"""
        if self.workflow is not None:
            return self.workflow.run({"input": input, "agent": self.name})
        raise NotImplementedError("子类需实现 run() 或注入 workflow")
