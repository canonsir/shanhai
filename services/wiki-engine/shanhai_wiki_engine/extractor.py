"""规则驱动的信息提取（Service 层，见 ADR 0007）。

从 Document.content 中识别实体并发现关系，填充 Document。
本层 model-agnostic：不调用模型、不访问网络，确定性可复现，便于单测。
模型在环由上层 Agent 经 ModelRouter 负责（见 WikiExtractionAgent）。
"""

from __future__ import annotations

import re

from shanhai_wiki_engine.schema import (
    Document,
    Entity,
    EntityType,
    Relation,
    RelationType,
)


def _entity_id(type_: EntityType, name: str) -> str:
    """确定性 id：类型 + 名称，保证可复现与去重。"""
    return f"{type_.value}:{name}"


def _relation_id(type_: RelationType, source_id: str, target_id: str) -> str:
    return f"{type_.value}:{source_id}->{target_id}"


class Extractor:
    """规则驱动抽取器。

    - 实体：按 EntityType 维护关键词/别名词典，命中即产出 Entity；
    - 关系：按 RelationType 维护文本模式，命中且两端实体均识别到才产出 Relation。
    词典与模式可在构造时覆盖，便于按领域扩展。
    """

    # 默认词典：名称 -> 别名列表
    DEFAULT_LEXICON: dict[EntityType, dict[str, list[str]]] = {
        EntityType.COMPANY: {
            "宁德时代": ["CATL"],
            "比亚迪": ["BYD"],
            "贵州茅台": ["茅台"],
        },
        EntityType.INDUSTRY: {
            "新能源": [],
            "动力电池": ["锂电池"],
            "白酒": [],
            "半导体": ["芯片"],
        },
        EntityType.POLICY: {
            "碳中和": ["双碳"],
        },
    }

    # 关系模式：(关系类型, 源实体类型, 目标实体类型, 连接正则)
    DEFAULT_PATTERNS: list[tuple[RelationType, EntityType, EntityType, str]] = [
        (RelationType.BELONGS_TO_INDUSTRY, EntityType.COMPANY, EntityType.INDUSTRY, r"属于|布局|从事|主营"),
        (RelationType.AFFECTS_INDUSTRY, EntityType.POLICY, EntityType.INDUSTRY, r"利好|影响|推动|促进"),
    ]

    def __init__(
        self,
        lexicon: dict[EntityType, dict[str, list[str]]] | None = None,
        patterns: list[tuple[RelationType, EntityType, EntityType, str]] | None = None,
    ) -> None:
        self._lexicon = lexicon or self.DEFAULT_LEXICON
        self._patterns = patterns or self.DEFAULT_PATTERNS

    def extract(self, document: Document) -> Document:
        """抽取实体与关系，返回填充后的 Document 副本。"""
        text = document.content or ""
        entities = self._extract_entities(text)
        relations = self._extract_relations(text, entities)
        return document.model_copy(
            update={
                "entities": list(entities.values()),
                "relations": relations,
            }
        )

    def _extract_entities(self, text: str) -> dict[str, Entity]:
        """返回 {规范名称: Entity}，按词典命中识别（含别名归一）。"""
        found: dict[str, Entity] = {}
        for type_, names in self._lexicon.items():
            for name, aliases in names.items():
                surface = [name, *aliases]
                if any(s and s in text for s in surface):
                    found[name] = Entity(
                        id=_entity_id(type_, name),
                        type=type_,
                        name=name,
                        aliases=list(aliases),
                    )
        return found

    def _extract_relations(self, text: str, entities: dict[str, Entity]) -> list[Relation]:
        """对每条模式，在源/目标实体之间寻找连接词共现，命中则建立关系。"""
        relations: list[Relation] = []
        seen: set[str] = set()
        by_type: dict[EntityType, list[Entity]] = {}
        for ent in entities.values():
            by_type.setdefault(ent.type, []).append(ent)

        for rel_type, src_type, dst_type, connector in self._patterns:
            for src in by_type.get(src_type, []):
                for dst in by_type.get(dst_type, []):
                    if self._connected(text, src.name, dst.name, connector):
                        rid = _relation_id(rel_type, src.id, dst.id)
                        if rid in seen:
                            continue
                        seen.add(rid)
                        relations.append(
                            Relation(
                                id=rid,
                                type=rel_type,
                                source_id=src.id,
                                target_id=dst.id,
                            )
                        )
        return relations

    @staticmethod
    def _connected(text: str, src_name: str, dst_name: str, connector: str) -> bool:
        """源在前、连接词、目标在后（同序共现）视为关系成立。"""
        pattern = re.compile(
            rf"{re.escape(src_name)}.*?(?:{connector}).*?{re.escape(dst_name)}"
        )
        return bool(pattern.search(text))
