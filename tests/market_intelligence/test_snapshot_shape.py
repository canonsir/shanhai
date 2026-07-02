"""MarketContextSnapshot ref-based shape 守护测试（M3.4 S1，R1-3 防 God Object）。

运行：
PYTHONPATH=services/market-data:services/market-intelligence:. \
    .venv/bin/python -m tests.market_intelligence.test_snapshot_shape

断言 Snapshot 严格是 ref-based 认知快照，不是数据聚合容器：
  Case 1  字段恰为 7 认知内容 + 3 meta，无多余字段
  Case 2  extra="forbid" + frozen（不可平铺塞值、不可变）
  Case 3  无 financials/news/technical/chip 类按数据种类平铺的容器字段
  Case 4  domain 值对象均 frozen + extra=forbid（不可变认知）
  Case 5  ContextAssembler 骨架抛 NotImplementedError（S1 不落实现，S4 才实现）
  Case 19 S4.3-2 接缝：ContextAssembler 经注入的 KnowledgeViewReader 端口消费
          Evolution 认知视图（Store→Resolver→View→Assembler），view 仍不进 frozen
          snapshot（assemble 保持 NotImplementedError）；无 reader → None
"""

from __future__ import annotations

import datetime

from shanhai_market_data.models import SubjectRef

from shanhai_market_intelligence import (
    AsOf,
    CognitionRef,
    CognitionState,
    Conflict,
    ContextAssembler,
    DataQuality,
    KnowledgeRef,
    MarketContextSnapshot,
    MarketState,
    ObservationRef,
    build_knowledge_view,
)
from shanhai_market_intelligence.evolution import (
    Belief,
    BeliefDelta,
    BeliefStatement,
    CandidateRef,
    DeterministicRevisionGate,
    EvidenceRef,
    InMemoryEvolutionStore,
    KnowledgeResolver,
    ProposedRevision,
    derive_object_id,
)

COGNITION_FIELDS = {
    "subject",
    "as_of",
    "observation_refs",
    "knowledge_refs",
    "market_state",
    "cognition_state",
    "data_quality",
}
META_FIELDS = {"snapshot_id", "schema_version", "assembled_at"}

# 禁止出现的「今天有哪些数据」式平铺容器字段（R1-3）
FORBIDDEN_FLATTENED = {"financials", "news", "technical", "chip", "quotes", "data"}

_NOW = datetime.datetime(2026, 1, 1)


class _NoopReadPort:
    """空 ObservationReadPort stub（本文件无真实 observation，只验证认知视图接缝）。"""

    def query(self, subject, *, knowledge_at, effective_at=None, fact_types=()):
        return ()


def _sample_snapshot(**overrides) -> MarketContextSnapshot:
    kwargs = dict(
        subject=SubjectRef(entity_type="company", entity_id="c1"),
        as_of=AsOf(effective_at=_NOW, knowledge_at=_NOW),
        market_state=MarketState(),
        cognition_state=CognitionState(),
        data_quality=DataQuality(),
        snapshot_id="deadbeef",
        assembled_at=_NOW,
    )
    kwargs.update(overrides)
    return MarketContextSnapshot(**kwargs)


def test_snapshot_fields_are_exactly_seven_cognition_plus_three_meta() -> None:
    fields = set(MarketContextSnapshot.model_fields)
    assert fields == COGNITION_FIELDS | META_FIELDS, (
        f"MarketContextSnapshot 字段应恰为 7 认知 + 3 meta，实际：{sorted(fields)}"
    )
    print("[OK] Case 1：字段恰为 7 认知内容 + 3 meta")


def test_snapshot_forbids_flattened_data_containers() -> None:
    fields = set(MarketContextSnapshot.model_fields)
    leaked = fields & FORBIDDEN_FLATTENED
    assert not leaked, f"Snapshot 出现按数据种类平铺的容器字段（R1-3 禁止）：{leaked}"
    print("[OK] Case 3：无 financials/news/technical/chip 类平铺容器")


def test_snapshot_is_frozen_and_extra_forbid() -> None:
    config = MarketContextSnapshot.model_config
    assert config.get("frozen") is True, "Snapshot 必须 frozen（不可变认知）"
    assert config.get("extra") == "forbid", "Snapshot 必须 extra=forbid（不可平铺塞值）"

    snap = _sample_snapshot()

    # extra=forbid：不能塞入平铺数据字段
    try:
        _sample_snapshot(financials={"revenue": 100})
    except Exception:
        pass
    else:
        raise AssertionError("extra=forbid 未生效：Snapshot 竟接受了 financials 平铺字段")

    # frozen：不能改字段
    try:
        snap.snapshot_id = "other"  # type: ignore[misc]
    except Exception:
        pass
    else:
        raise AssertionError("frozen 未生效：Snapshot 字段竟可被修改")
    print("[OK] Case 2：extra=forbid + frozen（不可平铺塞值、不可变）")


def test_value_objects_are_frozen_extra_forbid() -> None:
    for model in (
        AsOf,
        ObservationRef,
        KnowledgeRef,
        MarketState,
        CognitionRef,
        CognitionState,
        Conflict,
        DataQuality,
        MarketContextSnapshot,
    ):
        config = model.model_config
        assert config.get("frozen") is True, f"{model.__name__} 必须 frozen"
        assert config.get("extra") == "forbid", f"{model.__name__} 必须 extra=forbid"
    print("[OK] Case 4：全部 domain 值对象 frozen + extra=forbid")


def test_assembler_skeleton_raises_not_implemented() -> None:
    """S1 边界：ContextAssembler.assemble 仍是骨架，抛 NotImplementedError（S4 实现）。"""

    assembler = ContextAssembler(_NoopReadPort())
    try:
        assembler.assemble(
            SubjectRef(entity_type="company", entity_id="c1"),
            AsOf(effective_at=_NOW, knowledge_at=_NOW),
        )
    except NotImplementedError:
        pass
    else:
        raise AssertionError("S1 边界破坏：assemble 应抛 NotImplementedError（S4 才实现）")
    print("[OK] Case 5：ContextAssembler 骨架抛 NotImplementedError（S1 不落实现）")


def test_assembler_consumes_knowledge_view_via_reader() -> None:
    """Case 19：ContextAssembler 经注入端口消费 Evolution 认知视图（S4.3-2 接缝）。

    端到端组合根（在 context 之外，允许知道两侧）：

        InMemoryEvolutionStore ─ append revision(v1: +b1)
                 │
        KnowledgeResolver.resolve_at(subject, knowledge_at)
                 │
        build_knowledge_view → KnowledgeView
                 │  （实现 KnowledgeViewReader 端口）
        ContextAssembler(knowledge_reader=...).knowledge_view_for(subject, as_of)

    断言：assembler 拿到的 view 的 belief_ids / version / knowledge_at 与 resolver 一致；
    无 reader 注入时返回 None；view **不进** frozen snapshot（assemble 仍 NotImplementedError）。
    """
    subject = SubjectRef(entity_type="company", entity_id="600519")
    evidence = EvidenceRef(logical_key="lk-1", content_hash="ch-1", captured_at=_NOW)
    belief = Belief(
        belief_id="b1",
        statement=BeliefStatement(dimension="moat", claim="竞争优势下降"),
        evidence_refs=(evidence,),
    )
    object_id = derive_object_id(subject)
    proposed = ProposedRevision(
        candidate_id="cand-1",
        object_id=object_id,
        proposed_beliefs=(belief,),
        proposed_delta=BeliefDelta(added=("b1",)),
    )
    result = DeterministicRevisionGate().admit(
        subject, None, proposed,
        CandidateRef(candidate_id="cand-1", hypothesis_version=1),
        as_of_knowledge_at=_NOW, now=_NOW,
    )
    assert result.admitted and result.revision is not None
    store = InMemoryEvolutionStore()
    store.append_revision(result.revision)

    class _ResolverBackedReader:
        """组合根 adapter：包 Resolver + build_knowledge_view，实现 KnowledgeViewReader。"""

        def __init__(self, store: InMemoryEvolutionStore) -> None:
            self._resolver = KnowledgeResolver(store)

        def view_for(self, subject: SubjectRef, as_of: AsOf):
            resolved = self._resolver.resolve_at(subject, as_of.knowledge_at)
            return build_knowledge_view(resolved)

    as_of = AsOf(effective_at=_NOW, knowledge_at=_NOW)

    # 有 reader：Context 经端口拿到 Evolution 折叠出的认知视图
    assembler = ContextAssembler(
        _NoopReadPort(), knowledge_reader=_ResolverBackedReader(store)
    )
    view = assembler.knowledge_view_for(subject, as_of)
    assert view is not None
    assert view.object_id == object_id
    assert view.resolved_version == 1
    assert view.belief_ids == ("b1",)
    assert view.knowledge_at == _NOW

    # 无 reader：不越界自造认知，返回 None
    assert ContextAssembler(_NoopReadPort()).knowledge_view_for(subject, as_of) is None

    # view 不进 frozen snapshot：assemble 仍未实现（S4.3-2 只落端口接缝）
    try:
        assembler.assemble(subject, as_of)
    except NotImplementedError:
        pass
    else:
        raise AssertionError("S4.3-2 边界破坏：KnowledgeView 不应折进 snapshot，assemble 应仍 NotImplementedError")
    print("[OK] Case 19：ContextAssembler 经端口消费 KnowledgeView（consumes not owns，view 不进 snapshot）")


def main() -> None:
    test_snapshot_fields_are_exactly_seven_cognition_plus_three_meta()
    test_snapshot_forbids_flattened_data_containers()
    test_snapshot_is_frozen_and_extra_forbid()
    test_value_objects_are_frozen_extra_forbid()
    test_assembler_skeleton_raises_not_implemented()
    test_assembler_consumes_knowledge_view_via_reader()
    print("\nMarketContextSnapshot ref-based shape 守护测试全部通过 ✅")


if __name__ == "__main__":
    main()
