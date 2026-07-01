"""InMemory == SQLite ObservationReadPort parity 行为测试（M3.4 S3）。

运行：
PYTHONPATH=services/market-data:. \
    .venv/bin/python -m tests.market_data.test_observation_read_port_parity

S3-2 冻结：两个 ``ObservationReadPort`` 实现对同一
``(subject, knowledge_at, effective_at, fact_types)`` 查询返回**逐字段相等**的
结果。S2 的 ``InMemoryObservationReadPort`` 是参考基线，SQLite 必须与之对齐：
  Case 1  parity 矩阵：多组 (knowledge_at, fact_types) 逐字段相等
  Case 2  排序稳定性（S3-3）：同 captured_at 多行，两端顺序一致且与插入顺序无关
  Case 3  subject.label roundtrip：SQLite 经 attributes JSON 重建 label 与 InMemory 相等
  Case 4  None 字段 roundtrip：predicate/object_value/occurred_at/published_at 为 None 对齐
  Case 5  source_ref + datetime(tz) roundtrip：SourceRef 与 tz-aware captured_at 逐字段相等
  Case 6  append-only 全历史（S3-2）：同 logical_key 多 content_hash 全返回，非 latest
  Case 7  record 幂等于 (logical_key, content_hash)
  Case 8  effective_at 接受但不解释（与 InMemory 一致的 defer）
  Case 9  runtime_checkable：SQLite 适配器 isinstance(ObservationReadPort)
  Case 10 S3-1 零 schema 变更：knowledge_observation 列集恒定，无 observation_history
          表、无 effective_at 索引
"""

from __future__ import annotations

from datetime import datetime, timezone

from shanhai_market_data.models import FactType, SourceRef, SubjectRef
from shanhai_market_data.ports import (
    InMemoryObservationReadPort,
    Observation,
    ObservationReadPort,
    SQLiteObservationReadPort,
)


def _dt(day: int, *, hour: int = 0) -> datetime:
    return datetime(2026, 3, day, hour, tzinfo=timezone.utc)


_MAOTAI = SubjectRef(entity_type="company", entity_id="c-600519", label="贵州茅台")
_OTHER = SubjectRef(entity_type="company", entity_id="c-000001", label="平安银行")
_NO_LABEL = SubjectRef(entity_type="company", entity_id="c-600519")


def _obs(
    *,
    logical_key: str,
    content_hash: str,
    subject: SubjectRef = _MAOTAI,
    fact_type: FactType = FactType.INDUSTRY,
    captured_at: datetime,
    predicate: str | None = None,
    object_value: str | None = None,
    occurred_at: datetime | None = None,
    published_at: datetime | None = None,
    confidence: float = 1.0,
    source_ref: SourceRef | None = None,
) -> Observation:
    return Observation(
        logical_key=logical_key,
        content_hash=content_hash,
        fact_type=fact_type,
        subject=subject,
        predicate=predicate,
        object_value=object_value,
        occurred_at=occurred_at,
        published_at=published_at,
        captured_at=captured_at,
        confidence=confidence,
        source_ref=source_ref
        or SourceRef(source_id="test", source_name="test", captured_at=_dt(1)),
    )


def _both(observations: tuple[Observation, ...]) -> tuple[
    InMemoryObservationReadPort, SQLiteObservationReadPort
]:
    """同一批 observation 灌入两个后端，返回 (InMemory, SQLite)。"""
    mem = InMemoryObservationReadPort()
    mem.record_many(observations)
    sql = SQLiteObservationReadPort(path=":memory:")
    sql.record_many(observations)
    return mem, sql


def _seed() -> tuple[Observation, ...]:
    rich_source = SourceRef(
        source_id="ifind",
        source_name="同花顺 iFinD",
        external_id="600519.SH",
        captured_at=_dt(1, hour=9),
        provider="ifind",
        dataset="basic",
        version="v2",
        hash="abc123",
    )
    return (
        _obs(
            logical_key="k-industry",
            content_hash="h1",
            captured_at=_dt(1),
            predicate="belongs_to_industry",
            object_value="白酒",
            occurred_at=_dt(1),
            published_at=_dt(1),
            confidence=0.9,
            source_ref=rich_source,
        ),
        _obs(
            logical_key="k-industry",
            content_hash="h2",
            captured_at=_dt(3),
            object_value="白酒（更名）",
        ),
        _obs(
            logical_key="k-fin",
            content_hash="hf",
            fact_type=FactType.FINANCIAL,
            captured_at=_dt(2),
        ),
        _obs(
            logical_key="k-other",
            content_hash="ho",
            subject=_OTHER,
            captured_at=_dt(2),
        ),
    )


def _assert_equal(
    mem: ObservationReadPort,
    sql: ObservationReadPort,
    subject: SubjectRef,
    *,
    knowledge_at: datetime,
    effective_at: datetime | None = None,
    fact_types: tuple[FactType, ...] = (),
) -> tuple[Observation, ...]:
    a = mem.query(
        subject, knowledge_at=knowledge_at, effective_at=effective_at, fact_types=fact_types
    )
    b = sql.query(
        subject, knowledge_at=knowledge_at, effective_at=effective_at, fact_types=fact_types
    )
    assert a == b, f"parity mismatch\n InMemory={a}\n SQLite  ={b}"
    return a


def test_parity_matrix() -> None:
    mem, sql = _both(_seed())
    for knowledge_at in (_dt(1), _dt(2), _dt(3), _dt(30)):
        for fact_types in ((), (FactType.INDUSTRY,), (FactType.FINANCIAL,),
                            (FactType.INDUSTRY, FactType.FINANCIAL)):
            for subject in (_MAOTAI, _OTHER):
                _assert_equal(
                    mem, sql, subject, knowledge_at=knowledge_at, fact_types=fact_types
                )
    print("[OK] Case 1：parity 矩阵逐字段相等（knowledge_at × fact_types × subject）")


def test_order_stability_same_captured_at() -> None:
    # 三条同 captured_at 观测，正/反两种插入顺序灌两后端，四路结果必须全等。
    obs = (
        _obs(logical_key="c", content_hash="3", captured_at=_dt(5)),
        _obs(logical_key="a", content_hash="1", captured_at=_dt(5)),
        _obs(logical_key="b", content_hash="2", captured_at=_dt(5)),
    )
    mem_f, sql_f = _both(obs)
    mem_r, sql_r = _both(tuple(reversed(obs)))
    forward = _assert_equal(mem_f, sql_f, _MAOTAI, knowledge_at=_dt(30))
    reverse = _assert_equal(mem_r, sql_r, _MAOTAI, knowledge_at=_dt(30))
    assert forward == reverse, "排序应与插入顺序无关"
    assert [o.logical_key for o in forward] == ["a", "b", "c"], "tie-break 按 logical_key 升序"
    print("[OK] Case 2：排序稳定性（同 captured_at；插入顺序无关；两端一致）")


def test_subject_label_roundtrip() -> None:
    mem, sql = _both((_obs(logical_key="k", content_hash="h", captured_at=_dt(1)),))
    result = _assert_equal(mem, sql, _MAOTAI, knowledge_at=_dt(30))
    assert result[0].subject.label == "贵州茅台", "SQLite 须经 attributes JSON 重建 label"
    print("[OK] Case 3：subject.label roundtrip 相等")


def test_none_fields_roundtrip() -> None:
    mem, sql = _both(
        (
            _obs(
                logical_key="k",
                content_hash="h",
                subject=_NO_LABEL,  # label=None
                captured_at=_dt(1),
                predicate=None,
                object_value=None,
                occurred_at=None,
                published_at=None,
            ),
        )
    )
    result = _assert_equal(mem, sql, _NO_LABEL, knowledge_at=_dt(30))
    o = result[0]
    assert o.subject.label is None
    assert o.predicate is None and o.object_value is None
    assert o.occurred_at is None and o.published_at is None
    print("[OK] Case 4：None 字段 roundtrip 对齐（label/predicate/object_value/时间）")


def test_source_ref_and_tz_roundtrip() -> None:
    mem, sql = _both(_seed())
    result = _assert_equal(mem, sql, _MAOTAI, knowledge_at=_dt(1))
    o = result[0]
    assert o.source_ref.source_id == "ifind"
    assert o.source_ref.captured_at == _dt(1, hour=9)
    assert o.captured_at == _dt(1) and o.captured_at.tzinfo is not None
    assert o.confidence == 0.9
    print("[OK] Case 5：source_ref + tz-aware datetime roundtrip 逐字段相等")


def test_append_only_full_history() -> None:
    mem, sql = _both(_seed())
    result = _assert_equal(
        mem, sql, _MAOTAI, knowledge_at=_dt(30), fact_types=(FactType.INDUSTRY,)
    )
    assert {o.content_hash for o in result} == {"h1", "h2"}, "同 logical_key 全历史，非 latest"
    print("[OK] Case 6：append-only 全历史（S3-2 非 SELECT latest），两端一致")


def test_record_idempotent() -> None:
    obs = _obs(logical_key="k", content_hash="h", captured_at=_dt(1))
    sql = SQLiteObservationReadPort(path=":memory:")
    sql.record(obs)
    sql.record(obs)  # 同 (logical_key, content_hash) 幂等
    sql.record(_obs(logical_key="k", content_hash="h", captured_at=_dt(1), object_value="dup"))
    result = sql.query(_MAOTAI, knowledge_at=_dt(30))
    assert len(result) == 1, "SQLite 须幂等于 (logical_key, content_hash)"
    print("[OK] Case 7：SQLite record 幂等于 (logical_key, content_hash)")


def test_effective_at_not_interpreted() -> None:
    mem, sql = _both(
        (_obs(logical_key="k", content_hash="h", captured_at=_dt(1), occurred_at=_dt(20)),)
    )
    baseline = _assert_equal(mem, sql, _MAOTAI, knowledge_at=_dt(30))
    with_eff = _assert_equal(
        mem, sql, _MAOTAI, knowledge_at=_dt(30), effective_at=_dt(1)
    )
    assert with_eff == baseline, "effective_at 不应改变结果（S2/S3 defer）"
    print("[OK] Case 8：effective_at 接受但不解释（两端一致 defer）")


def test_runtime_checkable_protocol() -> None:
    sql = SQLiteObservationReadPort(path=":memory:")
    assert isinstance(sql, ObservationReadPort)
    print("[OK] Case 9：SQLiteObservationReadPort 满足 ObservationReadPort Protocol")


def test_no_schema_expansion() -> None:
    """S3-1 守护：不新增 observation_history 表、不加 effective_at 索引；spine 列集恒定。"""
    sql = SQLiteObservationReadPort(path=":memory:")
    conn = sql._connect()  # noqa: SLF001 — 测试内检查 schema
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(knowledge_observation)")}
        expected_cols = {
            "observation_id", "logical_key", "content_hash", "fact_type",
            "subject_type", "subject_id", "predicate", "object_type", "object_value",
            "occurred_at", "published_at", "captured_at", "confidence", "source_ref",
            "attributes", "schema_version", "created_at",
        }
        assert cols == expected_cols, f"spine 列集变动（S3-1 禁扩 schema）：{cols ^ expected_cols}"
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert "observation_history" not in tables, "S3-1 禁止新增 observation_history 表"
        indexes = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
            if row[0] is not None
        }
        assert not any("effective" in name.lower() for name in indexes), (
            "S3-1 禁止新增 effective_at 索引"
        )
    finally:
        sql._close(conn)  # noqa: SLF001
    print("[OK] Case 10：零 schema 变更（列集恒定；无 observation_history 表 / effective_at 索引）")


def main() -> None:
    test_parity_matrix()
    test_order_stability_same_captured_at()
    test_subject_label_roundtrip()
    test_none_fields_roundtrip()
    test_source_ref_and_tz_roundtrip()
    test_append_only_full_history()
    test_record_idempotent()
    test_effective_at_not_interpreted()
    test_runtime_checkable_protocol()
    test_no_schema_expansion()
    print("\nInMemory == SQLite ObservationReadPort parity 测试全部通过 ✅")


if __name__ == "__main__":
    main()
