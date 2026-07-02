"""Decision Registry 工具（Commit 4：Decision Registry）。

职责单一：读取 `decisions/registry.jsonl`（**唯一结构事实源**，每行一条 DecisionRecord），
并能把它渲染成一个**瞬态人读视图**打印到 stdout。建立 ContextEvent → Decision 的认知层。

为什么不落地第二份 registry.yaml（Commit 4 Review 修正，遵 ADR 0000「不维护重复事实」）：
- registry.jsonl 是机器读事实源；records/*.md 是人读解释层。两者已覆盖「机器 + 人」需求。
- 再派生一份 registry.yaml 会产生第三份状态，未来必然出现 jsonl 与 yaml 不一致。
- 需要快速浏览时，本工具按需把 jsonl 渲染成瞬态视图打印（不落盘）；未来由 context doctor 接管。

边界（ADR 0000 §D5/§D6）：纯 Python 标准库；不调 LLM、不做自动总结、不做 decision
extraction、不推断角色。决策内容由人工提炼写入 registry.jsonl，本模块只做加载 + 视图渲染。
load_registry 供 Commit 5 builder 复用（事实源 → context/ 派生）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools.context.schema import DecisionRecord

DEFAULT_REGISTRY = Path(".shanhai-meta/decisions/registry.jsonl")


def load_registry(registry_path: Path) -> list[DecisionRecord]:
    """逐行加载 registry.jsonl 为 DecisionRecord 列表（唯一结构事实源，机器读）。"""
    records: list[DecisionRecord] = []
    if not registry_path.exists():
        return records
    with registry_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(DecisionRecord.from_json(line))
    return records


def _render_list(label: str, items: list[str]) -> list[str]:
    if not items:
        return []
    return [f"  {label}:"] + [f"    - {it}" for it in items]


def render_view(records: list[DecisionRecord]) -> str:
    """把 DecisionRecord 列表渲染成瞬态人读视图（仅打印，不落盘）。"""
    lines: list[str] = [f"Decision Registry（{len(records)} 条，事实源 registry.jsonl）", ""]
    for r in records:
        lines.append(f"[{r.id}] ({r.type}/{r.status.value}) {r.title or r.decision}")
        lines.append(f"  decision: {r.decision}")
        lines.extend(_render_list("reason", r.reason))
        lines.extend(_render_list("alternatives", r.alternatives))
        lines.extend(_render_list("rejected_alternatives", r.rejected_alternatives))
        lines.extend(_render_list("related_context_events", r.related_context_events))
        lines.extend(_render_list("related", r.related))
        if r.source:
            lines.append(f"  source: {r.source}")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tools.context.decisions",
        description="Decision Registry：加载 registry.jsonl 并打印瞬态人读视图（不落盘，无第二事实源）",
    )
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY), help=f"事实源（默认 {DEFAULT_REGISTRY}）")
    args = parser.parse_args(argv)

    registry = Path(args.registry)
    if not registry.exists():
        print(f"[decisions] registry 不存在：{registry}", file=sys.stderr)
        return 1

    records = load_registry(registry)
    print(render_view(records))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
