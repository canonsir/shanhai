"""RuntimeEvent 契约测试（v0.7 §0.C G5 / Q5.4，PR-1）。

运行：PYTHONPATH=. .venv/bin/python -m tests.runtime_kernel.test_event_contract
覆盖（event schema）：
  Case 1 identity envelope schema：字段集合恰为 {event_id, run_id, event_type,
         timestamp, payload}（不新造、不多塞）
  Case 2 run_id 复用运行身份；payload 承载既有产物（任意对象，含 RunResult 形态）
  Case 3 event_id / timestamp 自动生成且各事件唯一
"""

from __future__ import annotations

from datetime import datetime

from shanhai_runtime_kernel import RuntimeEvent, RuntimeEventType

_EXPECTED_FIELDS = {"event_id", "run_id", "event_type", "timestamp", "payload"}


def test_case1_envelope_schema() -> None:
    fields = set(RuntimeEvent.model_fields.keys())
    assert fields == _EXPECTED_FIELDS, fields
    print("[OK] Case 1：RuntimeEvent 字段集合恰为 identity envelope（不新造 schema）")


def test_case2_run_id_and_payload() -> None:
    payload = {"agent": "demo", "status": "completed", "steps": []}
    ev = RuntimeEvent(
        run_id="run_001",
        event_type=RuntimeEventType.RUN_COMPLETED,
        payload=payload,
    )
    assert ev.run_id == "run_001"
    assert ev.event_type == RuntimeEventType.RUN_COMPLETED
    assert ev.payload == payload  # payload 透传既有产物，不约束其 schema
    assert isinstance(ev.timestamp, datetime)
    print("[OK] Case 2：run_id 复用运行身份；payload 透传既有产物")


def test_case3_event_id_unique() -> None:
    e1 = RuntimeEvent(run_id="r", event_type=RuntimeEventType.RUN_CREATED)
    e2 = RuntimeEvent(run_id="r", event_type=RuntimeEventType.RUN_CREATED)
    assert e1.event_id and e2.event_id
    assert e1.event_id != e2.event_id, "event_id 应各事件唯一"
    print("[OK] Case 3：event_id / timestamp 自动生成，event_id 唯一")


def main() -> None:
    test_case1_envelope_schema()
    test_case2_run_id_and_payload()
    test_case3_event_id_unique()
    print("\nRuntimeEvent 契约测试全部通过 ✅")


if __name__ == "__main__":
    main()
