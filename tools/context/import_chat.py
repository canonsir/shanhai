"""Raw conversation export → ContextEvent 流（Commit 3B：Context Importer）。

职责单一：把已归档的原始导出（conversations/raw/*.json）**搬运 + 结构化**为
ContextEvent，逐行 append 进 events/stream.jsonl。建立 Raw → ContextEvent 的桥。

严格边界（ADR 0000 §D5/§D6，经 Review 限定）——只做：
  raw json reader → ContextEvent 生成 → JSONL append → 幂等 → provenance 保留
绝不做：AI 调用 / 自动总结 / decision extraction / 重要性判断 / embedding / RAG / speaker 推理。

约定：
- actor 一律 unknown：忠实搬运，不推断「谁说的」（§D5）。
- provenance：source.kind=chatgpt_export，source.file=<归档文件名>，source.ref=raw#<msg_id>。
  支撑 AI 可审计性（Decision → Evidence ContextEvent → Origin raw#id）。
- 幂等：以 source.ref 去重，stream.jsonl 已存在的不重复生成；可安全重跑。
- event id 由 source.ref 确定性派生（同一 raw 消息恒得同一 id），便于稳定引用。
- 媒体丢失客观标记：文本含 `media pointer` / `sediment://` → has_lost_media=true（不删原文、不臆测其余）。
- 无逐条消息时间：timestamp 取入流时间；真实顺序经 metadata.seq 保留，会话级
  updateTime 原样存 metadata.conversation_update_time（§D5：不把会话时间伪造成消息时间）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable

from tools.context.schema import (
    ContextEvent,
    EventActor,
    EventContent,
    EventSource,
    EventType,
    SourceKind,
    now_iso,
)

# 客观可见的媒体丢失标记（导出后媒体已退化为文本指针）。
_MEDIA_MARKERS = ("media pointer", "sediment://")

DEFAULT_STREAM = Path(".shanhai-meta/events/stream.jsonl")


def _event_id(ref: str) -> str:
    """由 source.ref 确定性派生 event id：同一 raw 消息重跑恒得同一 id。"""
    digest = hashlib.sha1(ref.encode("utf-8")).hexdigest()[:16]
    return f"evt_{digest}"


def _has_lost_media(text: str) -> bool:
    low = text.lower()
    return any(m in low for m in _MEDIA_MARKERS)


def load_existing_refs(stream_path: Path) -> set[str]:
    """读取 stream.jsonl 中已存在的 source.ref 集合（幂等去重依据）。"""
    refs: set[str] = set()
    if not stream_path.exists():
        return refs
    with stream_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ref = json.loads(line).get("source", {}).get("ref")
            if ref:
                refs.add(ref)
    return refs


def iter_events(raw: dict[str, Any], source_file: str) -> Iterable[ContextEvent]:
    """把一份 raw 导出忠实展开为 ContextEvent（不解析语义、不推断角色）。"""
    for conv in raw.get("conversations", []):
        conv_id = conv.get("id")
        conv_title = conv.get("title")
        conv_update = conv.get("updateTime")
        for seq, msg in enumerate(conv.get("messages", [])):
            text = msg.get("text", "")
            if not isinstance(text, str) or not text.strip():
                continue  # 跳过空占位（如 client-created-root）
            raw_id = msg.get("id", f"seq{seq}")
            ref = f"raw#{raw_id}"
            yield ContextEvent(
                id=_event_id(f"{source_file}#{raw_id}"),
                type=EventType.CONVERSATION,
                timestamp=now_iso(),
                source=EventSource(kind=SourceKind.CHATGPT_EXPORT, file=source_file, ref=ref),
                actor=EventActor(),  # role=unknown，不推断
                content=EventContent(text=text, has_lost_media=_has_lost_media(text)),
                metadata={
                    "seq": seq,
                    "conversation_id": conv_id,
                    "conversation_title": conv_title,
                    "conversation_update_time": conv_update,
                },
            )


def import_file(source: Path, stream_path: Path, dry_run: bool = False) -> dict[str, int]:
    """导入一份 raw 文件到 stream.jsonl，返回统计。幂等：已存在 ref 跳过。"""
    raw = json.loads(source.read_text(encoding="utf-8"))
    existing = load_existing_refs(stream_path)

    new_events: list[ContextEvent] = []
    skipped_dup = 0
    media_lost = 0
    for ev in iter_events(raw, source_file=source.name):
        if ev.source.ref in existing:
            skipped_dup += 1
            continue
        existing.add(ev.source.ref)  # 防同次重复
        if ev.content.has_lost_media:
            media_lost += 1
        new_events.append(ev)

    if not dry_run and new_events:
        stream_path.parent.mkdir(parents=True, exist_ok=True)
        with stream_path.open("a", encoding="utf-8") as f:
            for ev in new_events:
                f.write(ev.to_json() + "\n")

    return {
        "new": len(new_events),
        "skipped_duplicate": skipped_dup,
        "with_lost_media": media_lost,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tools.context.import_chat",
        description="Raw conversation export → ContextEvent 流（搬运+结构化，不做语义/总结/推理）",
    )
    parser.add_argument(
        "--source",
        required=True,
        help="原始导出文件路径（.shanhai-meta/conversations/raw/*.json）",
    )
    parser.add_argument(
        "--stream",
        default=str(DEFAULT_STREAM),
        help=f"目标 ContextEvent 流（默认 {DEFAULT_STREAM}）",
    )
    parser.add_argument("--dry-run", action="store_true", help="只统计不写入")
    args = parser.parse_args(argv)

    source = Path(args.source)
    if not source.exists():
        print(f"[import_chat] 源文件不存在：{source}", file=sys.stderr)
        return 1

    stats = import_file(source, Path(args.stream), dry_run=args.dry_run)
    mode = "（dry-run，未写入）" if args.dry_run else ""
    print(
        f"[import_chat] {source.name} → {args.stream}{mode}："
        f"新增 {stats['new']}，跳过重复 {stats['skipped_duplicate']}，"
        f"媒体丢失标记 {stats['with_lost_media']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
