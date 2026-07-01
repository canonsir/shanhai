"""Knowledge Evolution 领域模型契约测试（S4.2-1，plain assert + main()）。

运行：
PYTHONPATH=services/market-data:services/market-intelligence:. \
    .venv/bin/python -m tests.market_intelligence.test_knowledge_evolution_contract

覆盖 S4.1 Review 指定的 6 个验收点 + 生命周期 + deterministic id：
  1. EvidenceRef 必须有 source（logical_key + content_hash 非空）
  2. Belief 无 evidence 不允许创建（evidence-first）
  3. Revision version 链正确（v1→v2，previous_version 指向）
  4. retire 不删除历史（旧版本仍含被 retire 的 belief）
  5. RevisionGate 不能改变内容（固化的 belief == proposed belief）
  6. Snapshot 不被引用（evolution 不 import context 侧 Snapshot 概念）
  + R5-1：KnowledgeObject 不拥有 Observation（无内嵌 observation 字段）
  + 生命周期状态机 ALLOWED_TRANSITIONS 合法/非法
  + deterministic id 复现（相同输入 → 相同 object_id / revision_id）
"""

from __future__ import annotations

import datetime

from shanhai_market_data.models import SubjectRef

from shanhai_market_intelligence.evolution import (
    ALLOWED_TRANSITIONS,
    Belief,
    BeliefDelta,
    BeliefStatement,
    CandidateRef,
    DeterministicRevisionGate,
    EvidenceRef,
    GateRejectReason,
    KnowledgeObject,
    ProposedRevision,
    RevisionState,
    assert_transition,
    build_next_version,
    derive_object_id,
    derive_revision_id,
)

_NOW = datetime.datetime(2026, 7, 1)
_SUBJECT = SubjectRef(entity_type="company", entity_id="600519")


def _evidence(logical_key: str = "lk-1", content_hash: str = "ch-1") -> EvidenceRef:
    return EvidenceRef(
        logical_key=logical_key, content_hash=content_hash, captured_at=_NOW
    )


def _belief(belief_id: str = "b1", *, evidence: tuple[EvidenceRef, ...] | None = None) -> Belief:
    return Belief(
        belief_id=belief_id,
        statement=BeliefStatement(dimension="moat", claim="竞争优势下降"),
        evidence_refs=evidence if evidence is not None else (_evidence(),),
    )


def _proposed(beliefs: tuple[Belief, ...], object_id: str) -> ProposedRevision:
    return ProposedRevision(
        candidate_id="cand-1",
        object_id=object_id,
        proposed_beliefs=beliefs,
        proposed_delta=BeliefDelta(added=tuple(b.belief_id for b in beliefs)),
    )


def _commit(current: KnowledgeObject | None, beliefs: tuple[Belief, ...]) -> KnowledgeObject:
    gate = DeterministicRevisionGate()
    object_id = current.object_id if current is not None else derive_object_id(_SUBJECT)
    result = gate.admit(
        _SUBJECT,
        current,
        _proposed(beliefs, object_id),
        CandidateRef(candidate_id="cand-1", hypothesis_version=1),
        as_of_knowledge_at=_NOW,
        now=_NOW,
    )
    assert result.admitted, f"expected admit, got reasons={result.reject_reasons}"
    assert result.knowledge_object is not None
    return result.knowledge_object


def test_evidence_ref_must_have_source() -> None:
    _evidence()  # 合法
    for bad in ("", "   "):
        try:
            EvidenceRef(logical_key=bad, content_hash="ch", captured_at=_NOW)
        except Exception:
            pass
        else:
            raise AssertionError("EvidenceRef 竟接受了空 logical_key（应要求 source）")
        try:
            EvidenceRef(logical_key="lk", content_hash=bad, captured_at=_NOW)
        except Exception:
            pass
        else:
            raise AssertionError("EvidenceRef 竟接受了空 content_hash（应要求 source）")
    print("[OK] Case 1：EvidenceRef 必须有 source")


def test_belief_without_evidence_is_invalid() -> None:
    _belief()  # 合法（默认带 evidence）
    try:
        _belief(evidence=())
    except Exception:
        pass
    else:
        raise AssertionError("Belief 竟允许无 evidence 创建（违反 evidence-first）")
    print("[OK] Case 2：Belief 无 evidence 不允许创建")


def test_revision_version_chain_is_correct() -> None:
    v1 = _commit(None, (_belief("b1"),))
    assert v1.version == 1, v1.version
    assert v1.previous_version is None
    v2 = _commit(v1, (_belief("b1"), _belief("b3", evidence=(_evidence("lk-3", "ch-3"),))))
    assert v2.version == 2, v2.version
    assert v2.previous_version is not None
    assert v2.previous_version.version == 1
    assert v2.previous_version.revision_id == v1.revision_id
    assert v2.object_id == v1.object_id  # 跨版本稳定
    print("[OK] Case 3：Revision version 链正确（v1→v2，previous 指向）")


def test_retire_does_not_delete_history() -> None:
    v1 = _commit(None, (_belief("b1"), _belief("b2", evidence=(_evidence("lk-2", "ch-2"),))))
    # v2 只保留 b1，retire b2（新版本不含 b2）
    v2 = _commit(v1, (_belief("b1"),))
    v2_belief_ids = {b.belief_id for b in v2.beliefs}
    assert "b2" not in v2_belief_ids, "v2 不应含被 retire 的 b2"
    v1_belief_ids = {b.belief_id for b in v1.beliefs}
    assert "b2" in v1_belief_ids, "retire != delete：v1 仍应含 b2（历史保留）"
    print("[OK] Case 4：retire 不删除历史（旧版本仍含被 retire 的 belief）")


def test_gate_does_not_change_content() -> None:
    b1 = _belief("b1")
    v1 = _commit(None, (b1,))
    assert len(v1.beliefs) == 1
    committed = v1.beliefs[0]
    # Gate 只固化不创作：内容逐字段等于 proposed 的 belief
    assert committed == b1, "RevisionGate 改变了 belief 内容（应只固化不创作）"
    print("[OK] Case 5：RevisionGate 不能改变内容")


def test_snapshot_is_not_referenced() -> None:
    """Case 6：evolution 子域源码不 import / 引用 context 侧 Snapshot 概念（D9）。

    结构层守护由 test_dependency_boundary.py 的 AST case 承担；此处从
    KnowledgeObject 字段角度断言无任何 snapshot/context 概念泄漏。
    """
    forbidden = {"snapshot", "context", "market_state", "cognition_state"}
    fields = set(KnowledgeObject.model_fields)
    leaked = {f for f in fields if any(term in f for term in forbidden)}
    assert not leaked, f"KnowledgeObject 泄漏了 context/snapshot 概念字段：{leaked}"
    print("[OK] Case 6：Snapshot 不被引用（KnowledgeObject 无 context/snapshot 字段）")


def test_knowledge_object_does_not_own_observation() -> None:
    """R5-1：KnowledgeObject 不拥有 Observation（只经 EvidenceRef 引用）。"""
    from shanhai_market_data.ports.observation_reader import Observation

    for name, field in KnowledgeObject.model_fields.items():
        annotation = str(field.annotation)
        assert "Observation" not in annotation or "EvidenceRef" in annotation, (
            f"KnowledgeObject.{name} 内嵌了 Observation（违反 R5-1，应只持 EvidenceRef）"
        )
    # evidence_refs 是 EvidenceRef，不是 Observation
    assert Observation is not None  # import 可用，仅确认类型存在
    print("[OK] R5-1：KnowledgeObject 不拥有 Observation（只引用 EvidenceRef）")


def test_lifecycle_transitions() -> None:
    assert_transition(RevisionState.proposed, RevisionState.reasoned)
    assert_transition(RevisionState.reasoned, RevisionState.committed)
    assert_transition(RevisionState.reasoned, RevisionState.rejected)
    # 非法：跳过 reasoning，或从终态迁出
    for current, target in (
        (RevisionState.proposed, RevisionState.committed),
        (RevisionState.committed, RevisionState.reasoned),
        (RevisionState.rejected, RevisionState.committed),
    ):
        try:
            assert_transition(current, target)
        except ValueError:
            pass
        else:
            raise AssertionError(f"非法迁移未被拒：{current} → {target}")
    # Gate 永远在 reasoned 之后（committed/rejected 是终态）
    assert ALLOWED_TRANSITIONS[RevisionState.committed] == frozenset()
    print("[OK] 生命周期：ALLOWED_TRANSITIONS 合法/非法均正确")


def test_deterministic_ids_reproduce() -> None:
    assert derive_object_id(_SUBJECT) == derive_object_id(_SUBJECT)
    ev = (_evidence(),)
    oid = derive_object_id(_SUBJECT)
    assert derive_revision_id(oid, 1, ev) == derive_revision_id(oid, 1, ev)
    # 相同输入两次 build → 相同 id
    v1a = build_next_version(
        subject=_SUBJECT, current=None, beliefs=(_belief(),),
        as_of_knowledge_at=_NOW, updated_at=_NOW,
    )
    v1b = build_next_version(
        subject=_SUBJECT, current=None, beliefs=(_belief(),),
        as_of_knowledge_at=_NOW, updated_at=_NOW,
    )
    assert v1a.object_id == v1b.object_id
    assert v1a.revision_id == v1b.revision_id
    print("[OK] deterministic id：相同输入 → 相同 object_id / revision_id")


def test_gate_rejects_missing_evidence_via_schema() -> None:
    """补充：Gate 对 delta 与 beliefs 不一致返回 schema_invalid（deterministic 拒因）。"""
    gate = DeterministicRevisionGate()
    oid = derive_object_id(_SUBJECT)
    proposed = ProposedRevision(
        candidate_id="c",
        object_id=oid,
        proposed_beliefs=(_belief("b1"),),
        proposed_delta=BeliefDelta(added=()),  # 未覆盖 b1
    )
    result = gate.admit(
        _SUBJECT, None, proposed,
        CandidateRef(candidate_id="c", hypothesis_version=1),
        as_of_knowledge_at=_NOW, now=_NOW,
    )
    assert not result.admitted
    assert GateRejectReason.schema_invalid in result.reject_reasons
    print("[OK] Gate：delta 与 beliefs 不一致 → schema_invalid（deterministic 拒）")


def main() -> None:
    test_evidence_ref_must_have_source()
    test_belief_without_evidence_is_invalid()
    test_revision_version_chain_is_correct()
    test_retire_does_not_delete_history()
    test_gate_does_not_change_content()
    test_snapshot_is_not_referenced()
    test_knowledge_object_does_not_own_observation()
    test_lifecycle_transitions()
    test_deterministic_ids_reproduce()
    test_gate_rejects_missing_evidence_via_schema()
    print("\nKnowledge Evolution 领域模型契约测试全部通过 ✅")


if __name__ == "__main__":
    main()
