"""Evolution 版本链 + 生命周期：KnowledgeRevision、BeliefDelta、ProposedRevision、状态机。

S4.2-1 冻结的 6 个核心模型之一（``KnowledgeRevision``）及其配套：

- ``BeliefDelta``       —— 显式记录本次相对上一版本的信念变化（added/revised/retired）
- ``KnowledgeRevision`` —— 一次演化事件（从 vN 到 vN+1，append-only，禁覆盖）
- ``ProposedRevision``  —— ReasoningPort 产出的拟修订（Gate 的输入，见 gate.py）
- ``RevisionState`` + ``ALLOWED_TRANSITIONS`` + ``assert_transition`` —— 生命周期状态机

铁律：

- **版本链 append-only（S4.0 §3 / D7）**：``retire != delete``。retire 一条 belief
  只是「新版本不再包含它」，旧版本里它仍在——可回放「AI 当时为何持有该信念」。
- **状态机是最后一道机械门的上游**（S4.1 Review 点 2）：
  ``Proposed → Reasoned → Committed/Rejected``。``RevisionGate`` 只在 ``Reasoned``
  之后介入，**不拥有 Reasoning 状态**（不调 Reasoner、不判断合理性、不改 candidate）。
- **deterministic id 派生**：``object_id`` 只由 subject 决定（跨版本稳定）；
  ``revision_id`` 由 ``(object_id, version, evidence 身份集)`` 决定（每版本唯一、可复现）。

依赖方向：import evidence / models（同子域）+ market-data ``SubjectRef``；**禁** import
context 侧概念（D9）与 reasoning-engine（只依赖 ReasoningPort Protocol，见 reasoning 后续步）。
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import Enum

from shanhai_market_data.models import SubjectRef

from shanhai_market_intelligence.evolution.evidence import EvidenceRef, _FrozenModel
from shanhai_market_intelligence.evolution.models import (
    Belief,
    CandidateRef,
    KnowledgeObject,
    KnowledgeObjectRef,
)


class RevisionState(str, Enum):
    """Revision lifecycle 状态（S4.1 §5.2，单遍简化）。"""

    proposed = "proposed"  # CandidateKnowledgeChange 已提出，未推理
    reasoned = "reasoned"  # ProposedRevision 已产出（经 ReasoningPort）
    committed = "committed"  # 已固化为新版本（经 RevisionGate）
    rejected = "rejected"  # 被 RevisionGate 拒绝（deterministic 拒因）


# 状态只能单向推进；Reasoning 在 proposed→reasoned，Gate 在 reasoned→committed/rejected。
# committed / rejected 是终态（本轮不实现 Archived/Reactivated 回退，S4.1 §5.2 记录）。
ALLOWED_TRANSITIONS: dict[RevisionState, frozenset[RevisionState]] = {
    RevisionState.proposed: frozenset({RevisionState.reasoned}),
    RevisionState.reasoned: frozenset({RevisionState.committed, RevisionState.rejected}),
    RevisionState.committed: frozenset(),
    RevisionState.rejected: frozenset(),
}


def assert_transition(current: RevisionState, target: RevisionState) -> None:
    """校验一次状态迁移是否合法；非法则 raise（守护生命周期不被绕过）。"""
    if target not in ALLOWED_TRANSITIONS[current]:
        raise ValueError(
            f"非法 Revision 状态迁移：{current.value} → {target.value}"
            f"（允许：{sorted(s.value for s in ALLOWED_TRANSITIONS[current])}）"
        )


class BeliefDelta(_FrozenModel):
    """显式记录本次相对上一版本的信念变化（不靠 diff 反推，可审计）。"""

    added: tuple[str, ...] = ()  # 新增 belief_id
    revised: tuple[str, ...] = ()  # confidence/scope 变化的 belief_id
    retired: tuple[str, ...] = ()  # 不再持有的 belief_id（retire != delete）


class ProposedRevision(_FrozenModel):
    """ReasoningPort 产出的拟修订（Gate 的输入）。

    每条 ``proposed_beliefs`` 已在 ``Belief`` 层强制 evidence 非空（evidence-first）；
    ``reasoning_ref`` 属 M3.7，本步为 None。
    """

    candidate_id: str
    object_id: str
    proposed_beliefs: tuple[Belief, ...]
    proposed_delta: BeliefDelta
    reasoning_ref: str | None = None


class KnowledgeRevision(_FrozenModel):
    """一次演化事件的记录（从 vN 到 vN+1，本身也 append-only，S4.0 §3）。"""

    revision_id: str  # = 新版本的 revision_id
    object_id: str
    from_version: int | None  # None = 初次创建（v1）
    to_version: int  # from_version + 1（或 1）
    triggered_by: CandidateRef  # 哪个 Candidate 触发（来源）
    reasoning_ref: str | None = None  # M3.7；本步 None
    belief_delta: BeliefDelta
    created_at: datetime


# ── deterministic id 派生（可复现锚点，S4.1 §5.3）────────────────────────


def _digest(payload: object) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def derive_object_id(subject: SubjectRef) -> str:
    """跨版本稳定：只由 subject 身份决定（同一 subject 所有版本共享）。"""
    return "ko-" + _digest([subject.entity_type, subject.entity_id])[:32]


def _evidence_identity_set(evidence_refs: tuple[EvidenceRef, ...]) -> list[list[str]]:
    """evidence 的排序身份集（与顺序无关的确定性指纹输入）。"""
    return sorted(
        [ref.logical_key, ref.content_hash] for ref in evidence_refs
    )


def derive_revision_id(
    object_id: str, version: int, evidence_refs: tuple[EvidenceRef, ...]
) -> str:
    """每版本唯一：由 (object_id, version, evidence 身份集) 决定，可确定性复现。"""
    return "rev-" + _digest(
        [object_id, version, _evidence_identity_set(evidence_refs)]
    )[:32]


def union_evidence_refs(beliefs: tuple[Belief, ...]) -> tuple[EvidenceRef, ...]:
    """对象级 evidence = 各 belief evidence 的并集（去重，稳定排序）。"""
    seen: dict[tuple[str, str], EvidenceRef] = {}
    for belief in beliefs:
        for ref in belief.evidence_refs:
            seen.setdefault((ref.logical_key, ref.content_hash), ref)
    return tuple(
        seen[key] for key in sorted(seen, key=lambda k: (k[0], k[1]))
    )


def build_next_version(
    *,
    subject: SubjectRef,
    current: KnowledgeObject | None,
    beliefs: tuple[Belief, ...],
    as_of_knowledge_at: datetime,
    updated_at: datetime,
) -> KnowledgeObject:
    """从 current（可为 None）+ 新 beliefs 构造 vN+1（不修改 current，append 语义）。

    这是 KnowledgeObject 版本的**唯一确定性构造函数**；由 ``RevisionGate`` 在校验通过后
    调用（gate.py）。调用方**禁**绕过 Gate 直接调本函数造版本。
    """
    object_id = derive_object_id(subject)
    version = (current.version + 1) if current is not None else 1
    evidence_refs = union_evidence_refs(beliefs)
    revision_id = derive_revision_id(object_id, version, evidence_refs)
    previous = (
        KnowledgeObjectRef(
            object_id=current.object_id,
            version=current.version,
            revision_id=current.revision_id,
        )
        if current is not None
        else None
    )
    return KnowledgeObject(
        subject=subject,
        version=version,
        previous_version=previous,
        beliefs=beliefs,
        evidence_refs=evidence_refs,
        confidence=None,  # 本步不聚合（R4-3）
        as_of_knowledge_at=as_of_knowledge_at,
        updated_at=updated_at,
        object_id=object_id,
        revision_id=revision_id,
    )
