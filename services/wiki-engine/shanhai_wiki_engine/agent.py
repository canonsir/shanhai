"""WikiExtractionAgent — 编排知识提取链路（见 ADR 0007）。

think：经 ModelRouter 调模型（task=EXTRACTION），证明模型在环与能力路由生效；
act： 经 ToolRegistry 调 WikiExtractTool → Extractor 完成确定性编译。
模型只出现在 think，编译只出现在 Service，二者由 Tool 解耦，符合架构铁律。
"""

from __future__ import annotations

from typing import Any

from shanhai_agent_runtime import BaseAgent
from shanhai_agent_runtime.context import AgentContext
from shanhai_agent_runtime.types import Plan
from shanhai_schemas import TaskType

from shanhai_wiki_engine.schema import Document


class WikiExtractionAgent(BaseAgent):
    """从文档提取实体与关系。输入为 Document 或纯文本。"""

    TOOL_NAME = "wiki_extract"

    @staticmethod
    def _content(ctx: AgentContext) -> str:
        return ctx.input.content if isinstance(ctx.input, Document) else str(ctx.input)

    def think(self, ctx: AgentContext) -> Plan:
        text = self._content(ctx)
        # 模型在环：让 Router 按 EXTRACTION 能力选模型并产出规划提示
        completion = ctx.complete(
            f"识别下列文本中的公司、行业、政策及其关系：\n{text}",
            task=TaskType.EXTRACTION,
        )
        args: dict[str, Any] = (
            {"document": ctx.input}
            if isinstance(ctx.input, Document)
            else {"content": text}
        )
        return Plan(
            thought=f"经模型 {completion.model} 规划后调用 {self.TOOL_NAME} 编译知识",
            tool=self.TOOL_NAME,
            tool_args=args,
        )
