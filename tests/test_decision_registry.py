"""Decision Registry 测试（见 ADR 0000 Commit 4：Decision Registry）。

运行：python3 -m tests.test_decision_registry
覆盖：
  1. DecisionRecord 加法字段 roundtrip：type/title/alternatives/rejected_alternatives/related_context_events
  2. 向后兼容：缺新字段的旧 dict（Commit 2 形态）仍可 from_dict 解析，新字段取默认值（type 默认 architecture）
  3. registry.jsonl 是唯一结构事实源，不再派生 registry.yaml（断言该文件不存在；render_view 仅打印不落盘）
  4. 仓库内 registry.jsonl 全行可被 schema 回读，id 唯一，status 合法，type/title 齐备
  5. 可审计性桥：related_context_events 全部指向 events/stream.jsonl 实际存在的 evt_id
  6. 边界：decisions 工具不接 LLM/embedding/RAG/YAML 解析（仅 stdlib + 本层 schema）
"""

from __future__ import annotations

import json
from pathlib import Path

from tools.context.decisions import load_registry, render_view
from tools.context.schema import (
    SCHEMA_VERSION,
    DecisionRecord,
    DecisionStatus,
)

_REPO = Path(__file__).resolve().parent.parent
_DECISIONS = _REPO / ".shanhai-meta" / "decisions"
_REGISTRY = _DECISIONS / "registry.jsonl"
_STREAM = _REPO / ".shanhai-meta" / "events" / "stream.jsonl"


def test_additive_fields_roundtrip() -> None:
    rec = DecisionRecord(
        id="DEC-9001",
        title="测试决策",
        decision="只为测试",
        status=DecisionStatus.ACCEPTED,
        type="strategy",
        reason=["r1"],
        alternatives=["a1", "a2"],
        rejected_alternatives=["x1"],
        related=["ADR 0000"],
        related_context_events=["evt_abc", "evt_def"],
        source="evt_abc",
        decided_at="2026-06-24T00:00:00+00:00",
    )
    back = DecisionRecord.from_json(rec.to_json())
    assert back == rec
    assert back.type == "strategy"
    assert back.title == "测试决策"
    assert back.alternatives == ["a1", "a2"]
    assert back.rejected_alternatives == ["x1"]
    assert back.related_context_events == ["evt_abc", "evt_def"]
    print("[OK] DecisionRecord 加法字段 roundtrip 一致（含 type / rejected_alternatives）")


def test_backward_compatible_old_dict() -> None:
    # Commit 2 形态（无新字段）应仍可解析，新字段取默认值，无需 bump version
    old = {
        "schema_version": SCHEMA_VERSION,
        "id": "DEC-OLD",
        "decision": "旧记录",
        "status": "proposed",
        "reason": ["旧原因"],
        "related": [],
        "source": None,
        "decided_at": None,
    }
    rec = DecisionRecord.from_dict(old)
    assert rec.id == "DEC-OLD"
    assert rec.type == "architecture"  # 缺字段时默认 architecture
    assert rec.title is None
    assert rec.alternatives == []
    assert rec.rejected_alternatives == []
    assert rec.related_context_events == []
    print("[OK] 向后兼容：旧 dict 无新字段仍可解析，type 默认 architecture")


def test_no_second_source_of_truth() -> None:
    # Commit 4 Review 修正：删除 registry.yaml，registry.jsonl 是唯一结构事实源（不维护重复事实）
    assert not (_DECISIONS / "registry.yaml").exists(), "registry.yaml 不应存在（避免第二份事实源）"
    # render_view 只渲染瞬态视图，不写任何文件
    records = [
        DecisionRecord(id="DEC-1", title="t1", decision="d1", status=DecisionStatus.ACCEPTED),
        DecisionRecord(id="DEC-2", title="t2", decision="d2", status=DecisionStatus.PROPOSED, type="strategy"),
    ]
    text = render_view(records)
    i1 = text.index("[DEC-1]")
    i2 = text.index("[DEC-2]")
    assert 0 <= i1 < i2  # 顺序保留
    assert "(strategy/proposed)" in text  # type/status 一并呈现
    assert "registry.jsonl" in text  # 头部声明事实源
    print("[OK] 无第二事实源：registry.yaml 不存在，render_view 仅打印瞬态视图")


def test_repo_registry_loads_unique_and_valid() -> None:
    records = load_registry(_REGISTRY)
    assert records, "registry.jsonl 不应为空"
    ids = [r.id for r in records]
    assert len(set(ids)) == len(ids), f"决策 id 重复：{ids}"
    for r in records:
        assert r.status in DecisionStatus  # 合法枚举（from_dict 已校验）
        assert r.title, f"{r.id} 缺 title"
        assert r.type, f"{r.id} 缺 type"
    print(f"[OK] 仓库 registry.jsonl 全行可回读，id 唯一（{len(records)} 条）：{ids}")


def test_provenance_links_point_to_real_events() -> None:
    event_ids: set[str] = set()
    with _STREAM.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                event_ids.add(json.loads(line)["id"])
    records = load_registry(_REGISTRY)
    linked = {e for r in records for e in r.related_context_events}
    assert linked, "首批决策应带 related_context_events 回链"
    missing = linked - event_ids
    assert not missing, f"related_context_events 指向不存在的 evt_id：{missing}"
    print(f"[OK] 可审计性桥：{len(linked)} 个回链全部命中 stream.jsonl 实际 evt_id")


def test_no_llm_or_yaml_parse_deps() -> None:
    import ast

    import tools.context.decisions as mod

    with open(mod.__file__, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    allowed_roots = {
        "argparse", "json", "sys", "pathlib", "__future__", "tools",
    }
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    forbidden = {"openai", "anthropic", "numpy", "faiss", "chromadb",
                 "langchain", "sentence_transformers", "pydantic", "yaml"}
    assert not (imported & forbidden), f"decisions 禁止重依赖/LLM/YAML解析：{imported & forbidden}"
    assert imported <= allowed_roots, f"出现未预期依赖：{imported - allowed_roots}"
    print("[OK] 边界：不接 LLM/embedding/RAG，且不 import yaml（仅 stdlib + 本层 schema）")


def main() -> None:
    test_additive_fields_roundtrip()
    test_backward_compatible_old_dict()
    test_no_second_source_of_truth()
    test_repo_registry_loads_unique_and_valid()
    test_provenance_links_point_to_real_events()
    test_no_llm_or_yaml_parse_deps()
    print("\nDecision Registry 测试全部通过 ✅")


if __name__ == "__main__":
    main()
