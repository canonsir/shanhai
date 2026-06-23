"""MemoryService — 记忆访问编排层（见 ADR 0012 §3/§5）。

按 MemoryScope 把 read / search / write 路由到对应 adapter，对上提供统一语义：
- RUNTIME：进程内 scratchpad，可读写。
- KNOWLEDGE / EXPERIENCE：只读委派各自事实来源；write 被拒绝（不复制、不另存）。

边界铁律：不调用模型、不直连 DB、不复制知识/度量、不侵入 Agent Runtime。
依赖单向：memory → agent-runtime 抽象 + wiki-engine + experience。
"""

from __future__ import annotations

from typing import Any

from shanhai_memory.adapters import (
    ExperienceReadAdapter,
    KnowledgeReadAdapter,
    RuntimeMemoryAdapter,
)
from shanhai_memory.models import MemoryQuery, MemoryRecord, MemoryScope

# 只读 scope 不可写
_READONLY_SCOPES = {MemoryScope.KNOWLEDGE, MemoryScope.EXPERIENCE}


class MemoryService:
    """三层记忆统一编排。按 scope 路由到注入的 adapter。"""

    def __init__(
        self,
        runtime: RuntimeMemoryAdapter,
        knowledge: KnowledgeReadAdapter | None = None,
        experience: ExperienceReadAdapter | None = None,
    ) -> None:
        self._adapters: dict[MemoryScope, Any] = {MemoryScope.RUNTIME: runtime}
        if knowledge is not None:
            self._adapters[MemoryScope.KNOWLEDGE] = knowledge
        if experience is not None:
            self._adapters[MemoryScope.EXPERIENCE] = experience

    def _adapter(self, scope: MemoryScope) -> Any:
        adapter = self._adapters.get(scope)
        if adapter is None:
            raise KeyError(f"未配置 {scope.value} scope 的 adapter")
        return adapter

    def read(self, scope: MemoryScope, key: str) -> MemoryRecord | None:
        return self._adapter(scope).read(key)

    def search(self, query: MemoryQuery) -> list[MemoryRecord]:
        return self._adapter(query.scope).search(query)

    def write(
        self,
        scope: MemoryScope,
        key: str,
        content: Any,
        tags: list[str] | None = None,
    ) -> MemoryRecord:
        if scope in _READONLY_SCOPES:
            raise PermissionError(f"{scope.value} 为只读记忆，禁止写入（事实来源在对应模块）")
        return self._adapter(scope).write(key, content, tags=tags)
