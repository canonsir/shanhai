"""MemoryTool — Agent 触达 Memory 的唯一通道（见 ADR 0012 §3/§5）。

与 WikiExtractTool 同构：构造注入 MemoryService，execute 经 action 派发到 read/search/write。
单工具 + action 派发：Agent 只需被授予一个工具名 "memory" 即可访问三层记忆，
仍受 AgentContext.use_tool 的授权校验约束。Agent 不持有 MemoryService/Store 引用。
"""

from __future__ import annotations

from typing import Any

from shanhai_tools.base import Tool, ToolResult

from shanhai_memory.models import MemoryQuery, MemoryScope
from shanhai_memory.service import MemoryService


class MemoryTool(Tool):
    name = "memory"
    description = "访问 Agent 三层记忆（runtime/knowledge/experience）：action=read/search/write。"

    def __init__(self, service: MemoryService) -> None:
        super().__init__()
        self._service = service

    def execute(self, **kwargs: Any) -> ToolResult:
        """入参：action(read|search|write) + scope + 各操作所需字段。"""
        action = kwargs.get("action")
        scope = _as_scope(kwargs.get("scope"))
        if scope is None:
            return ToolResult(ok=False, error="缺少或非法 scope（runtime/knowledge/experience）")

        try:
            if action == "read":
                key = kwargs.get("key")
                if not key:
                    return ToolResult(ok=False, error="read 需要 key")
                record = self._service.read(scope, key)
                return ToolResult(ok=True, data=record)

            if action == "search":
                query = MemoryQuery(
                    scope=scope,
                    text=kwargs.get("text"),
                    key=kwargs.get("key"),
                    type=kwargs.get("type"),
                    tags=kwargs.get("tags") or [],
                    agent=kwargs.get("agent"),
                    limit=kwargs.get("limit", 50),
                )
                return ToolResult(ok=True, data=self._service.search(query))

            if action == "write":
                key = kwargs.get("key")
                if not key:
                    return ToolResult(ok=False, error="write 需要 key")
                record = self._service.write(
                    scope, key, kwargs.get("content"), tags=kwargs.get("tags")
                )
                return ToolResult(ok=True, data=record)

            return ToolResult(ok=False, error=f"未知 action: {action}（应为 read/search/write）")
        except (PermissionError, KeyError) as exc:
            return ToolResult(ok=False, error=str(exc))


def _as_scope(value: Any) -> MemoryScope | None:
    if isinstance(value, MemoryScope):
        return value
    try:
        return MemoryScope(value)
    except ValueError:
        return None
