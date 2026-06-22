"""示例工具：仅用于验证注册与调用链路，不含业务逻辑。"""

from __future__ import annotations

from typing import Any

from shanhai_tools.base import Tool, ToolResult


class EchoTool(Tool):
    name = "echo"
    description = "回显输入，用于验证 Agent → Tool 调用链路。"

    def execute(self, **kwargs: Any) -> ToolResult:
        return ToolResult(ok=True, data=kwargs)
