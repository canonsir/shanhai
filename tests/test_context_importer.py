"""Context Importer 测试（见 ADR 0000 Commit 3B：Raw → ContextEvent）。

运行：python -m tests.test_context_importer   或   uv run python -m tests.test_context_importer
覆盖：
  1. raw json → ContextEvent：type=conversation，actor=unknown（不推断 speaker，§D5）
  2. provenance 保留：source.kind/file/ref（raw#<id>），event id 由 ref 确定性派生
  3. 空 text 消息被跳过（如 client-created-root）
  4. 媒体丢失客观标记：含 media pointer → has_lost_media=true，原文不删
  5. 幂等：重复导入同一文件不产生重复事件（按 source.ref 去重，可安全重跑）
  6. JSONL 落地：每行一个可被 schema 回读的 ContextEvent；metadata 保留 seq/会话信息
  7. 边界：importer 不接 LLM/embedding/RAG（仅 stdlib + schema）
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from tools.context.import_chat import import_file, iter_events
from tools.context.schema import ActorRole, ContextEvent, EventType, SourceKind

_RAW = {
    "conversations": [
        {
            "id": "conv-1",
            "title": "山海架构",
            "updateTime": 1782281479.59222,
            "messages": [
                {"id": "client-created-root", "text": ""},
                {"id": "m1", "text": "我们决定不要把 context 放进 .shanhai"},
                {"id": "m2", "text": '[media pointer="sediment://file_x"]\n我看是公开的呀'},
                {"id": "m3", "text": "   "},
            ],
        }
    ]
}


def _write_raw(dir_: Path) -> Path:
    p = dir_ / "20260624-chatgpt-山海架构.json"
    p.write_text(json.dumps(_RAW, ensure_ascii=False), encoding="utf-8")
    return p


def test_basic_mapping_and_actor_unknown() -> None:
    events = list(iter_events(_RAW, source_file="20260624-chatgpt-山海架构.json"))
    # 4 条 message，2 条空（root + 纯空格）被跳过 → 2 个事件
    assert len(events) == 2
    for ev in events:
        assert ev.type == EventType.CONVERSATION
        assert ev.actor.role == ActorRole.UNKNOWN  # 不推断 speaker（§D5）
        assert ev.actor.name is None
    print("[OK] raw→ContextEvent：type=conversation，actor=unknown，空消息跳过")


def test_provenance_and_deterministic_id() -> None:
    events = list(iter_events(_RAW, source_file="f.json"))
    ev = events[0]
    assert ev.source.kind == SourceKind.CHATGPT_EXPORT
    assert ev.source.file == "f.json"
    assert ev.source.ref == "raw#m1"
    # event id 由 ref 确定性派生：同一 raw 消息恒得同一 id
    again = list(iter_events(_RAW, source_file="f.json"))[0]
    assert ev.id == again.id
    assert ev.id.startswith("evt_")
    print("[OK] provenance 保留（kind/file/ref）+ event id 确定性派生")


def test_lost_media_marked_without_deleting_text() -> None:
    events = list(iter_events(_RAW, source_file="f.json"))
    media_ev = next(e for e in events if e.source.ref == "raw#m2")
    assert media_ev.content.has_lost_media is True
    assert "media pointer" in media_ev.content.text  # 原文不删
    assert "我看是公开的呀" in media_ev.content.text
    # 普通消息不误标
    plain_ev = next(e for e in events if e.source.ref == "raw#m1")
    assert plain_ev.content.has_lost_media is False
    print("[OK] 媒体丢失客观标记 has_lost_media，且不删原文")


def test_jsonl_roundtrip_and_metadata() -> None:
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        raw = _write_raw(d)
        stream = d / "events" / "stream.jsonl"
        stats = import_file(raw, stream)
        assert stats == {"new": 2, "skipped_duplicate": 0, "with_lost_media": 1}

        lines = stream.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        # 每行可被 schema 回读
        for line in lines:
            ev = ContextEvent.from_json(line)
            assert ev.metadata["conversation_id"] == "conv-1"
            assert ev.metadata["conversation_title"] == "山海架构"
            assert "seq" in ev.metadata
    print("[OK] JSONL 落地：每行可 schema 回读，metadata 保留会话信息")


def test_idempotent_reimport() -> None:
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        raw = _write_raw(d)
        stream = d / "events" / "stream.jsonl"

        s1 = import_file(raw, stream)
        assert s1["new"] == 2
        n_after_first = len(stream.read_text(encoding="utf-8").splitlines())

        # 重跑：应全部跳过，文件行数不变
        s2 = import_file(raw, stream)
        assert s2["new"] == 0
        assert s2["skipped_duplicate"] == 2
        n_after_second = len(stream.read_text(encoding="utf-8").splitlines())
        assert n_after_first == n_after_second == 2
    print("[OK] 幂等：重复导入不产生重复事件，可安全重跑")


def test_no_llm_or_heavy_deps() -> None:
    import ast

    import tools.context.import_chat as mod

    with open(mod.__file__, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    allowed_roots = {
        "argparse", "hashlib", "json", "sys", "pathlib", "typing",
        "__future__", "tools",  # tools.context.schema（本层）
    }
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    forbidden = {"openai", "anthropic", "numpy", "faiss", "chromadb",
                 "langchain", "sentence_transformers", "pydantic"}
    assert not (imported & forbidden), f"importer 禁止重依赖/LLM：{imported & forbidden}"
    assert imported <= allowed_roots, f"出现未预期依赖：{imported - allowed_roots}"
    print("[OK] 边界：不接 LLM/embedding/RAG（仅 stdlib + 本层 schema）")


def main() -> None:
    test_basic_mapping_and_actor_unknown()
    test_provenance_and_deterministic_id()
    test_lost_media_marked_without_deleting_text()
    test_jsonl_roundtrip_and_metadata()
    test_idempotent_reimport()
    test_no_llm_or_heavy_deps()
    print("\nContext Importer 测试全部通过 ✅")


if __name__ == "__main__":
    main()
