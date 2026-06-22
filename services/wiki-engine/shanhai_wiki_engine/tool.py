"""WikiExtractTool — Agent 触达知识编译 Service 的唯一通道（见 ADR 0007）。

依赖 shanhai-tools 的 Tool 基类，包装 Extractor。保持依赖方向 wiki-engine → tools（单向）。
"""

from __future__ import annotations

from typing import Any

from shanhai_tools.base import Tool, ToolResult

from shanhai_wiki_engine.extractor import Extractor
from shanhai_wiki_engine.schema import Document


class WikiExtractTool(Tool):
    name = "wiki_extract"
    description = "从文档中抽取实体与关系（规则驱动），返回编译后的 Document。"

    def __init__(self, extractor: Extractor | None = None) -> None:
        super().__init__()
        self._extractor = extractor or Extractor()

    def execute(self, **kwargs: Any) -> ToolResult:
        """入参：document（Document）或 content/title（构造临时 Document）。"""
        document = kwargs.get("document")
        if document is None:
            content = kwargs.get("content")
            if content is None:
                return ToolResult(ok=False, error="缺少 document 或 content 参数")
            document = Document(
                id=kwargs.get("id", "doc:adhoc"),
                title=kwargs.get("title", ""),
                content=content,
            )
        compiled = self._extractor.extract(document)
        return ToolResult(ok=True, data=compiled)
