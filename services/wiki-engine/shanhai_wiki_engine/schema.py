"""Wiki 知识 Schema（Phase 0 仅结构定义）。

实体：Company / Industry / Policy / Event / Person / Concept
关系：Company→Industry, Policy→Industry, Event→Company, Company→SupplyChain ...
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    COMPANY = "company"
    INDUSTRY = "industry"
    POLICY = "policy"
    EVENT = "event"
    PERSON = "person"
    CONCEPT = "concept"


class RelationType(str, Enum):
    # 公司 -> 行业
    BELONGS_TO_INDUSTRY = "belongs_to_industry"
    # 政策 -> 行业
    AFFECTS_INDUSTRY = "affects_industry"
    # 事件 -> 公司
    IMPACTS_COMPANY = "impacts_company"
    # 公司 -> 产业链（上下游）
    SUPPLY_CHAIN = "supply_chain"


class Entity(BaseModel):
    id: str
    type: EntityType
    name: str
    aliases: list[str] = Field(default_factory=list)
    attributes: dict = Field(default_factory=dict)


class Relation(BaseModel):
    id: str
    type: RelationType
    source_id: str
    target_id: str
    attributes: dict = Field(default_factory=dict)


class Document(BaseModel):
    """知识来源文档。后续由 pipeline 编译为 Entity / Relation。"""

    id: str
    title: str
    content: str
    source: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # 编译结果（Phase 0 默认空）
    entities: list[Entity] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)
