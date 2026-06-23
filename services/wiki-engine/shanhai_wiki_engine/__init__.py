"""ShanHai Wiki Engine。

知识编译层。定义 Entity / Relation / Document Schema，并提供规则驱动的
信息提取（Extractor，见 ADR 0007）。模型在环由上层 Agent 经 ModelRouter 负责，
本层保持 model-agnostic。
"""

from shanhai_wiki_engine.agent import WikiExtractionAgent
from shanhai_wiki_engine.extractor import Extractor
from shanhai_wiki_engine.schema import (
    Document,
    Entity,
    EntityType,
    Relation,
    RelationType,
)
from shanhai_wiki_engine.service import KnowledgeService
from shanhai_wiki_engine.tool import WikiExtractTool

__all__ = [
    "Document",
    "Entity",
    "EntityType",
    "Relation",
    "RelationType",
    "Extractor",
    "KnowledgeService",
    "WikiExtractTool",
    "WikiExtractionAgent",
]
