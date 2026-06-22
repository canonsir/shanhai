"""示例 Agent：演示 think → act → observe 执行模型，不含业务逻辑。

仅用于验证运行时装配与调用链路（Agent → Tool / Agent → ModelRouter）。
"""

from __future__ import annotations

from shanhai_agent_runtime.agent import BaseAgent
from shanhai_agent_runtime.context import AgentContext
from shanhai_agent_runtime.types import Plan


class ToolEchoAgent(BaseAgent):
    """think 阶段规划调用指定工具，act 阶段经 ToolRegistry 执行。"""

    def __init__(self, *args, tool_name: str = "echo", **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._tool_name = tool_name

    def think(self, ctx: AgentContext) -> Plan:
        return Plan(
            thought=f"调用工具 {self._tool_name} 处理输入",
            tool=self._tool_name,
            tool_args={"q": ctx.input},
        )
