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

    class _NoopPort:
        def query(self, subject, *, knowledge_at, effective_at=None, fact_types=()):
            return ()

    assembler = ContextAssembler(_NoopPort())
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


def main() -> None:
    test_snapshot_fields_are_exactly_seven_cognition_plus_three_meta()
    test_snapshot_forbids_flattened_data_containers()
    test_snapshot_is_frozen_and_extra_forbid()
    test_value_objects_are_frozen_extra_forbid()
    test_assembler_skeleton_raises_not_implemented()
    print("\nMarketContextSnapshot ref-based shape 守护测试全部通过 ✅")


if __name__ == "__main__":
    main()
