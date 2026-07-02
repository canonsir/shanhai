"""Context Health Check（Commit 5C，极简——不是 context doctor）。

对 Project Context Layer 做一次**确定性体检**，回答「这套元上下文是否自洽」：

- Source       事实源是否齐备：project.yaml / decisions/registry.jsonl / events/stream.jsonl 存在。
- Integrity    可审计性桥是否完整：每条 DecisionRecord.related_context_events 引用的 evt_id
               都能在 events/stream.jsonl 找到（不存在 broken event reference）。
- Projection   派生物是否已生成：context/cognition.json / context/current-state.md 存在。

输出：全过打印 `OK`（返回 0）；否则打印 `FAILED:` + 逐条缺陷（返回 1）。

边界（ADR 0000 §D6）：纯 Python 标准库，零依赖。只读、不修复、不调 LLM、不做 embedding/RAG。
刻意保持极简：复杂的自动修复 / 报告留未来（不在 Context Foundation 范围）。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.context.decisions import load_registry

DEFAULT_ROOT = Path(".shanhai-meta")


def _stream_event_ids(stream_path: Path) -> set[str]:
    ids: set[str] = set()
    if not stream_path.exists():
        return ids
    with stream_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                ids.add(json.loads(line)["id"])
    return ids


def check_health(root: Path = DEFAULT_ROOT) -> list[str]:
    """返回缺陷列表（空列表 = 健康）。确定性、只读。"""
    project = root / "project.yaml"
    registry = root / "decisions" / "registry.jsonl"
    stream = root / "events" / "stream.jsonl"
    cognition = root / "context" / "cognition.json"
    current_state = root / "context" / "current-state.md"

    problems: list[str] = []

    # Source：事实源存在
    for label, p in (("project.yaml", project), ("registry.jsonl", registry), ("stream.jsonl", stream)):
        if not p.exists():
            problems.append(f"missing source: {label} ({p})")

    # Integrity：决策回链全部命中 stream.jsonl 的 evt_id
    if registry.exists() and stream.exists():
        event_ids = _stream_event_ids(stream)
        for rec in load_registry(registry):
            for ref in rec.related_context_events:
                if ref not in event_ids:
                    problems.append(f"broken event reference: {rec.id} → {ref} (not in stream.jsonl)")

    # Projection：派生物已生成
    for label, p in (("cognition.json", cognition), ("current-state.md", current_state)):
        if not p.exists():
            problems.append(f"missing projection: {label} ({p})")

    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tools.context.health",
        description="Context Health Check：检查 .shanhai-meta/ 事实源 / 回链完整性 / 派生物（只读，禁 LLM）",
    )
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help=f"元上下文层根目录（默认 {DEFAULT_ROOT}）")
    args = parser.parse_args(argv)

    problems = check_health(Path(args.root))
    if not problems:
        print("OK")
        return 0
    print("FAILED:")
    for p in problems:
        print(f"- {p}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
