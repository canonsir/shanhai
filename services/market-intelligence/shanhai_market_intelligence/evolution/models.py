"""Evolution 核心领域模型：evidence-bound、versioned 的解释性认知资产。

S4.2-1 冻结的 6 个核心模型中的前 4 个（其余 ``KnowledgeRevision`` /
``RevisionGateResult`` 见 revision.py / gate.py）：

- ``Belief``            —— evidence-bound 结构化信念（无证据不允许创建，evidence-first）
- ``KnowledgeObject``   —— 以 subject 为中心、versioned 的信念聚合（**不拥有** observation）
- ``CandidateKnowledgeChange`` —— 结构化「信念修订候选」= 可验证假设（非 summary）
- （``EvidenceRef`` 见 evidence.py）

铁律（本模块护栏）：

- **Evidence-first**：``Belief.evidence_refs`` 非空是构造前置条件。
  ``Belief(statement=..., evidence_refs=[])`` 直接 invalid（区分 AI Agent 与
  AI Native Knowledge System）。
- **R5-1（不拥有 observation）**：``KnowledgeObject`` 只持 ``EvidenceRef``（身份引用），
  **禁** ``observations: list[Observation]`` 或任何内嵌 observation 值的字段。
- **confidence 延迟设计（S4.1 Review 点 5 / R4-3）**：``confidence: float | None``，
  **本步不计算**（无 source_weight × model_score × … 聚合）。默认 ``None`` = 未评估。
- **结构化信念而非 summary**：``BeliefStatement.claim`` 是受控主张；``summary`` 若保留
  仅人类可读派生视图，不作语义/匹配依据。禁 KnowledgeSummary/KnowledgeCard/Insight
  这类 UI/输出层概念混入核心资产。

依赖方向：本模块 import market-data（``SubjectRef``，下游 import 上游，允许）；
**禁** import context 侧任何概念（``MarketContextSnapshot`` / ``ContextAssembler`` /
``AsOf`` 等，D9 / R4-1，AST 守护）。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from shanhai_market_data.models import SubjectRef

from shanhai_market_intelligence.evolution.evidence import EvidenceRef, _FrozenModel


class BeliefPolarity(str, Enum):
    """信念立场。"""

    supportive = "supportive"
    cautionary = "cautionary"
    neutral = "neutral"


class ChangeKind(str, Enum):
    """候选修订的性质（触发解释性演化的原因）。"""

    new_evidence = "new_evidence"
    conflict = "conflict"
    gap = "gap"


class BeliefStatement(_FrozenModel):
    """结构化信念主张（杜绝退化为自由文本 summary）。"""

    dimension: str  # profitability / moat / valuation_regime …
    claim: str  # 结构化 / 受控主张，非任意长文


class Belief(_FrozenModel):
    """evidence-bound 的结构化信念（S4.0 §2）。

    ``evidence_refs`` 必须非空——一条没有证据支撑的信念不允许存在（evidence-first）。
    ``confidence`` 是 ``float | None``：本步不计算聚合，``None`` 表示未评估。
    """

    belief_id: str
    statement: BeliefStatement
    evidence_refs: tuple[EvidenceRef, ...]  # 必须非空（下方 validator）
    confidence: float | None = None  # 延迟设计（Review 点 5 / R4-3）：不计算
    polarity: BeliefPolarity = BeliefPolarity.neutral

    def model_post_init(self, __context: object) -> None:
        if not self.evidence_refs:
            raise ValueError(
                f"Belief({self.belief_id!r}) 无证据不允许创建"
                "（evidence-first：evidence_refs 必须非空）"
            )


class KnowledgeObjectRef(_FrozenModel):
    """指向某个 KnowledgeObject 版本（版本链锚点）。"""

    object_id: str
    version: int
    revision_id: str


class KnowledgeObject(_FrozenModel):
    """以 subject 为中心、evidence-bound、versioned 的解释性认知资产（S4.0 §2）。

    **不拥有 observation**（R5-1）：``evidence_refs`` 只是各 belief 证据身份的并集
    （引用），不内嵌 observation 值。``object_id`` 跨版本稳定，``revision_id`` 每版本
    唯一（deterministic 派生见 revision.py）。
    """

    subject: SubjectRef
    version: int  # v1=1, v2=2 …
    previous_version: KnowledgeObjectRef | None = None  # v1 为 None（版本链锚点）
    beliefs: tuple[Belief, ...] = ()
    evidence_refs: tuple[EvidenceRef, ...] = ()  # 各 belief evidence 的并集（引用）
    confidence: float | None = None  # 对象级置信度：本步不聚合（R4-3）
    as_of_knowledge_at: datetime  # 本版本采纳的 observation 截止线（对齐 0019 D5）
    updated_at: datetime
    object_id: str  # deterministic from subject —— 跨版本稳定
    revision_id: str  # deterministic from (object_id, version, evidence 身份集)


class RevisionHypothesis(_FrozenModel):
    """候选携带的结构化假设（拟修订什么信念、为何）——非 summary。"""

    dimension: str
    claim: str
    rationale: str  # 人类可读，不作语义载体


class CandidateRef(_FrozenModel):
    """指向一个候选（含假设版本）。"""

    candidate_id: str
    hypothesis_version: int


class CandidateKnowledgeChange(_FrozenModel):
    """结构化「信念修订候选」= 可验证假设（S4.0 §5，镜像 ExperienceCandidate）。

    ``source_refs``（触发此候选的 observation）与 ``evidence_refs``（可用于验证的
    observation）分离（对齐 ADR 0017 Decision C）。候选自身可演化（``hypothesis_version``）。
    """

    candidate_id: str
    subject: SubjectRef
    change_kind: ChangeKind
    hypothesis: RevisionHypothesis
    source_refs: tuple[EvidenceRef, ...] = ()  # 来源
    evidence_refs: tuple[EvidenceRef, ...] = ()  # 证据（与 source 分离）
    hypothesis_version: int = 1
    created_at: datetime
