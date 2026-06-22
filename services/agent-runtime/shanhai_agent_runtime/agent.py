"""Agent 基类。

执行模型：think → act → observe（见 ADR 0006）。
- 默认实现为「单步直答」：think 经 ModelRouter 取答案，act 直接产出，observe 结束。
- 复杂 Agent 通过覆写 think/act/observe，或注入 Workflow 实现多步。

铁律：Agent 经 ModelRouter 调模型、经 ToolRegistry 调工具，绝不直连模型或数据库。
"""

from __future__ import annotations

from typing import Any

from shanhai_harness_core import Workflow
from shanhai_model_router import ModelRouter
from shanhai_tools import ToolResult, registry as default_registry
from shanhai_tools.registry import ToolRegistry

from shanhai_agent_runtime.context import AgentContext
from shanhai_agent_runtime.memory import InMemoryMemory, Memory
from shanhai_agent_runtime.types import Plan


class BaseAgent:
    """所有 Agent 的基类。"""

    def __init__(
        self,
        name: str,
        router: ModelRouter,
        tools: list[str] | None = None,
        tool_registry: ToolRegistry | None = None,
        memory: Memory | None = None,
        workflow: Workflow | None = None,
        max_steps: int = 1,
    ) -> None:
        self.name = name
        self.router = router
        self.tools = tools or []
        self._registry = tool_registry or default_registry
        self.memory = memory or InMemoryMemory()
        self.workflow = workflow
        self.max_steps = max_steps

    # ---- 执行钩子（子类覆写以定制行为）----

    def think(self, ctx: AgentContext) -> Plan:
        """规划下一步。默认：经 ModelRouter 直接作答。"""
        completion = ctx.complete(str(ctx.input))
        return Plan(thought="direct-answer", answer=completion.content)

    def act(self, ctx: AgentContext, plan: Plan) -> Any:
        """执行计划。有 tool 则调用工具，否则返回直答内容。"""
        if plan.tool is not None:
            return ctx.use_tool(plan.tool, **plan.tool_args)
        return plan.answer

    def observe(self, ctx: AgentContext, plan: Plan, result: Any) -> bool:
        """观察结果并决定是否结束。默认单步即结束。"""
        return True

    # ---- 运行上下文工厂 ----

    def new_context(self, input: Any = None) -> AgentContext:
        return AgentContext(
            agent_name=self.name,
            router=self.router,
            tool_registry=self._registry,
            memory=self.memory,
            granted_tools=self.tools,
            input=input,
        )

    # ---- 向后兼容入口 ----

    def use_tool(self, tool_name: str, **kwargs: Any) -> ToolResult:
        """Agent 触达外部能力的唯一入口：Agent → Tool → Service。"""
        if tool_name not in self.tools:
            raise PermissionError(f"Agent[{self.name}] 未被授予工具: {tool_name}")
        return self._registry.get(tool_name).execute(**kwargs)

    def run(self, input: Any) -> Any:
        """Agent 执行入口。

        - 注入 Workflow 时沿用 workflow 编排（与 Phase 0 行为一致）；
        - 否则交由 AgentRunner 驱动 think/act/observe 循环，返回 RunResult。
        """
        if self.workflow is not None:
            return self.workflow.run({"input": input, "agent": self.name})

        # 延迟导入避免循环依赖
        from shanhai_agent_runtime.runner import AgentRunner

        return AgentRunner(self).run(input)


# 向后兼容别名
Agent = BaseAgent
