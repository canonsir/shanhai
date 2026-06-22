"""示例 Agent：演示 think → act → observe 执行模型，不含业务逻辑。

仅用于验证运行时装配与调用链路（Agent → Tool / Agent → ModelRouter）。
"""

from __future__ import annotations

from typing import Any

from shanhai_agent_runtime.agent import BaseAgent
from shanhai_agent_runtime.context import AgentContext
from shanhai_agent_runtime.types import Plan


class ToolEchoAgent(BaseAgent):
    """单步：think 规划调用工具，act 经 ToolRegistry 执行。"""

    def __init__(self, *args, tool_name: str = "echo", **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._tool_name = tool_name

    def think(self, ctx: AgentContext) -> Plan:
        return Plan(
            thought=f"调用工具 {self._tool_name} 处理输入",
            tool=self._tool_name,
            tool_args={"q": ctx.input},
        )


class MultiStepToolAgent(BaseAgent):
    """多步：对一组输入逐项调用工具，演示 max_steps 调度与多轮循环。

    - think：取第 iteration 项规划工具调用；
    - observe：处理完最后一项才结束，否则继续下一轮。
    输入应为可索引序列；max_steps 上限保护避免越界与失控。
    """

    def __init__(self, *args, tool_name: str = "echo", **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._tool_name = tool_name

    def _items(self, ctx: AgentContext) -> list[Any]:
        return list(ctx.input) if isinstance(ctx.input, (list, tuple)) else [ctx.input]

    def think(self, ctx: AgentContext) -> Plan:
        item = self._items(ctx)[ctx.iteration]
        return Plan(
            thought=f"第 {ctx.iteration + 1} 步：处理 {item!r}",
            tool=self._tool_name,
            tool_args={"q": item},
        )

    def observe(self, ctx: AgentContext, plan: Plan, result: Any) -> bool:
        return ctx.iteration >= len(self._items(ctx)) - 1
