"""ExperienceCandidate 聚合与生命周期状态机（见 ADR 0017 Decision C/D/F，Stage 2-b）。

候选经验是 Evolution Layer 的核心实体（ADR 0017 Decision A：能力增强而非重命名/重建）。
本模块定义聚合本体与「合法状态转移表」。状态机是领域规则，故置于领域对象内；
但**权限校验与实际转移落地**由 CandidateService 统一承担（service.py），
任何调用方禁止直接赋值 candidate.validation_status（ADR 0017 §5 不变量）。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from shanhai_experience_evolution.models import (
    Actor,
    CandidateSource,
    CandidateStatus,
    EvidenceRefs,
    Hypothesis,
    Lineage,
    SourceRefs,
    ValidationStats,
)

# 合法状态转移表：(from_status, to_status, actor) ∈ 集合 才允许（ADR 0017 Stage 2-b 权限模型）。
#
# Producer 只能 create（产生 Created），不在转移表内——故 Created → 任何状态都不可由 Producer 执行。
# Validator：Created → Evaluating → Validated / Rejected，以及 Reactivated → Evaluating（重新进入验证）。
# PromotionGate：Validated → Promoted。
# System：Rejected → Reactivated / Archived（失效不删除，保留血缘）。
ALLOWED_TRANSITIONS: frozenset[tuple[CandidateStatus, CandidateStatus, Actor]] = frozenset(
    {
        (CandidateStatus.CREATED, CandidateStatus.EVALUATING, Actor.VALIDATOR),
        (CandidateStatus.EVALUATING, CandidateStatus.VALIDATED, Actor.VALIDATOR),
        (CandidateStatus.EVALUATING, CandidateStatus.REJECTED, Actor.VALIDATOR),
        (CandidateStatus.VALIDATED, CandidateStatus.PROMOTED, Actor.PROMOTION_GATE),
        (CandidateStatus.REJECTED, CandidateStatus.REACTIVATED, Actor.SYSTEM),
        (CandidateStatus.REJECTED, CandidateStatus.ARCHIVED, Actor.SYSTEM),
        (CandidateStatus.REACTIVATED, CandidateStatus.EVALUATING, Actor.VALIDATOR),
    }
)


def is_allowed_transition(
    from_status: CandidateStatus,
    to_status: CandidateStatus,
    actor: Actor,
) -> bool:
    """纯函数：判定某 actor 是否可执行某状态转移。不产生副作用。"""
    return (from_status, to_status, actor) in ALLOWED_TRANSITIONS


class ExperienceCandidate(BaseModel):
    """一条候选经验（Evolution Layer 核心实体，ADR 0017 Decision A）。

    持有可验证假设、来源/证据引用、验证统计与血缘。状态只经 CandidateService.transition
    迁移，apply_validation 更新统计；本类不自行决定权限（权限属 service 层）。
    """

    candidate_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    source: CandidateSource
    hypothesis: Hypothesis = Field(default_factory=Hypothesis)
    # 假设版本：Candidate 会演化（ADR 0017 Decision C），即「approved scope: version」。
    hypothesis_version: int = 1
    source_refs: SourceRefs = Field(default_factory=SourceRefs)
    evidence_refs: EvidenceRefs = Field(default_factory=EvidenceRefs)
    confidence: float = 0.0
    validation_status: CandidateStatus = CandidateStatus.CREATED
    validation_stats: ValidationStats = Field(default_factory=ValidationStats)
    lineage: Lineage = Field(default_factory=Lineage)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
