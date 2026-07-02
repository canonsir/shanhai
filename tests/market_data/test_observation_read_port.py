"""ObservationReadPort InMemory 适配器行为测试（M3.4 S2）。

运行：
PYTHONPATH=services/market-data:. \
    .venv/bin/python -m tests.market_data.test_observation_read_port

守护 S2 read contract 的确定性领域语义 + Review Gate 批准的负向约束：
  Case 1  subject 过滤（entity_type + entity_id；label 不参与身份）
  Case 2  fact_types 过滤（为空 = 全部家族）
  Case 3  captured_at <= knowledge_at 边界（含边界；不返回未来观测）
  Case 4  append-only：同 logical_key 多 content_hash 全部返回，不做 latest 投影
  Case 5  record 幂等于 (logical_key, content_hash)
  Case 6  effective_at 接受但不解释（S2-3：给不同 effective_at 结果不变）
  Case 7  确定性排序：插入顺序无关，输出稳定
  Case 8  runtime_checkable：适配器 isinstance(ObservationReadPort)
  Case 9  S2-1 不扩 schema：Observation 字段集恒定（新增字段即视为越界）
"""

from __future__ import annotations

from datetime import datetime, timezone

from shanhai_market_data.models import FactType, SourceRef, SubjectRef
from shanhai_market_data.ports import (
    InMemoryObservationReadPort,
    Observation,
    ObservationReadPort,
)


def _dt(day: int) -> datetime:
    return datetime(2026, 3, day, tzinfo=timezone.utc)


_MAOTAI = SubjectRef(entity_type="company", entity_id="c-600519", label="贵州茅台")
_OTHER = SubjectRef(entity_type="company", entity_id="c-000001", label="平安银行")


def _obs(
    *,
    logical_key: str,
    content_hash: str,
    subject: SubjectRef = _MAOTAI,
    fact_type: FactType = FactType.INDUSTRY,
    captured_day: int,
    object_value: str | None = None,
    occurred_at: datetime | None = None,
) -> Observation:
    return Observation(
        logical_key=logical_key,
        content_hash=content_hash,
        fact_type=fact_type,
        subject=subject,
        object_value=object_value,
        occurred_at=occurred_at,
        captured_at=_dt(captured_day),
        source_ref=SourceRef(source_id="test", source_name="test", captured_at=_dt(1)),
    )


def _seed() -> InMemoryObservationReadPort:
    port = InMemoryObservationReadPort()
    port.record_many(
        (
            _obs(logical_key="k-industry", content_hash="h1", captured_day=1, object_value="白酒"),
            _obs(
                logical_key="k-industry",
                content_hash="h2",
                captured_day=3,
                object_value="白酒（更名）",
            ),
            _obs(
                logical_key="k-fin",
                content_hash="hf",
                fact_type=FactType.FINANCIAL,
                captured_day=2,
            ),
            _obs(
                logical_key="k-other",
                content_hash="ho",
                subject=_OTHER,
                captured_day=2,
            ),
        )
    )
    return port


def test_subject_filter() -> None:
    port = _seed()
    result = port.query(_MAOTAI, knowledge_at=_dt(30))
    assert all(o.subject.entity_id == "c-600519" for o in result)
    assert {o.logical_key for o in result} == {"k-industry", "k-fin"}
    # label 不参与身份：换 label 仍命中同一 subject。
    relabeled = SubjectRef(entity_type="company", entity_id="c-600519", label="改名了")
    assert port.query(relabeled, knowledge_at=_dt(30)) == result
    print("[OK] Case 1：subject 过滤（entity_type+entity_id；label 不参与身份）")


def test_fact_types_filter() -> None:
    port = _seed()
    only_fin = port.query(_MAOTAI, knowledge_at=_dt(30), fact_types=(FactType.FINANCIAL,))
    assert {o.fact_type for o in only_fin} == {FactType.FINANCIAL}
    # 空 fact_types = 全部家族。
    all_fam = port.query(_MAOTAI, knowledge_at=_dt(30))
    assert {o.fact_type for o in all_fam} == {FactType.INDUSTRY, FactType.FINANCIAL}
    print("[OK] Case 2：fact_types 过滤（空=全部家族）")


def test_knowledge_at_boundary() -> None:
    port = _seed()
    # 边界含等号：captured_at == knowledge_at 命中。
    at_day1 = port.query(_MAOTAI, knowledge_at=_dt(1))
    assert {o.content_hash for o in at_day1} == {"h1"}
    # 未来观测（h2@day3）在 day2 视角不可见。
    at_day2 = port.query(_MAOTAI, knowledge_at=_dt(2))
    assert {o.content_hash for o in at_day2} == {"h1", "hf"}
    print("[OK] Case 3：captured_at <= knowledge_at 边界（含等号；不返回未来观测）")


def test_append_only_no_latest_projection() -> None:
    port = _seed()
    industry = port.query(_MAOTAI, knowledge_at=_dt(30), fact_types=(FactType.INDUSTRY,))
    # 同 logical_key 两条不同 content_hash 全部返回（append-only），不折叠为 latest。
    assert {o.content_hash for o in industry} == {"h1", "h2"}
    assert {o.object_value for o in industry} == {"白酒", "白酒（更名）"}
    print("[OK] Case 4：append-only 全历史返回，不做 latest-per-key 投影")


def test_record_idempotent() -> None:
    port = InMemoryObservationReadPort()
    obs = _obs(logical_key="k", content_hash="h", captured_day=1)
    port.record(obs)
    port.record(obs)  # 同 (logical_key, content_hash) 二次记录幂等
    port.record(_obs(logical_key="k", content_hash="h", captured_day=1, object_value="dup"))
    result = port.query(_MAOTAI, knowledge_at=_dt(30))
    assert len(result) == 1
    print("[OK] Case 5：record 幂等于 (logical_key, content_hash)")


def test_effective_at_not_interpreted() -> None:
    """S2-3：effective_at 保留不解释——给任意值结果都不变。"""
    port = InMemoryObservationReadPort()
    port.record(
        _obs(
            logical_key="k",
            content_hash="h",
            captured_day=1,
            occurred_at=_dt(20),  # 世界视角时间
        )
    )
    baseline = port.query(_MAOTAI, knowledge_at=_dt(30))
    # effective_at 早于 occurred_at：若被解释应过滤掉，但 S2 不解释 → 仍返回。
    with_effective = port.query(_MAOTAI, knowledge_at=_dt(30), effective_at=_dt(1))
    assert with_effective == baseline
    assert len(with_effective) == 1
    print("[OK] Case 6：effective_at 接受但不解释（S2-3）")


def test_deterministic_order_insertion_independent() -> None:
    forward = InMemoryObservationReadPort()
    forward.record_many(
        (
            _obs(logical_key="a", content_hash="1", captured_day=1),
            _obs(logical_key="b", content_hash="2", captured_day=2),
            _obs(logical_key="c", content_hash="3", captured_day=3),
        )
    )
    reverse = InMemoryObservationReadPort()
    reverse.record_many(
        (
            _obs(logical_key="c", content_hash="3", captured_day=3),
            _obs(logical_key="b", content_hash="2", captured_day=2),
            _obs(logical_key="a", content_hash="1", captured_day=1),
        )
    )
    assert forward.query(_MAOTAI, knowledge_at=_dt(30)) == reverse.query(
        _MAOTAI, knowledge_at=_dt(30)
    )
    print("[OK] Case 7：确定性排序，输出与插入顺序无关")


def test_runtime_checkable_protocol() -> None:
    port = InMemoryObservationReadPort()
    assert isinstance(port, ObservationReadPort)
    print("[OK] Case 8：InMemoryObservationReadPort 满足 ObservationReadPort Protocol")


def test_observation_schema_not_expanded() -> None:
    """S2-1 守护：S2 不新增 Observation schema，字段集恒定。"""
    expected = {
        "logical_key",
        "content_hash",
        "fact_type",
        "subject",
        "predicate",
        "object_value",
        "occurred_at",
        "published_at",
        "captured_at",
        "confidence",
        "source_ref",
    }
    assert set(Observation.model_fields) == expected, (
        "S2 不得扩展 Observation schema（S2-1）；字段集变动需过 Review Gate"
    )
    print("[OK] Case 9：Observation schema 未扩（S2-1）")


def main() -> None:
    test_subject_filter()
    test_fact_types_filter()
    test_knowledge_at_boundary()
    test_append_only_no_latest_projection()
    test_record_idempotent()
    test_effective_at_not_interpreted()
    test_deterministic_order_insertion_independent()
    test_runtime_checkable_protocol()
    test_observation_schema_not_expanded()
    print("\nObservationReadPort InMemory 适配器行为测试全部通过 ✅")


if __name__ == "__main__":
    main()
