"""ShanHai Wiki Engine。

知识编译层。Phase 0 仅定义 Entity / Relation / Document Schema，
不实现信息提取、实体识别、关系发现等逻辑。
"""

from shanhai_wiki_engine.schema import (
    Document,
    Entity,
    EntityType,
    Relation,
    RelationType,
)

__all__ = [
    "Document",
    "Entity",
    "EntityType",
    "Relation",
    "RelationType",
]
