"""Experience Event Infrastructure 测试（见 ADR 0014 Stage 1）。

运行：uv run python -m tests.test_experience
覆盖：
  1. append 返回 event_id，事件可被 get 回读
  2. get 未命中返回 None
  3. 自动生成 event_id（未显式指定时）
  4. list 过滤：agent / type / entity_id / since / limit + occurred_at 倒序
  5. append-only 不可变：重复 event_id 拒绝覆盖；无 update/delete 接口
  6. refs 只引用不复制：只持有 run_id/evaluation_ref/entity_ids，不内嵌 RunStore/Evaluation/Knowledge 内容
"""

from __future__ import annotations

from datetime import datetime, timedelta

from shanhai_experience import (
    ExperienceEvent,
    ExperienceEventType,
    ExperienceRefs,
    ExperienceStore,
    InMemoryExperienceStore,
)


def _event(
    agent: str = "research",
    type: ExperienceEventType = ExperienceEventType.DECISION,
    episode_id: str = "ep-1",
    occurred_at: datetime | None = None,
    refs: ExperienceRefs | None = None,
    event_id: str | None = None,
) -> ExperienceEvent:
    kwargs: dict = dict(
        episode_id=episode_id,
        agent=agent,
        type=type,
        payload={"note": "x"},
        refs=refs or ExperienceRefs(),
    )
    if occurred_at is not None:
        kwargs["occurred_at"] = occurred_at
    if event_id is not None:
        kwargs["event_id"] = event_id
    return ExperienceEvent(**kwargs)


def test_append_and_get() -> None:
    store = InMemoryExperienceStore()
    eid = store.append(_event(event_id="e1"))

    assert eid == "e1"
    got = store.get("e1")
    assert got is not None
    assert got.agent == "research"
    assert got.type == ExperienceEventType.DECISION
    print("[OK] append 返回 id 且可 get 回读")


def test_get_miss() -> None:
    store = InMemoryExperienceStore()
    assert store.get("nope") is None
    print("[OK] get 未命中返回 None")


def test_auto_event_id() -> None:
    store = InMemoryExperienceStore()
    eid = store.append(_event())  # 不显式指定 event_id

    assert isinstance(eid, str) and len(eid) > 0
    assert store.get(eid) is not None
    print("[OK] 未指定时自动生成 event_id")


def test_list_filters_and_order() -> None:
    store = InMemoryExperienceStore()
    base = datetime(2026, 1, 1)
    store.append(_event(agent="research", type=ExperienceEventType.DECISION,
                        occurred_at=base, event_id="d1",
                        refs=ExperienceRefs(entity_ids=["600519"])))
    store.append(_event(agent="research", type=ExperienceEventType.OUTCOME,
                        occurred_at=base + timedelta(days=5), event_id="o1",
                        refs=ExperienceRefs(entity_ids=["600519"], parent_event_id="d1")))
    store.append(_event(agent="other", type=ExperienceEventType.DECISION,
                        occurred_at=base + timedelta(days=1), event_id="d2",
                        refs=ExperienceRefs(entity_ids=["000001"])))

    # 倒序：最新 occurred_at 在前
    all_events = store.list()
    assert [e.event_id for e in all_events] == ["o1", "d2", "d1"]

    # agent 过滤
    assert {e.event_id for e in store.list(agent="research")} == {"d1", "o1"}
    # type 过滤
    assert {e.event_id for e in store.list(type=ExperienceEventType.DECISION)} == {"d1", "d2"}
    # entity_id 过滤（命中 refs.entity_ids）
    assert {e.event_id for e in store.list(entity_id="600519")} == {"d1", "o1"}
    # since 过滤
    assert {e.event_id for e in store.list(since=base + timedelta(days=2))} == {"o1"}
    # limit
    assert len(store.list(limit=1)) == 1
    print("[OK] list 过滤 agent/type/entity_id/since/limit 且倒序正确")


def test_append_only_immutable() -> None:
    store = InMemoryExperienceStore()
    store.append(_event(event_id="e1"))

    # 重复 event_id 拒绝覆盖
    try:
        store.append(_event(event_id="e1", agent="tamper"))
        raise AssertionError("重复 event_id 应被拒绝")
    except ValueError:
        pass

    # 无 update/delete 接口
    assert not hasattr(ExperienceStore, "update")
    assert not hasattr(ExperienceStore, "delete")
    print("[OK] append-only：拒绝覆盖且无 update/delete")


def test_refs_reference_not_copy() -> None:
    # refs 只持有标识符，不内嵌 RunStore/Evaluation/Knowledge 对象
    refs = ExperienceRefs(
        run_id="run-123",
        evaluation_ref="run-123:runtime_evaluator",
        entity_ids=["600519", "industry:baijiu"],
        parent_event_id="d1",
    )
    ev = _event(refs=refs)

    assert ev.refs.run_id == "run-123"
    assert ev.refs.evaluation_ref == "run-123:runtime_evaluator"
    assert ev.refs.entity_ids == ["600519", "industry:baijiu"]
    # 字段类型即引用语义：全是 str / list[str]，没有内嵌的 RunResult/Step/Metric/Entity
    field_types = {name: f.annotation for name, f in ExperienceRefs.model_fields.items()}
    assert field_types["run_id"] == (str | None)
    assert field_types["evaluation_ref"] == (str | None)
    assert field_types["parent_event_id"] == (str | None)
    assert field_types["entity_ids"] == list[str]
    print("[OK] refs 只引用 id，不复制 RunStore/Evaluation/Knowledge 内容")


def main() -> None:
    test_append_and_get()
    test_get_miss()
    test_auto_event_id()
    test_list_filters_and_order()
    test_append_only_immutable()
    test_refs_reference_not_copy()
    print("\nExperience Event Infrastructure 测试全部通过 ✅")


if __name__ == "__main__":
    main()
