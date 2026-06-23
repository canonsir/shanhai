"""候选经验创建输入契约（见 ADR 0017 修正 2，Stage 2-b）。

CandidateProposal 是「描述来源 + 初始假设草稿 + source_refs」的**纯输入对象**，
不是 Candidate，也不是生成引擎。统一入口让 feedback / outcome / mining / human /
agent_discovery 等多来源复用 CandidateService.create()（ADR 0017 修正 2）。

边界（本阶段冻结）：这里只放输入数据契约，不放 ProposalEngine / CandidateGenerator /
ProposalBuilder——那属于尚未开放的 Discovery Layer（Mining / Agent Discovery /
Self Improvement）。
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from shanhai_experience_evolution.models import (
    CandidateSource,
    Hypothesis,
    Lineage,
    SourceRefs,
)


class CandidateProposal(BaseModel):
    """创建候选经验的输入契约（input contract，非 Candidate）。

    - source：来源（哪个 Producer 提出）。
    - hypothesis：初始假设草稿（可不完整，后续随验证演化）。
    - source_refs：为什么产生这条候选（事实/上游候选/外部引用）。
    - lineage：可选血缘备注；create 时若缺省，由 Service 以 source 兜底填充。
    """

    source: CandidateSource
    hypothesis: Hypothesis = Field(default_factory=Hypothesis)
    source_refs: SourceRefs = Field(default_factory=SourceRefs)
    lineage: Lineage | None = None
