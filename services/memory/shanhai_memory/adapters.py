"""三层记忆的 scope adapter（见 ADR 0012 §2/§5）。

每个 adapter 把一个事实来源适配为统一的 read / search（Runtime 额外可 write）：
- RuntimeMemoryAdapter：薄包 agent-runtime 的进程内 Memory（scratchpad，可读写，无持久后端）。
- KnowledgeReadAdapter：只读委派 wiki-engine KnowledgeService，不复制知识。
- ExperienceReadAdapter：只读委派 ExperienceStore（get/list），绝不 append、不改 EventStore。

返回统一收敛为 MemoryRecord；原始对象置于 content，事实来源仍属各自模块。
"""

from __future__ import annotations

from typing import Any

from shanhai_agent_runtime.memory import Memory
from shanhai_experience import ExperienceEventType, ExperienceStore
from shanhai_wiki_engine import EntityType, KnowledgeService

from shanhai_memory.models import MemoryQuery, MemoryRecord, MemoryScope

_MISSING = object()


class RuntimeMemoryAdapter:
    """进程内运行时记忆（Layer 1）。scratchpad，可读写，无外部存储后端。"""

    scope = MemoryScope.RUNTIME

    def __init__(self, memory: Memory) -> None:
        self._memory = memory

    def write(self, key: str, content: Any, tags: list[str] | None = None) -> MemoryRecord:
        self._memory.remember(key, content)
        return MemoryRecord(
            scope=self.scope, key=key, content=content, tags=tags or [], source="runtime"
        )

    def read(self, key: str) -> MemoryRecord | None:
        value = self._memory.recall(key, _MISSING)
        if value is _MISSING:
            return None
        return MemoryRecord(scope=self.scope, key=key, content=value, source="runtime")

    def search(self, query: MemoryQuery) -> list[MemoryRecord]:
        records = [
            MemoryRecord(scope=self.scope, key=str(k), content=v, source="runtime")
            for k, v in self._memory.history()
        ]
        return records[: query.limit]


class KnowledgeReadAdapter:
    """世界知识只读检索（Layer 2）。委派 KnowledgeService，不另存知识。"""

    scope = MemoryScope.KNOWLEDGE

    def __init__(self, knowledge: KnowledgeService) -> None:
        self._knowledge = knowledge

    def read(self, key: str) -> MemoryRecord | None:
        entity = self._knowledge.get_entity(key)
        if entity is None:
            return None
        return self._to_record(entity)

    def search(self, query: MemoryQuery) -> list[MemoryRecord]:
        entity_type = _as_enum(EntityType, query.type)
        entities = self._knowledge.search(text=query.text, type=entity_type, limit=query.limit)
        return [self._to_record(e) for e in entities]

    def _to_record(self, entity: Any) -> MemoryRecord:
        return MemoryRecord(
            scope=self.scope,
            key=entity.id,
            content=entity,
            tags=[entity.type.value],
            source=entity.id,
        )


class ExperienceReadAdapter:
    """跨运行经验只读检索（Layer 3）。委派 ExperienceStore，只读不写。"""

    scope = MemoryScope.EXPERIENCE

    def __init__(self, store: ExperienceStore) -> None:
        self._store = store

    def read(self, key: str) -> MemoryRecord | None:
        event = self._store.get(key)
        if event is None:
            return None
        return self._to_record(event)

    def search(self, query: MemoryQuery) -> list[MemoryRecord]:
        event_type = _as_enum(ExperienceEventType, query.type)
        # 经验语境下 query.text 解释为「关于某知识实体」的 entity_id（精确匹配）
        events = self._store.list(
            agent=query.agent,
            type=event_type,
            entity_id=query.text,
            limit=query.limit,
        )
        return [self._to_record(e) for e in events]

    def _to_record(self, event: Any) -> MemoryRecord:
        return MemoryRecord(
            scope=self.scope,
            key=event.event_id,
            content=event,
            tags=[event.type.value],
            source=event.event_id,
            metadata={"episode_id": event.episode_id, "agent": event.agent},
        )


def _as_enum(enum_cls: Any, value: str | None) -> Any:
    """字符串安全转枚举；None 或非法值返回 None（不过滤）。"""
    if value is None:
        return None
    try:
        return enum_cls(value)
    except ValueError:
        return None
