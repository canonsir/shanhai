"""Feedback → Evolution 候选提案适配器（见 ADR 0017 修正 2，Stage 2-b）。

旁路适配层（Stage 2-b）：把 feedback 现有的弱 ExperienceCandidate 映射为 Evolution Layer
的 CandidateProposal，再由调用方经 CandidateService.create() 统一产出 Candidate。
Feedback 由此退为「Candidate Producer 之一」（ADR 0017 Decision B），主链路（lesson 晋升）
本阶段保持不动；本文件为纯新增 adapter，不修改 feedback 既有逻辑。

依赖方向（允许）：feedback → experience-evolution → experience。
边界冻结：Adapter 只产 CandidateProposal，**不**生成 ExperienceCandidate、
不持有 CandidateService、不绕过 Service（只暴露 to_proposal，不提供 create_candidate）。
"""

from __future__ import annotations

from shanhai_experience_evolution.models import (
    CandidateSource,
    Hypothesis,
    Lineage,
    SourceRefs,
)
from shanhai_experience_evolution.proposals import CandidateProposal

from shanhai_feedback.models import ExperienceCandidate as FeedbackCandidate


class FeedbackProposalAdapter:
    """把 feedback 候选确定性映射为 CandidateProposal（无模型、无副作用）。"""

    source = CandidateSource.FEEDBACK

    def to_proposal(self, candidate: FeedbackCandidate) -> CandidateProposal:
        """feedback ExperienceCandidate → CandidateProposal（不创建 Candidate）。

        映射规则（确定性）：
        - kind/summary → hypothesis 草稿（condition 用人类可读 summary，action 留待验证演化）；
          occurrences/score 不作为 validity 依据（validation != occurrence count）。
        - source_run_ids → source_refs.event_ids（来源：为什么产生）。
        - dedup_key → lineage.source（保留血缘可追溯到 feedback 来源）。
        """
        hypothesis = Hypothesis(
            condition=candidate.summary,
            expected_outcome=f"规避 {candidate.kind.value}",
        )
        source_refs = SourceRefs(event_ids=list(candidate.source_run_ids))
        lineage = Lineage(
            source=f"feedback:{candidate.dedup_key}",
            notes=candidate.summary,
        )
        return CandidateProposal(
            source=self.source,
            hypothesis=hypothesis,
            source_refs=source_refs,
            lineage=lineage,
        )
