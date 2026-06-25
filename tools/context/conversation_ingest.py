"""Human-AI Conversation Ingestion（Commit 5D / ADR 0000）。

职责单一：把用户从浏览器导出的 ChatGPT 会话 dump（IndexedDB 等）**规范化 + 增量纳管**为
ShanHai 的协作历史。建立「人-AI 协作输入层」（reasoning trace），补齐 Context Foundation 缺口。

链路：
    conversations/inbox/*.json   ← 用户临时输入（gitignore）
        │  best-effort extract + normalize + identity + 增量
        ▼
    conversations/raw/*.json     ← 每个会话身份一份「最新全量快照」（沿用现有 raw schema）
    conversations/index.jsonl    ← conversation catalog（已纳管会话目录，非 import log）
    conversations/quarantine/    ← 解析失败的输入（保留不丢弃，便于调试）

严格边界（经 Review 修正确认）——只做：
    inbox dump → 解析 → 身份识别 → 增量同步 raw 快照 + catalog → 失败隔离
绝不做：
    ❌ 进入 events/stream.jsonl（conversation 是 reasoning trace，不是 ContextEvent 事实源）
    ❌ LLM 总结 / embedding / RAG / 自动抽取 Decision / 更新 cognition / 改 builder·renderer·registry
    ❌ Agent Runtime 读取 conversation

增量语义（catalog，非 import log）：
    同一 conversation_id 会被反复导出（消息持续增长）。
      identity 不变 + message_count/update_time 无变化 → skip
      identity 不变 + 内容增长                       → 覆盖 raw 快照 + 更新 catalog（保留 first_seen_at）
      identity 新出现                                → 写 raw 快照 + 新增 catalog 行

身份（identity）：优先原生 `conversation.id`；缺失则 `sha256(title + first_message_time)`（记为 sha256:...）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_ROOT = Path(".shanhai-meta/conversations")

_UNSAFE = re.compile(r'[\\/:\*\?"<>\|\s]+')


class ConversationParseError(Exception):
    """inbox 输入无法解析为会话（触发 quarantine，不中断、不丢弃）。"""


@dataclass
class ConversationRecord:
    """从 dump 中 best-effort 提取的单个会话（规范化中间态）。"""

    identity: str
    title: str | None
    update_time: float | None
    conversation: dict[str, Any]  # 原始会话对象，原样保真写入 raw（沿用现有 schema）
    messages: list[Any] = field(default_factory=list)

    @property
    def message_count(self) -> int:
        return len(self.messages)


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _sha256_identity(title: str | None, first_msg: Any) -> str:
    basis = f"{title or ''}|{first_msg if first_msg is not None else ''}"
    return "sha256:" + hashlib.sha256(basis.encode("utf-8")).hexdigest()


def _slug(title: str | None, identity: str) -> str:
    base = (title or identity or "untitled").strip()
    base = _UNSAFE.sub("-", base).strip("-")
    return base or "untitled"


def _id_prefix(identity: str, length: int = 8) -> str:
    """会话身份的短前缀，作 raw 文件名的稳定锚点（非可变 title）。

    原生 id 取首段（如 6a266982-... → 6a266982）；sha256 身份取 hash 前缀。
    """
    core = identity.split(":", 1)[1] if identity.startswith("sha256:") else identity
    core = _UNSAFE.sub("", core)
    return core[:length] or "unknown"


def _raw_filename(identity: str, slug: str, source: str = "chatgpt") -> str:
    """<source>-<conversation_id_prefix>-<slug>.json。

    文件名只表达稳定身份；时间（first_seen/last_synced）归 index.jsonl，不进路径。
    """
    return f"{source}-{_id_prefix(identity)}-{slug}.json"


def extract_conversations(dump: Any) -> list[ConversationRecord]:
    """best-effort 提取会话列表。不强依赖 ChatGPT 内部 schema；提取不到则抛 ParseError。"""
    convs: list[Any]
    if isinstance(dump, dict) and isinstance(dump.get("conversations"), list):
        convs = dump["conversations"]
    elif isinstance(dump, list):
        convs = dump
    elif isinstance(dump, dict) and ("messages" in dump or "mapping" in dump):
        convs = [dump]  # 单会话对象
    else:
        raise ConversationParseError("未发现 conversations 列表/会话对象")

    records: list[ConversationRecord] = []
    for conv in convs:
        if not isinstance(conv, dict):
            continue
        messages = conv.get("messages")
        if not isinstance(messages, list):
            messages = []
        title = conv.get("title")
        update_time = conv.get("updateTime") or conv.get("update_time")
        native_id = conv.get("id") or conv.get("conversation_id")
        if native_id:
            identity = str(native_id)
        else:
            first_msg = messages[0].get("id") if messages and isinstance(messages[0], dict) else None
            identity = _sha256_identity(title, first_msg)
        records.append(
            ConversationRecord(
                identity=identity,
                title=title,
                update_time=update_time,
                conversation=conv,
                messages=messages,
            )
        )
    if not records:
        raise ConversationParseError("conversations 为空或无可提取会话")
    return records


def load_catalog(index_path: Path) -> dict[str, dict[str, Any]]:
    """读取 index.jsonl → {conversation_id: entry}。缺文件返回空目录。"""
    catalog: dict[str, dict[str, Any]] = {}
    if not index_path.exists():
        return catalog
    with index_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            cid = entry.get("conversation_id")
            if cid:
                catalog[cid] = entry
    return catalog


def write_catalog(index_path: Path, catalog: dict[str, dict[str, Any]]) -> None:
    """整表重写 index.jsonl（catalog 小、便于幂等更新），按 first_seen_at + id 稳定排序。"""
    index_path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(
        catalog.values(),
        key=lambda e: (e.get("first_seen_at", ""), e.get("conversation_id", "")),
    )
    with index_path.open("w", encoding="utf-8") as f:
        for entry in rows:
            f.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


def _write_raw_snapshot(raw_dir: Path, raw_file: str, conv: dict[str, Any]) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    payload = {"conversations": [conv]}
    (raw_dir / raw_file).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _classify(rec: ConversationRecord, catalog: dict[str, dict[str, Any]]) -> str:
    """new / updated / unchanged。"""
    entry = catalog.get(rec.identity)
    if entry is None:
        return "new"
    if entry.get("message_count") != rec.message_count or entry.get("update_time") != rec.update_time:
        return "updated"
    return "unchanged"


def sync_record(
    rec: ConversationRecord,
    catalog: dict[str, dict[str, Any]],
    raw_dir: Path,
    today: str,
    dry_run: bool,
) -> tuple[str, str]:
    """对单个会话应用 catalog 增量逻辑。返回 (action, raw_file)。"""
    action = _classify(rec, catalog)
    if action == "unchanged":
        return action, catalog[rec.identity]["raw_file"]

    if action == "new":
        first_seen = today
        raw_file = _raw_filename(rec.identity, _slug(rec.title, rec.identity))
    else:  # updated：保留首见日期与既有文件名，原地覆盖快照
        first_seen = catalog[rec.identity].get("first_seen_at", today)
        raw_file = catalog[rec.identity]["raw_file"]

    if not dry_run:
        _write_raw_snapshot(raw_dir, raw_file, rec.conversation)
        catalog[rec.identity] = {
            "conversation_id": rec.identity,
            "title": rec.title,
            "raw_file": raw_file,
            "source": "chatgpt",
            "message_count": rec.message_count,
            "update_time": rec.update_time,
            "first_seen_at": first_seen,
            "last_synced_at": today,
        }
    return action, raw_file


def ingest_file(
    source: Path,
    root: Path = DEFAULT_ROOT,
    today: str | None = None,
    dry_run: bool = False,
    catalog: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """解析一份 inbox 文件并增量同步。解析失败 → quarantine（不抛出、不丢弃）。"""
    today = today or _today()
    raw_dir = root / "raw"
    index_path = root / "index.jsonl"
    owns_catalog = catalog is None
    if catalog is None:
        catalog = load_catalog(index_path)

    try:
        dump = json.loads(source.read_text(encoding="utf-8"))
        records = extract_conversations(dump)
    except (ConversationParseError, json.JSONDecodeError, OSError) as exc:
        quarantined = None if dry_run else _quarantine(source, root, str(exc))
        return {
            "ok": False,
            "reason": str(exc),
            "quarantined": str(quarantined) if quarantined else None,
            "new": 0,
            "updated": 0,
            "unchanged": 0,
            "imported_titles": [],
        }

    new = updated = unchanged = 0
    imported_titles: list[str] = []
    for rec in records:
        action, _ = sync_record(rec, catalog, raw_dir, today, dry_run)
        if action == "new":
            new += 1
            imported_titles.append(rec.title or rec.identity)
        elif action == "updated":
            updated += 1
            imported_titles.append(rec.title or rec.identity)
        else:
            unchanged += 1

    if owns_catalog and not dry_run and (new or updated):
        write_catalog(index_path, catalog)

    return {
        "ok": True,
        "new": new,
        "updated": updated,
        "unchanged": unchanged,
        "imported_titles": imported_titles,
    }


def _quarantine(source: Path, root: Path, reason: str) -> Path:
    """把无法解析的 inbox 文件移入 quarantine/，并写 .reason.txt。"""
    qdir = root / "quarantine"
    qdir.mkdir(parents=True, exist_ok=True)
    target = qdir / source.name
    if target.exists():
        target = qdir / f"{source.stem}-{datetime.now().strftime('%H%M%S')}{source.suffix}"
    source.replace(target)
    target.with_suffix(target.suffix + ".reason.txt").write_text(
        f"{reason}\nquarantined_at={datetime.now().isoformat()}\n", encoding="utf-8"
    )
    return target


def backfill_legacy(root: Path = DEFAULT_ROOT, today: str | None = None, dry_run: bool = False) -> dict[str, Any]:
    """把 raw/ 里已存在但未登记 catalog 的历史会话补登记（不改 raw 内容，幂等）。"""
    today = today or _today()
    raw_dir = root / "raw"
    index_path = root / "index.jsonl"
    catalog = load_catalog(index_path)
    known_files = {e.get("raw_file") for e in catalog.values()}

    added = 0
    if raw_dir.exists():
        for raw_path in sorted(raw_dir.glob("*.json")):
            if raw_path.name in known_files:
                continue
            try:
                dump = json.loads(raw_path.read_text(encoding="utf-8"))
                records = extract_conversations(dump)
            except (ConversationParseError, json.JSONDecodeError, OSError):
                continue
            first_seen = _first_seen_from_mtime(raw_path, today)
            for rec in records:
                if rec.identity in catalog:
                    continue
                if not dry_run:
                    catalog[rec.identity] = {
                        "conversation_id": rec.identity,
                        "title": rec.title,
                        "raw_file": raw_path.name,
                        "source": "chatgpt",
                        "message_count": rec.message_count,
                        "update_time": rec.update_time,
                        "first_seen_at": first_seen,
                        "last_synced_at": first_seen,
                    }
                added += 1

    if not dry_run and added:
        write_catalog(index_path, catalog)
    return {"backfilled": added}


def _first_seen_from_mtime(path: Path, fallback: str) -> str:
    """回填首见日期的 fallback：用文件 mtime，而非从文件名 regex 解析（文件名不是数据库）。"""
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
    except OSError:
        return fallback


def ingest_inbox(root: Path = DEFAULT_ROOT, today: str | None = None, dry_run: bool = False) -> dict[str, Any]:
    """扫描 inbox/*.json，逐个增量同步，共享同一份 catalog。"""
    today = today or _today()
    inbox = root / "inbox"
    index_path = root / "index.jsonl"
    catalog = load_catalog(index_path)

    files = sorted(p for p in inbox.glob("*.json")) if inbox.exists() else []
    totals = {"files": len(files), "new": 0, "updated": 0, "unchanged": 0, "failed": 0, "imported_titles": []}
    for f in files:
        stats = ingest_file(f, root=root, today=today, dry_run=dry_run, catalog=catalog)
        if not stats["ok"]:
            totals["failed"] += 1
            continue
        totals["new"] += stats["new"]
        totals["updated"] += stats["updated"]
        totals["unchanged"] += stats["unchanged"]
        totals["imported_titles"].extend(stats["imported_titles"])

    if not dry_run and (totals["new"] or totals["updated"]):
        write_catalog(index_path, catalog)
    return totals


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tools.context.conversation_ingest",
        description="Human-AI 会话增量纳管（inbox → raw 快照 + index catalog；不进 stream.jsonl，不做语义/总结）",
    )
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help=f"conversations 根目录（默认 {DEFAULT_ROOT}）")
    parser.add_argument("--backfill", action="store_true", help="把 raw/ 内未登记的历史会话补登记进 index.jsonl")
    parser.add_argument("--dry-run", action="store_true", help="只统计不写入")
    args = parser.parse_args(argv)

    root = Path(args.root)
    today = _today()

    if args.backfill:
        bf = backfill_legacy(root, today=today, dry_run=args.dry_run)
        print(f"Backfill: 补登记历史会话 {bf['backfilled']} 条{'（dry-run）' if args.dry_run else ''}")

    print("Scanning inbox...")
    totals = ingest_inbox(root, today=today, dry_run=args.dry_run)
    print(f"\nFound:\n- {totals['files']} inbox files")
    if totals["imported_titles"]:
        print("\nImported / Updated:")
        for t in totals["imported_titles"]:
            print(f"- {t}")
    print(f"\nSkipped (unchanged): {totals['unchanged']}")
    if totals["failed"]:
        print(f"Quarantined (failed): {totals['failed']}（见 conversations/quarantine/）")
    print(f"\nCatalog → new {totals['new']}, updated {totals['updated']}{'（dry-run，未写入）' if args.dry_run else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
