"""Promotion → Artifact Bridge：晋升后的资产构建（见 ADR 0018 D4，Commit 6）。

ArtifactBuilder 是一次**纯转换**：把已通过晋升的 (Candidate, PromotionDecision)
固化为稳定的 ExperienceArtifact。它落在 evolution 侧而非 artifact 侧，因为只有
evolution 同时知道 Candidate 与 PromotionDecision，且依赖方向必须是
experience-evolution → experience-artifact（artifact 不得反向依赖 evolution）。

职责边界（ADR 0018 D4，严格收敛）：
    允许：build(candidate, promotion_decision) -> ExperienceArtifact（纯函数）
    禁止：调用 ArtifactService.create（生产与存储分离）、持久化、修改 Candidate、
          回写 lineage.promoted_to、改 PromotionGate 契约、接入 Agent / Memory。

confidence 取晋升时刻 Candidate 置信度的**快照拷贝**（ADR 0018 D3）：Artifact 是
不可变资产，其 confidence 不随 Candidate 后续再验证而漂移，故按值拷贝、不引用、不回写。
"""

from __future__ import annotations

from shanhai_experience_artifact import (
    ArtifactRule,
    ArtifactType,
    ExperienceArtifact,
    Provenance,
)

from shanhai_experience_evolution.candidate import ExperienceCandidate
from shanhai_experience_evolution.promotion import PromotionDecision


class ArtifactBuilder:
    """(Candidate + PromotionDecision) → ExperienceArtifact 的纯转换器。"""

    def build(
        self,
        candidate: ExperienceCandidate,
        promotion_decision: PromotionDecision,
    ) -> ExperienceArtifact:
        """把已批准晋升的候选固化为稳定经验资产（不持久化、不改 Candidate）。

        - 要求 promotion_decision.approved 为 True，否则 ValueError（未晋升不产资产）。
        - 要求 decision.candidate_id 与 candidate 一致，否则 ValueError（防错配）。
        - hypothesis → ArtifactRule（context/condition/action）+ expected_outcome 提顶层。
        - confidence 取 candidate.confidence 的快照值（ADR 0018 D3）。
        - provenance 仅记录来源引用（source_type=promotion_decision，source_id=candidate_id）。
        """
        if not promotion_decision.approved:
            raise ValueError("promotion_decision.approved 必须为 True 才能构建 Artifact")
        if promotion_decision.candidate_id != candidate.candidate_id:
            raise ValueError(
                "promotion_decision.candidate_id 与 candidate.candidate_id 不一致"
            )

        hypothesis = candidate.hypothesis
        return ExperienceArtifact(
            artifact_type=ArtifactType.EXPERIENCE_RULE,
            name=hypothesis.action or candidate.candidate_id,
            rule=ArtifactRule(
                context=hypothesis.context,
                condition=hypothesis.condition,
                action=hypothesis.action,
            ),
            expected_outcome=hypothesis.expected_outcome,
            confidence=candidate.confidence,
            provenance=Provenance(
                source_type="promotion_decision",
                source_id=candidate.candidate_id,
            ),
        )
