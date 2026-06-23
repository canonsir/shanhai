"""知识只读检索 Service（见 ADR 0012 Layer 2 Knowledge Memory）。

Knowledge Engine 是世界知识的唯一事实来源；本 Service 在其之上提供
「按 id 读取 / 按文本·类型检索」的只读入口，供 Memory 层经 Tool/Service 复用，
不复制、不另存一份知识。当前为进程内 Entity 索引（local-first、零依赖、无向量）。

事实来源仍属 Knowledge Engine：索引内容由上游（Extractor 编译产物 / 数据管道）写入，
本 Service 只读出。后续持久化知识库可替换此实现，接口不变。
"""

from __future__ import annotations

from collections.abc import Iterable

from shanhai_wiki_engine.schema import Entity, EntityType


class KnowledgeService:
    """进程内只读知识检索。

    维护 {entity_id: Entity} 索引；提供 get_entity / search。
    index_entities 供装配层（数据管道 / 测试）灌入已编译实体，非 Agent 写路径。
    """

    def __init__(self, entities: Iterable[Entity] | None = None) -> None:
        self._entities: dict[str, Entity] = {}
        if entities:
            self.index_entities(entities)

    def index_entities(self, entities: Iterable[Entity]) -> None:
        """灌入/更新实体索引（装配层用，幂等覆盖同 id）。"""
        for ent in entities:
            self._entities[ent.id] = ent

    def get_entity(self, entity_id: str) -> Entity | None:
        """按 id 读取实体；不存在返回 None。"""
        return self._entities.get(entity_id)

    def search(
        self,
        text: str | None = None,
        type: EntityType | None = None,
        limit: int = 50,
    ) -> list[Entity]:
        """按名称/别名子串 + 类型过滤检索（keyword，无向量）。"""
        results = list(self._entities.values())
        if type is not None:
            results = [e for e in results if e.type == type]
        if text:
            needle = text.lower()
            results = [
                e
                for e in results
                if needle in e.name.lower()
                or any(needle in a.lower() for a in e.aliases)
            ]
        return results[:limit]
