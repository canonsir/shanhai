"""ShanHai Market Intelligence — Evolution 子域（S4，见 ADR 0020 + S4.0/S4.1 设计）。

Knowledge Evolution：认知**如何变化**（与 context/ 的「当前认知视图」生命周期不同，
二者并列、互不合并）。核心链路：

    Observation → CandidateKnowledgeChange → ReasoningPort → ProposedRevision
        → RevisionGate → KnowledgeRevision → KnowledgeObject@vN+1（版本链）

S4.2-1（本步）范围：Domain Model Implementation —— 6 个核心模型 + evidence-first
校验 + 版本链构造 + 生命周期状态机 + DeterministicRevisionGate。**不做** SQLite /
Repository / Reasoner / LLM / Observation adapter / iFinD / Wind。

核心资产命名只有 Evidence / Knowledge / Revision / Context / Decision；禁
KnowledgeSummary/KnowledgeCard/Insight/AIReport 这类 UI/输出层概念（S4.1 Review 点 3）。
"""

from shanhai_market_intelligence.evolution.evidence import (
    EvidenceRef,
    EvidenceRelation,
    EvidenceResolver,
)
from shanhai_market_intelligence.evolution.gate import (
    DeterministicRevisionGate,
    GateRejectReason,
    RevisionGate,
    RevisionGateResult,
)
from shanhai_market_intelligence.evolution.models import (
    Belief,
    BeliefPolarity,
    BeliefStatement,
    CandidateKnowledgeChange,
    CandidateRef,
    ChangeKind,
    KnowledgeObject,
    KnowledgeObjectRef,
    RevisionHypothesis,
)
from shanhai_market_intelligence.evolution.revision import (
    ALLOWED_TRANSITIONS,
    BeliefDelta,
    KnowledgeRevision,
    ProposedRevision,
    RevisionState,
    assert_transition,
    build_next_version,
    derive_object_id,
    derive_revision_id,
    union_evidence_refs,
)

__all__ = [
    # evidence
    "EvidenceRef",
    "EvidenceRelation",
    "EvidenceResolver",
    # models
    "Belief",
    "BeliefStatement",
    "BeliefPolarity",
    "ChangeKind",
    "KnowledgeObject",
    "KnowledgeObjectRef",
    "CandidateKnowledgeChange",
    "CandidateRef",
    "RevisionHypothesis",
    # revision + lifecycle
    "BeliefDelta",
    "KnowledgeRevision",
    "ProposedRevision",
    "RevisionState",
    "ALLOWED_TRANSITIONS",
    "assert_transition",
    "build_next_version",
    "derive_object_id",
    "derive_revision_id",
    "union_evidence_refs",
    # gate
    "RevisionGate",
    "RevisionGateResult",
    "GateRejectReason",
    "DeterministicRevisionGate",
]
