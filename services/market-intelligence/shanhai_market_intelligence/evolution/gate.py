"""Evolution 机械门：RevisionGate —— KnowledgeObject 的唯一写入口，deterministic。

S4.2-1 冻结的 6 个核心模型之一（``RevisionGateResult``）及其判定器。

铁律（S4.1 Review 点 2 + R4-2）：

- **Gate 永远是最后一道机械门**：输入是**已经过 reasoning 的** ``ProposedRevision``。
  Gate **不拥有 Reasoning 状态**——不调用 Reasoner、不判断合理性、不修改 candidate/内容。
  正确链路：``Candidate → ReasoningPort → ProposedRevision → RevisionGate → KnowledgeRevision``。
- **只做机械可判定校验（R4-2）**：``evidence exists? / schema valid? / version conflict? /
  provenance complete?``。**禁**任何需理解的判断（``is this belief reasonable?`` /
  ``is this company good?``——那属 Reasoning Engine / M3.7）。
- **只固化不创作**（继承 ADR 0017 Promotion Gate / 0018 ArtifactBuilder）：只把已校验的
  ``proposed`` 固化为 vN+1，不新增/改写信念内容，不携带 LLM 自由文本。
- **唯一写入口**：任何 KnowledgeObject 版本都必须经 ``admit``；``build_next_version``
  只在此被调用。

依赖方向：import evidence / models / revision（同子域）；**禁** import context 侧概念
（D9）与 reasoning-engine。``EvidenceResolver`` 是可选注入（S4.2-1 不接 adapter，仅结构
校验；可解析性校验在注入 resolver 后生效）。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Protocol, runtime_checkable

from shanhai_market_data.models import SubjectRef

from shanhai_market_intelligence.evolution.evidence import (
    EvidenceResolver,
    _FrozenModel,
)
from shanhai_market_intelligence.evolution.models import (
    CandidateRef,
    KnowledgeObject,
)
from shanhai_market_intelligence.evolution.revision import (
    KnowledgeRevision,
    ProposedRevision,
    build_next_version,
)


class GateRejectReason(str, Enum):
    """Gate 的 deterministic 拒因（只表机械可判定失败）。"""

    evidence_missing = "evidence_missing"  # 某 belief evidence_refs 为空
    evidence_unresolvable = "evidence_unresolvable"  # evidence 指向的 observation 不存在
    schema_invalid = "schema_invalid"  # proposed 结构不合契约（如 delta 与 beliefs 不一致）
    version_conflict = "version_conflict"  # to_version 与 current 版本链冲突
    provenance_incomplete = "provenance_incomplete"  # evidence 身份缺失


class RevisionGateResult(_FrozenModel):
    """Gate 的唯一出口形状（R4-2）：判定 + 已固化版本；不携带 LLM 自由文本。"""

    admitted: bool
    reject_reasons: tuple[GateRejectReason, ...] = ()  # admitted=True 时为空
    revision: KnowledgeRevision | None = None  # admitted=True 时非 None
    knowledge_object: KnowledgeObject | None = None  # admitted=True 时 = 新版本 vN+1


@runtime_checkable
class RevisionGate(Protocol):
    def admit(
        self,
        subject: SubjectRef,
        current: KnowledgeObject | None,
        proposed: ProposedRevision,
        triggered_by: CandidateRef,
        *,
        as_of_knowledge_at: datetime,
        now: datetime,
    ) -> RevisionGateResult: ...


class DeterministicRevisionGate:
    """S4.2-1 参考实现：只做 deterministic 校验，只固化不创作（R4-2）。

    ``resolver`` 可选：未注入时只做结构性 + provenance 校验（本步不接 observation
    adapter）；注入后额外做「evidence 指向真实 observation」的可解析性校验。
    """

    def __init__(self, resolver: EvidenceResolver | None = None) -> None:
        self._resolver = resolver

    def admit(
        self,
        subject: SubjectRef,
        current: KnowledgeObject | None,
        proposed: ProposedRevision,
        triggered_by: CandidateRef,
        *,
        as_of_knowledge_at: datetime,
        now: datetime,
    ) -> RevisionGateResult:
        reasons: list[GateRejectReason] = []

        # 1. evidence exists?（每条 proposed belief 必须有 evidence）
        #    Belief 构造已强制非空；此处对 proposed 再机械核验一遍（防绕过构造）。
        for belief in proposed.proposed_beliefs:
            if not belief.evidence_refs:
                reasons.append(GateRejectReason.evidence_missing)
                break

        # 2. provenance complete?（evidence 身份 logical_key/content_hash 非空）
        for belief in proposed.proposed_beliefs:
            for ref in belief.evidence_refs:
                if not ref.logical_key.strip() or not ref.content_hash.strip():
                    reasons.append(GateRejectReason.provenance_incomplete)
                    break
            else:
                continue
            break

        # 3. evidence resolvable?（注入 resolver 时才校验，S4.2-1 不接 adapter）
        if self._resolver is not None:
            for belief in proposed.proposed_beliefs:
                if any(not self._resolver.exists(ref) for ref in belief.evidence_refs):
                    reasons.append(GateRejectReason.evidence_unresolvable)
                    break

        # 4. schema valid?（proposed_delta.added 应覆盖 proposed_beliefs 的 belief_id）
        proposed_ids = {b.belief_id for b in proposed.proposed_beliefs}
        delta_ids = set(proposed.proposed_delta.added)
        if not proposed_ids.issubset(delta_ids):
            reasons.append(GateRejectReason.schema_invalid)

        # 5. version conflict?（proposed.object_id 必须与 current 一致，若有 current）
        if current is not None and proposed.object_id != current.object_id:
            reasons.append(GateRejectReason.version_conflict)

        if reasons:
            # 去重且保持稳定顺序
            seen: list[GateRejectReason] = []
            for r in reasons:
                if r not in seen:
                    seen.append(r)
            return RevisionGateResult(admitted=False, reject_reasons=tuple(seen))

        # 全过 → 固化 vN+1（只固化不创作：内容来自 proposed，不新增/改写）
        knowledge_object = build_next_version(
            subject=subject,
            current=current,
            beliefs=proposed.proposed_beliefs,
            as_of_knowledge_at=as_of_knowledge_at,
            updated_at=now,
        )
        revision = KnowledgeRevision(
            revision_id=knowledge_object.revision_id,
            object_id=knowledge_object.object_id,
            from_version=current.version if current is not None else None,
            to_version=knowledge_object.version,
            triggered_by=triggered_by,
            reasoning_ref=proposed.reasoning_ref,
            belief_delta=proposed.proposed_delta,
            created_at=now,
        )
        return RevisionGateResult(
            admitted=True,
            revision=revision,
            knowledge_object=knowledge_object,
        )
