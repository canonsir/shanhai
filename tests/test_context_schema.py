"""Context Schema 测试（见 ADR 0000 Commit 2：Context Schema）。

运行：python -m tests.test_context_schema   或   uv run python -m tests.test_context_schema
覆盖：
  1. 三个对象 object → dict → json → dict → object 可逆（round-trip 相等）
  2. schema_version 字段存在且为受支持版本；不支持版本被拒
  3. required fields 缺失被拒（SchemaError）
  4. enum type 非法值被拒（SchemaError）
  5. 默认值守约：actor 默认 unknown（ADR 0000 §D5）、零依赖（仅 stdlib）
"""

from __future__ import annotations

import sys

from tools.context.schema import (
    SCHEMA_VERSION,
    ActorRole,
    ContextEvent,
    ContextSnapshot,
    DecisionRecord,
    DecisionStatus,
    EventActor,
    EventContent,
    EventSource,
    EventType,
    SchemaError,
    SourceKind,
)


def _sample_event() -> ContextEvent:
    return ContextEvent(
        id="evt_0001",
        type=EventType.CONVERSATION,
        timestamp="2026-06-24T00:00:00+00:00",
        source=EventSource(kind=SourceKind.CHATGPT_EXPORT, file="raw.json", ref="raw#42"),
        actor=EventActor(role=ActorRole.UNKNOWN, name=None),
        content=EventContent(text="山海架构讨论", attachments=[], has_lost_media=True),
        metadata={"seq": 42},
    )


def _sample_decision() -> DecisionRecord:
    return DecisionRecord(
        id="ADR-0000-context-boundary",
        decision="Runtime data and Meta Context must be separated",
        status=DecisionStatus.ACCEPTED,
        reason=[".shanhai already owns runtime state"],
        related=["ADR0009", "ADR0000"],
        source="evt_0001",
        decided_at="2026-06-24T00:00:00+00:00",
    )


def _sample_snapshot() -> ContextSnapshot:
    return ContextSnapshot(
        project_phase="context-layer-building",
        architecture={"runtime_memory": "implemented", "meta_context": "foundation"},
        frozen_decisions=["ADR0000", "ADR0009"],
        generated_at="2026-06-24T00:00:00+00:00",
    )


def test_event_roundtrip() -> None:
    ev = _sample_event()
    restored = ContextEvent.from_dict(ev.to_dict())
    assert restored == ev
    # json 层亦可逆
    assert ContextEvent.from_json(ev.to_json()).to_dict() == ev.to_dict()
    # 枚举落地为字符串值
    d = ev.to_dict()
    assert d["type"] == "conversation"
    assert d["source"]["kind"] == "chatgpt_export"
    assert d["actor"]["role"] == "unknown"
    assert d["content"]["has_lost_media"] is True
    print("[OK] ContextEvent object→dict→json 可逆")


def test_decision_roundtrip() -> None:
    dr = _sample_decision()
    assert DecisionRecord.from_dict(dr.to_dict()) == dr
    assert DecisionRecord.from_json(dr.to_json()).to_dict() == dr.to_dict()
    assert dr.to_dict()["status"] == "accepted"
    print("[OK] DecisionRecord object→dict→json 可逆")


def test_snapshot_roundtrip() -> None:
    sn = _sample_snapshot()
    assert ContextSnapshot.from_dict(sn.to_dict()) == sn
    assert ContextSnapshot.from_json(sn.to_json()).to_dict() == sn.to_dict()
    print("[OK] ContextSnapshot object→dict→json 可逆")


def test_schema_version_present_and_checked() -> None:
    for obj in (_sample_event(), _sample_decision(), _sample_snapshot()):
        d = obj.to_dict()
        assert d["schema_version"] == SCHEMA_VERSION

    # 不支持的版本被拒
    bad = _sample_event().to_dict()
    bad["schema_version"] = "9.9"
    _expect_schema_error(lambda: ContextEvent.from_dict(bad), "不支持版本应被拒")

    # 缺 schema_version 被拒
    missing = _sample_decision().to_dict()
    del missing["schema_version"]
    _expect_schema_error(lambda: DecisionRecord.from_dict(missing), "缺 schema_version 应被拒")
    print("[OK] schema_version 存在且受校验（含不支持/缺失拒绝）")


def test_required_fields() -> None:
    # ContextEvent 缺 id
    d = _sample_event().to_dict()
    del d["id"]
    _expect_schema_error(lambda: ContextEvent.from_dict(d), "缺 id 应被拒")

    # DecisionRecord 缺 decision
    d2 = _sample_decision().to_dict()
    del d2["decision"]
    _expect_schema_error(lambda: DecisionRecord.from_dict(d2), "缺 decision 应被拒")

    # ContextSnapshot 缺 project_phase
    d3 = _sample_snapshot().to_dict()
    del d3["project_phase"]
    _expect_schema_error(lambda: ContextSnapshot.from_dict(d3), "缺 project_phase 应被拒")
    print("[OK] required fields 缺失被拒")


def test_enum_validation() -> None:
    d = _sample_event().to_dict()
    d["type"] = "not_a_type"
    _expect_schema_error(lambda: ContextEvent.from_dict(d), "非法 EventType 应被拒")

    d2 = _sample_event().to_dict()
    d2["actor"]["role"] = "owner"  # 不是合法 ActorRole（应为 human-owner）
    _expect_schema_error(lambda: ContextEvent.from_dict(d2), "非法 ActorRole 应被拒")

    d3 = _sample_decision().to_dict()
    d3["status"] = "maybe"
    _expect_schema_error(lambda: DecisionRecord.from_dict(d3), "非法 DecisionStatus 应被拒")
    print("[OK] enum type 非法值被拒")


def test_defaults_and_zero_dependency() -> None:
    # actor 默认 unknown（ADR 0000 §D5：宁可 unknown 不错误记忆）
    ev = ContextEvent(id="e", type=EventType.DECISION)
    assert ev.actor.role == ActorRole.UNKNOWN
    assert ev.source.kind == SourceKind.UNKNOWN
    assert ev.content.has_lost_media is False
    assert ev.schema_version == SCHEMA_VERSION
    assert ev.timestamp  # 自动填充

    # 零依赖：schema 模块不得 import 第三方（pydantic 等），仅标准库
    import ast

    import tools.context.schema as schema_mod

    src = schema_mod.__file__
    assert src is not None
    with open(src, encoding="utf-8") as f:
        tree = ast.parse(f.read())

    stdlib_roots = {"json", "dataclasses", "datetime", "enum", "typing", "__future__", "hashlib"}
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
    third_party = imported_roots - stdlib_roots
    assert not third_party, f"tools/context 必须零依赖（ADR 0000 §D6），发现第三方依赖：{third_party}"
    print("[OK] 默认值守约 + 零依赖（仅 stdlib，无第三方 import）")


def _expect_schema_error(fn, msg: str) -> None:
    try:
        fn()
        raise AssertionError(msg)
    except SchemaError:
        pass


def main() -> None:
    test_event_roundtrip()
    test_decision_roundtrip()
    test_snapshot_roundtrip()
    test_schema_version_present_and_checked()
    test_required_fields()
    test_enum_validation()
    test_defaults_and_zero_dependency()
    print("\nContext Schema 测试全部通过 ✅")


if __name__ == "__main__":
    main()
    sys.exit(0)
