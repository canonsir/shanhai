"""ShanHai Tool Registry。

统一管理 Agent 可调用的工具。Phase 0 只提供接口、注册机制与一个示例工具。

调用链铁律：Agent → Tool → Service → Database。
工具是 Agent 触达外部能力的唯一入口。
"""

from shanhai_tools.base import Tool, ToolResult
from shanhai_tools.registry import ToolRegistry, registry
from shanhai_tools.examples import EchoTool

__all__ = [
    "Tool",
    "ToolResult",
    "ToolRegistry",
    "registry",
    "EchoTool",
]
