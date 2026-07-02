"""Knowledge Evolution 领域模型契约测试（S4.2-1 + S4.2-2，plain assert + main()）。

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

S4.2-2（NoopReasoner，冻结未来智能插槽）追加：
  11. Reasoner 不改变 Candidate（candidate 内容 hash 前后一致；两次 reason 内容 hash 一致）
  12. Reasoner 替换不影响 Gate（NoopReasoner 与 FutureReasoner 都满足 ReasoningPort，
      产出的 ProposedRevision 走同一 Gate 输入协议、均被 admit）

S4.2-3（InMemoryEvolutionStore，append-only 演化历史）追加：
  13. append-only：save v1 → save v2 → get_history(object) == [v1, v2]
  14. 历史不可变：v1 append 后再 append v2，v1 记录保持不变（frozen + 副本返回）
  15. 不同 object 隔离：company_A / company_B 历史不混

S4.3（Knowledge Reference Resolution，Evolution → Context）追加：
  16. Evolution → Context reference：Revision → KnowledgeResolver → KnowledgeView（ref-only）
  17. 历史时点回放：resolve_at(T1) 得 v1；resolve_at(T2) 得 v1+v2（无 current truth）
"""

from __future__ import annotations

import datetime
import hashlib

from shanhai_market_data.models import SubjectRef

from shanhai_market_intelligence.evolution import (
    ALLOWED_TRANSITIONS,
    Belief,
    BeliefDelta,
    BeliefStatement,
    CandidateKnowledgeChange,
    CandidateRef,
    ChangeKind,
    DeterministicRevisionGate,
    EvidenceRef,
    GateRejectReason,
    InMemoryEvolutionStore,
    KnowledgeObject,
    KnowledgeResolver,
    KnowledgeRevision,
    NOOP_REASONING_MODE,
    NoopReasoner,
    ProposedRevision,
    ReasoningPort,
    ResolvedKnowledge,
    RevisionHypothesis,
    RevisionState,
    assert_transition,
    build_next_version,
    derive_belief_id,
    derive_object_id,
    derive_revision_id,
)
from shanhai_market_intelligence import KnowledgeView, build_knowledge_view

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


def _candidate(
    *, evidence: tuple[EvidenceRef, ...] | None = None
) -> CandidateKnowledgeChange:
    return CandidateKnowledgeChange(
        candidate_id="cand-1",
        subject=_SUBJECT,
        change_kind=ChangeKind.new_evidence,
        hypothesis=RevisionHypothesis(
            dimension="moat", claim="竞争优势下降", rationale="新公告披露产能扩张放缓"
        ),
        evidence_refs=evidence if evidence is not None else (_evidence(),),
        created_at=_NOW,
    )


def _content_hash(model: object) -> str:
    """基于 pydantic 稳定 JSON 序列化的内容指纹（frozen model 逐字段等价 → hash 等价）。"""
    payload = model.model_dump_json()  # type: ignore[attr-defined]
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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


def _revision(
    subject: SubjectRef,
    current: KnowledgeObject | None,
    beliefs: tuple[Belief, ...],
    *,
    now: datetime.datetime = _NOW,
    retired: tuple[str, ...] = (),
) -> tuple[KnowledgeRevision, KnowledgeObject]:
    """走一遍 Gate，返回 (KnowledgeRevision, KnowledgeObject@vN+1)（供 store 测试用）。

    ``now`` 决定 revision.created_at（Case 17 历史时点回放需要不同 created_at）；
    ``retired`` 记入 belief_delta.retired（Case 17 让 v2 显式 retire 旧 belief_id，
    Resolver 折叠 delta 时据此移除——delta 是演化的可审计事实，非从对象反推）。
    """
    gate = DeterministicRevisionGate()
    object_id = current.object_id if current is not None else derive_object_id(subject)
    proposed = ProposedRevision(
        candidate_id="cand-1",
        object_id=object_id,
        proposed_beliefs=beliefs,
        proposed_delta=BeliefDelta(
            added=tuple(b.belief_id for b in beliefs), retired=retired
        ),
    )
    result = gate.admit(
        subject,
        current,
        proposed,
        CandidateRef(candidate_id="cand-1", hypothesis_version=1),
        as_of_knowledge_at=now,
        now=now,
    )
    assert result.admitted, f"expected admit, got reasons={result.reject_reasons}"
    assert result.revision is not None and result.knowledge_object is not None
    return result.revision, result.knowledge_object


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


def test_reasoner_does_not_change_candidate() -> None:
    """S4.2-2 Case 11：Reasoner 不改变 Candidate（恒等映射，deterministic）。

        CandidateKnowledgeChange → NoopReasoner → ProposedRevision

    断言：
      - reason() 前后 candidate 内容 hash 不变（reasoner 不 mutate 输入）；
      - 两次 reason() 产出 ProposedRevision 内容 hash 一致（无随机/时间注入）；
      - evidence 直通（proposed belief 的 evidence_refs == candidate.evidence_refs）；
      - confidence 未计算（None，R4-3）；reasoning_mode 标记为 noop。
    """
    reasoner = NoopReasoner()
    assert isinstance(reasoner, ReasoningPort), "NoopReasoner 未满足 ReasoningPort 协议"

    candidate = _candidate()
    before = _content_hash(candidate)
    proposed_a = reasoner.reason(candidate)
    after = _content_hash(candidate)
    assert before == after, "NoopReasoner 改变了 candidate（应恒等、不 mutate 输入）"

    proposed_b = reasoner.reason(candidate)
    assert _content_hash(proposed_a) == _content_hash(proposed_b), (
        "NoopReasoner 非 deterministic：相同 candidate 两次 reason 内容 hash 不一致"
    )

    (belief,) = proposed_a.proposed_beliefs
    assert belief.evidence_refs == candidate.evidence_refs, "evidence 未直通（应原样透传）"
    assert belief.confidence is None, "NoopReasoner 不应计算 confidence（R4-3）"
    assert belief.statement.dimension == candidate.hypothesis.dimension
    assert belief.statement.claim == candidate.hypothesis.claim
    assert proposed_a.reasoning_mode == NOOP_REASONING_MODE
    assert proposed_a.reasoning_ref is None
    # belief_id deterministic 派生：与 candidate 独立复现一致
    assert belief.belief_id == derive_belief_id(candidate, candidate.evidence_refs)
    print("[OK] Case 11：Reasoner 不改变 Candidate（恒等 + deterministic，内容 hash 一致）")


def test_reasoner_swap_does_not_affect_gate() -> None:
    """S4.2-2 Case 12：Reasoner 替换不影响 Gate（Gate 输入协议稳定、可互换）。

        NoopReasoner ─┐
                      ├─► RevisionGate.admit（同一协议，均 admit）
        FutureReasoner┘

    构造一个「未来推理器」stub（改 confidence/reasoning_mode，模拟真实推理器差异），
    断言它同样满足 ReasoningPort，且 Gate 对两者产出的 ProposedRevision 都能 admit
    ——Gate 不感知 reasoner 身份，只做 deterministic 校验。
    """

    class _FutureReasoner:
        """未来 LLM 推理器占位（S4.2-2 不接 LLM，仅验证协议可互换）。"""

        def reason(self, candidate: CandidateKnowledgeChange) -> ProposedRevision:
            evidence_refs = candidate.evidence_refs
            belief = Belief(
                belief_id=derive_belief_id(candidate, evidence_refs),
                statement=BeliefStatement(
                    dimension=candidate.hypothesis.dimension,
                    claim=candidate.hypothesis.claim,
                ),
                evidence_refs=evidence_refs,
                confidence=0.87,  # 未来推理器可给分；Gate 仍不据此判定
            )
            return ProposedRevision(
                candidate_id=candidate.candidate_id,
                object_id=derive_object_id(candidate.subject),
                proposed_beliefs=(belief,),
                proposed_delta=BeliefDelta(added=(belief.belief_id,)),
                reasoning_mode="future-llm",
            )

    assert isinstance(NoopReasoner(), ReasoningPort)
    assert isinstance(_FutureReasoner(), ReasoningPort)

    candidate = _candidate()
    gate = DeterministicRevisionGate()
    triggered_by = CandidateRef(candidate_id=candidate.candidate_id, hypothesis_version=1)

    for reasoner in (NoopReasoner(), _FutureReasoner()):
        proposed = reasoner.reason(candidate)
        result = gate.admit(
            _SUBJECT,
            None,
            proposed,
            triggered_by,
            as_of_knowledge_at=_NOW,
            now=_NOW,
        )
        assert result.admitted, (
            f"Gate 拒了 {type(reasoner).__name__} 的产出（协议应稳定）："
            f"{result.reject_reasons}"
        )
        assert result.knowledge_object is not None
        assert result.knowledge_object.version == 1
    print("[OK] Case 12：Reasoner 替换不影响 Gate（协议稳定，NoopReasoner 与 Future 均 admit）")


def test_store_is_append_only_history() -> None:
    """S4.2-3 Case 13：append-only —— save v1 → save v2 → history == [v1, v2]（有序）。"""
    store = InMemoryEvolutionStore()
    rev1, v1 = _revision(_SUBJECT, None, (_belief("b1"),))
    rev2, _v2 = _revision(
        _SUBJECT, v1, (_belief("b1"), _belief("b3", evidence=(_evidence("lk-3", "ch-3"),)))
    )
    store.append_revision(rev1)
    store.append_revision(rev2)

    history = store.get_history(rev1.object_id)
    assert [r.to_version for r in history] == [1, 2], history
    assert history[0] == rev1 and history[1] == rev2
    # 结构性 append-only：没有 update/delete 入口（比运行时校验更强）
    assert not hasattr(store, "update_revision"), "EvolutionStore 不应有 update_revision"
    assert not hasattr(store, "delete_revision"), "EvolutionStore 不应有 delete_revision"
    # 也不做智能查询（真值选择 / 冲突消解属未来 Evolution Policy）
    for banned in ("find_best_belief", "latest_truth", "resolve_conflict"):
        assert not hasattr(store, banned), f"EvolutionStore 不应有智能查询 {banned}"
    print("[OK] Case 13：append-only（history==[v1,v2]，无 update/delete/智能查询）")


def test_store_history_is_immutable() -> None:
    """S4.2-3 Case 14：历史不可变 —— append v2 后 v1 记录保持不变。"""
    store = InMemoryEvolutionStore()
    rev1, v1 = _revision(_SUBJECT, None, (_belief("b1"),))
    store.append_revision(rev1)

    snapshot_before = _content_hash(store.get_history(rev1.object_id)[0])

    rev2, _v2 = _revision(_SUBJECT, v1, (_belief("b1"),))
    store.append_revision(rev2)

    history = store.get_history(rev1.object_id)
    snapshot_after = _content_hash(history[0])
    assert snapshot_before == snapshot_after, "append v2 改变了 v1 历史记录（应不可变）"

    # get_history 返回副本：外部改动不污染内部历史
    history.append(rev1)
    assert len(store.get_history(rev1.object_id)) == 2, "get_history 未返回副本（内部被污染）"
    print("[OK] Case 14：历史不可变（append v2 后 v1 记录不变；get_history 返回副本）")


def test_store_isolates_distinct_objects() -> None:
    """S4.2-3 Case 15：不同 object 隔离 —— company_A / company_B 历史不混。"""
    subject_a = SubjectRef(entity_type="company", entity_id="600519")
    subject_b = SubjectRef(entity_type="company", entity_id="000001")
    store = InMemoryEvolutionStore()

    rev_a, _ = _revision(subject_a, None, (_belief("ba"),))
    rev_b, _ = _revision(subject_b, None, (_belief("bb"),))
    store.append_revision(rev_a)
    store.append_revision(rev_b)

    assert rev_a.object_id != rev_b.object_id, "两个 subject 的 object_id 应不同"
    history_a = store.get_history(rev_a.object_id)
    history_b = store.get_history(rev_b.object_id)
    assert history_a == [rev_a], "company_A 历史混入了他者"
    assert history_b == [rev_b], "company_B 历史混入了他者"
    # 未知 object 返回空 list（不 raise）
    assert store.get_history("ko-unknown") == []
    print("[OK] Case 15：不同 object 隔离（company_A / company_B 历史不混）")


def test_evolution_to_context_reference() -> None:
    """S4.3 Case 16：Evolution → Context reference（Revision → Resolver → KnowledgeView）。

        KnowledgeRevision → KnowledgeResolver.resolve_at → ResolvedKnowledge
                                     → build_knowledge_view → KnowledgeView（ref-only）

    断言：
      - Resolver 从 store 折叠出 ResolvedKnowledge（version/revision_id/live_belief_ids/chain）；
      - KnowledgeView 是 ResolvedKnowledge 的纯投影（belief_ids == live_belief_ids）；
      - ref-only：KnowledgeView 无任何 belief 值字段（只 id / 版本引用）。
    """
    store = InMemoryEvolutionStore()
    rev1, v1 = _revision(_SUBJECT, None, (_belief("b1"),))
    store.append_revision(rev1)

    resolver = KnowledgeResolver(store)
    resolved = resolver.resolve_at(_SUBJECT, _NOW)
    assert isinstance(resolved, ResolvedKnowledge)
    assert resolved.object_id == rev1.object_id
    assert resolved.resolved_version == 1
    assert resolved.resolved_revision_id == rev1.revision_id
    assert resolved.live_belief_ids == ("b1",)
    assert [r.to_version for r in resolved.revision_chain] == [1]

    view = build_knowledge_view(resolved)
    assert isinstance(view, KnowledgeView)
    assert view.object_id == resolved.object_id
    assert view.subject == _SUBJECT
    assert view.resolved_version == 1
    assert view.resolved_revision_id == rev1.revision_id
    assert view.belief_ids == resolved.live_belief_ids
    assert view.knowledge_at == _NOW
    # ref-only：视图不内嵌 belief 值（只 belief_ids）
    fields = set(KnowledgeView.model_fields)
    assert "beliefs" not in fields and "belief" not in fields, (
        f"KnowledgeView 泄漏了 belief 值字段（应 ref-only）：{fields}"
    )
    print("[OK] Case 16：Evolution → Context reference（Resolver → ref-only KnowledgeView）")


def test_resolve_at_replays_by_knowledge_time() -> None:
    """S4.3 Case 17：历史时点回放 —— resolve_at(T1)=v1；resolve_at(T2)=v1+v2。

        knowledge_at=T1 → revision v1（live={b1}）
        knowledge_at=T2 → revision v1+v2（v2 retire b1、add b3 → live={b3}）

    证明「没有 current truth」：认知随 knowledge_at 变化，站在不同时点回看得到不同视图。
    T0（早于首个 revision）→ 空视图（resolved_version=None）。
    """
    t1 = datetime.datetime(2026, 1, 1)
    t2 = datetime.datetime(2026, 4, 1)
    store = InMemoryEvolutionStore()

    rev1, v1 = _revision(_SUBJECT, None, (_belief("b1"),), now=t1)
    # v2：retire b1、新增 b3（模拟「需求增长假设」被「价格战」替代）
    rev2, _v2 = _revision(
        _SUBJECT,
        v1,
        (_belief("b3", evidence=(_evidence("lk-3", "ch-3"),)),),
        now=t2,
        retired=("b1",),
    )
    store.append_revision(rev1)
    store.append_revision(rev2)

    resolver = KnowledgeResolver(store)

    # 站在 T0（早于任何 revision）：系统尚无认知
    at_t0 = resolver.resolve_at(_SUBJECT, datetime.datetime(2025, 12, 31))
    assert at_t0.resolved_version is None
    assert at_t0.resolved_revision_id is None
    assert at_t0.live_belief_ids == ()
    assert at_t0.revision_chain == ()

    # 站在 T1：只看到 v1
    at_t1 = resolver.resolve_at(_SUBJECT, t1)
    assert at_t1.resolved_version == 1
    assert at_t1.live_belief_ids == ("b1",)
    assert [r.to_version for r in at_t1.revision_chain] == [1]

    # 站在 T2：看到 v1+v2；b1 已 retire、b3 生效（delta 折叠）
    at_t2 = resolver.resolve_at(_SUBJECT, t2)
    assert at_t2.resolved_version == 2
    assert at_t2.resolved_revision_id == rev2.revision_id
    assert at_t2.live_belief_ids == ("b3",), "v2 应 retire b1、add b3（折叠后只剩 b3）"
    assert [r.to_version for r in at_t2.revision_chain] == [1, 2]

    # deterministic：同一 knowledge_at 两次 resolve 结果一致
    assert resolver.resolve_at(_SUBJECT, t2) == at_t2
    print("[OK] Case 17：历史时点回放（resolve_at(T1)=v1；resolve_at(T2)=v1+v2，无 current truth）")


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
    test_reasoner_does_not_change_candidate()
    test_reasoner_swap_does_not_affect_gate()
    test_store_is_append_only_history()
    test_store_history_is_immutable()
    test_store_isolates_distinct_objects()
    test_evolution_to_context_reference()
    test_resolve_at_replays_by_knowledge_time()
    print("\nKnowledge Evolution 领域模型契约测试全部通过 ✅")


if __name__ == "__main__":
    main()
