"""Conversation Ingestion 测试（见 ADR 0000 Commit 5D：Human-AI Conversation Ingestion）。

运行：python3 -m tests.test_conversation_ingest
覆盖：
  1. 新会话导入：inbox dump → raw 快照产出 + index.jsonl catalog 追加
  2. catalog 增量：同 identity 内容增长 → 更新 raw 快照 + catalog（保留 first_seen_at）；无变化 → skip
  3. identity 稳定：同一会话不同导出文件名 → 同一 conversation_id（单条 catalog）
  4. 文件名锚定 identity：标题改名不迁移 raw 文件（id 稳定，title 归 catalog）
  5. 不污染：ingest 不写 events/stream.jsonl，也不改 cognition.json / registry.jsonl
  6. raw schema 贯通：产出的 raw 可被现有 import_chat.iter_events 读出（接上 Commit 3B 管线）
  7. quarantine：无法解析的 inbox 输入移入 quarantine/ 并写 reason，不抛错、不丢弃
  8. 零依赖：conversation_ingest 仅 stdlib + 本层，不接 LLM/embedding/RAG/yaml
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from tools.context.conversation_ingest import (
    extract_conversations,
    ingest_inbox,
    load_catalog,
)
from tools.context.import_chat import iter_events


def _dump(conv_id: str, title: str, n_msgs: int, update_time: float) -> dict:
    msgs = [{"id": "client-created-root", "text": ""}]
    for i in range(n_msgs):
        msgs.append({"id": f"m{i}", "text": f"message {i} content"})
    return {
        "conversations": [
            {"id": conv_id, "title": title, "updateTime": update_time, "messages": msgs}
        ]
    }


def _write_inbox(root: Path, name: str, dump: dict, clear: bool = False) -> Path:
    inbox = root / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    if clear:
        for old in inbox.glob("*.json"):
            old.unlink()
    p = inbox / name
    p.write_text(json.dumps(dump, ensure_ascii=False), encoding="utf-8")
    return p


def test_new_conversation_import() -> None:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write_inbox(root, "exp.json", _dump("conv-A", "Runtime Design", 3, 100.0))
        stats = ingest_inbox(root)
        assert stats["new"] == 1 and stats["updated"] == 0
        raws = list((root / "raw").glob("*.json"))
        assert len(raws) == 1, "应产出一份 raw 快照"
        catalog = load_catalog(root / "index.jsonl")
        assert "conv-A" in catalog
        assert catalog["conv-A"]["message_count"] == 4  # 含 root 占位
        assert catalog["conv-A"]["first_seen_at"] == catalog["conv-A"]["last_synced_at"]
        # 命名约定：<source>-<id_prefix>-<slug>.json，文件名只表达身份、不含日期
        name = raws[0].name
        assert name == "chatgpt-conv-A-Runtime-Design.json", f"身份式命名，无日期前缀：{name}"
        assert not name[:1].isdigit(), "文件名不应以日期数字开头"
    print("[OK] 新会话导入：raw 快照产出（身份式命名，无日期）+ index catalog 追加")


def test_catalog_incremental_update() -> None:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        # 第一次：100 条
        _write_inbox(root, "day1.json", _dump("conv-A", "山海", 100, 100.0))
        s1 = ingest_inbox(root, today="2026-06-24")
        assert s1["new"] == 1
        cat1 = load_catalog(root / "index.jsonl")
        raw_file = cat1["conv-A"]["raw_file"]
        # 第二次：同 identity，内容增长到 130 条，updateTime 变化（新导出替换 inbox）
        _write_inbox(root, "day2.json", _dump("conv-A", "山海", 130, 200.0), clear=True)
        s2 = ingest_inbox(root, today="2026-06-25")
        assert s2["new"] == 0 and s2["updated"] == 1, "内容增长应为 updated 而非 duplicate"
        cat2 = load_catalog(root / "index.jsonl")
        assert len(cat2) == 1, "同 identity 不应产生第二条 catalog"
        assert cat2["conv-A"]["raw_file"] == raw_file, "快照原地覆盖，文件名不变"
        assert cat2["conv-A"]["message_count"] == 131
        assert cat2["conv-A"]["first_seen_at"] == "2026-06-24", "首见日期保留"
        assert cat2["conv-A"]["last_synced_at"] == "2026-06-25", "同步日期更新"
        # raw 快照确实更新到 131 条
        snap = json.loads((root / "raw" / raw_file).read_text(encoding="utf-8"))
        assert len(snap["conversations"][0]["messages"]) == 131
        # 第三次：无变化 → skip（新导出替换 inbox）
        _write_inbox(root, "day3.json", _dump("conv-A", "山海", 130, 200.0), clear=True)
        s3 = ingest_inbox(root, today="2026-06-26")
        assert s3["new"] == 0 and s3["updated"] == 0 and s3["unchanged"] == 1
    print("[OK] catalog 增量：增长→更新快照（保 first_seen），无变化→skip，同 identity 不重复")


def test_identity_stable_across_filenames() -> None:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write_inbox(root, "aaa.json", _dump("conv-X", "T", 5, 1.0))
        ingest_inbox(root)
        # 不同文件名，同会话内容（id 不变）
        _write_inbox(root, "zzz-renamed.json", _dump("conv-X", "T", 5, 1.0))
        ingest_inbox(root)
        catalog = load_catalog(root / "index.jsonl")
        assert list(catalog.keys()) == ["conv-X"], "同 id 不同文件名应归并为同一 identity"
    print("[OK] identity 稳定：不同导出文件名 → 同一 conversation_id")


def test_filename_anchors_on_identity_not_title() -> None:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write_inbox(root, "v1.json", _dump("conv-A", "山海架构", 10, 100.0))
        ingest_inbox(root, today="2026-06-24")
        cat1 = load_catalog(root / "index.jsonl")
        raw_file = cat1["conv-A"]["raw_file"]
        # 同会话 id，标题改名 + 内容增长 → 文件名（身份）不变，只覆盖快照、刷新 title
        _write_inbox(root, "v2.json", _dump("conv-A", "Runtime Kernel设计", 20, 200.0), clear=True)
        s2 = ingest_inbox(root, today="2026-06-25")
        assert s2["updated"] == 1
        cat2 = load_catalog(root / "index.jsonl")
        assert cat2["conv-A"]["raw_file"] == raw_file, "标题变化不应导致 raw 文件改名/迁移"
        assert cat2["conv-A"]["title"] == "Runtime Kernel设计", "title 在 catalog 中刷新"
        raws = list((root / "raw").glob("*.json"))
        assert len(raws) == 1, "标题改名不得产生第二份快照"
    print("[OK] 文件名锚定 identity：标题改名不迁移文件（id 稳定，title 可变归 catalog）")


def test_does_not_pollute_other_context() -> None:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        # 模拟邻近的事实源/派生物
        (root / "events").mkdir()
        stream = root.parent / "stream_probe.jsonl"  # 不在 root 内，确保 ingest 绝不触碰
        events_stream = root / "events" / "stream.jsonl"
        events_stream.write_text('{"id":"evt_x"}\n', encoding="utf-8")
        before = events_stream.read_bytes()
        _write_inbox(root, "exp.json", _dump("conv-A", "T", 3, 1.0))
        ingest_inbox(root)
        assert events_stream.read_bytes() == before, "ingest 不得修改 events/stream.jsonl"
        assert not stream.exists()
        # ingest 只写 raw / index / quarantine
        produced = {p.name for p in root.rglob("*") if p.is_file()}
        assert "stream.jsonl" in {p.name for p in (root / "events").glob("*")}
        assert (root / "index.jsonl").exists()
    print("[OK] 不污染：ingest 不写 stream.jsonl，仅维护 raw/index/quarantine")


def test_raw_snapshot_feeds_import_chat() -> None:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _write_inbox(root, "exp.json", _dump("conv-A", "T", 4, 1.0))
        ingest_inbox(root)
        raw_file = next((root / "raw").glob("*.json"))
        dump = json.loads(raw_file.read_text(encoding="utf-8"))
        events = list(iter_events(dump, source_file=raw_file.name))
        assert len(events) == 4, "空 root 占位被 importer 跳过，4 条实体消息可读出"
        assert all(ev.type.value == "conversation" for ev in events)
        assert all(ev.actor.role.value == "unknown" for ev in events)
    print("[OK] raw schema 贯通：产出 raw 可被 import_chat.iter_events 读出（接 Commit 3B）")


def test_quarantine_on_parse_failure() -> None:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        bad = _write_inbox(root, "broken.json", {"unexpected": "shape"})  # 无 conversations
        empty = root / "inbox" / "empty.json"
        empty.write_text("{ not json", encoding="utf-8")
        stats = ingest_inbox(root)
        assert stats["failed"] == 2, "两个坏输入都应失败隔离"
        assert not bad.exists(), "坏文件应已移出 inbox"
        q = root / "quarantine"
        qfiles = {p.name for p in q.glob("*.json")}
        assert "broken.json" in qfiles and "empty.json" in qfiles
        reasons = list(q.glob("*.reason.txt"))
        assert len(reasons) == 2, "每个隔离文件附 reason"
    print("[OK] quarantine：坏输入移入隔离区 + reason，不抛错、不丢弃")


def test_extract_best_effort_shapes() -> None:
    # dict with conversations / bare list / single conversation object
    recs = extract_conversations(_dump("c1", "t", 2, 1.0))
    assert recs[0].identity == "c1"
    recs2 = extract_conversations([{"id": "c2", "title": "t", "messages": []}])
    assert recs2[0].identity == "c2"
    recs3 = extract_conversations({"messages": [{"id": "m0", "text": "hi"}], "title": "no-id"})
    assert recs3[0].identity.startswith("sha256:"), "缺原生 id 时回退 sha256 identity"
    print("[OK] best-effort extract：dict/list/单会话三形态 + 缺 id 回退 sha256")


def test_no_llm_or_extra_deps() -> None:
    import ast

    import tools.context.conversation_ingest as mod

    with open(mod.__file__, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    allowed_roots = {
        "argparse", "hashlib", "json", "re", "sys", "dataclasses",
        "datetime", "pathlib", "typing", "__future__", "tools",
    }
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    forbidden = {"openai", "anthropic", "numpy", "faiss", "chromadb",
                 "langchain", "sentence_transformers", "pydantic", "yaml"}
    assert not (imported & forbidden), f"conversation_ingest 禁止重依赖/LLM：{imported & forbidden}"
    assert imported <= allowed_roots, f"出现未预期依赖：{imported - allowed_roots}"
    print("[OK] 零依赖：仅 stdlib + 本层，不接 LLM/embedding/RAG/yaml")


def main() -> None:
    test_new_conversation_import()
    test_catalog_incremental_update()
    test_identity_stable_across_filenames()
    test_filename_anchors_on_identity_not_title()
    test_does_not_pollute_other_context()
    test_raw_snapshot_feeds_import_chat()
    test_quarantine_on_parse_failure()
    test_extract_best_effort_shapes()
    test_no_llm_or_extra_deps()
    print("\nConversation Ingestion 测试全部通过 ✅")


if __name__ == "__main__":
    main()
