"""ShanHai Experience Evolution — 候选经验生命周期层（见 ADR 0016 / 0017）。

Stage 2-b：把「候选经验」从 feedback 子模块演进为独立 Evolution Layer 核心，
建模 Candidate 的生命周期（Created → Evaluating → Validated/Rejected → Promoted，
Rejected 可 Reactivated/Archived），并以抽象边界冻结存储与验证/晋升入口。

依赖方向（ADR 0017 §4，单向不成环）：
    feedback ──► experience-evolution ──► experience（只读）
本包不依赖 feedback；experience 不依赖本包。

不在范围（持续冻结）：Artifact / Artifact Store / Vector / Graph / WeKnora /
llm-wiki / Knowledge Document / Summary generation / LLM promotion / Candidate persistence。
"""

from shanhai_experience_evolution.candidate import (
    ALLOWED_TRANSITIONS,
    ExperienceCandidate,
    is_allowed_transition,
)
from shanhai_experience_evolution.models import (
    Actor,
    CandidateSource,
    CandidateStatus,
    EvidenceRefs,
    Hypothesis,
    Lineage,
    SourceRefs,
    ValidationStats,
    ValidationVerdict,
)
from shanhai_experience_evolution.proposals import CandidateProposal
from shanhai_experience_evolution.repository import (
    CandidateRepository,
    InMemoryCandidateRepository,
)
from shanhai_experience_evolution.service import CandidateService, TransitionError

__all__ = [
    "Actor",
    "CandidateSource",
    "CandidateStatus",
    "Hypothesis",
    "SourceRefs",
    "EvidenceRefs",
    "ValidationStats",
    "ValidationVerdict",
    "Lineage",
    "ExperienceCandidate",
    "ALLOWED_TRANSITIONS",
    "is_allowed_transition",
    "CandidateRepository",
    "InMemoryCandidateRepository",
    "CandidateProposal",
    "CandidateService",
    "TransitionError",
]
