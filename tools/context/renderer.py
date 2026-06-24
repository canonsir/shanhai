"""Cognition Snapshot Renderer（Commit 5B）。

把 AI 启动认知状态 `context/cognition.json` 渲染成**人读视图** `context/current-state.md`：

    context/cognition.json   ← 唯一派生认知枢纽（Agent 直接加载，机器读）
            │ render（纯函数：snapshot → markdown，确定性 / 可幂等 / 可 diff / 零依赖）
            ▼
    context/current-state.md ← 人读视图（review artifact）

边界（ADR 0000 §D6/§D9，GPT Commit 5B Review）：
- renderer 是 cognition.json 的**纯函数**：只读 cognition.json 这一个输入，不重跑 build、
  不读 project.yaml / registry.jsonl（避免二次构建产生 timestamp 漂移或第二事实源）。
- current-state.md 是**派生视图**，零新增信息：不内联「为什么这么决定」（那来自
  DecisionRecord.reason 与 decisions/records/*.md），只允许 link，禁止 renderer 杜撰。
- 不调 LLM、不读 raw、不做 semantic extraction / embedding / RAG。AI 不直接改本视图；
  要改改事实源 → 重跑 builder → 重跑 renderer。
- AI_CONTEXT.md 不由本模块生成（它是 Governance / bootstrap manifest，不是 Cognition 视图）。

唯一中心是 cognition.json；current-state.md 只是它面向人的其中一个视图（未来还可有 CLI/UI 视图）。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools.context.schema import CognitionSnapshot

DEFAULT_COGNITION = Path(".shanhai-meta/context/cognition.json")
DEFAULT_OUT = Path(".shanhai-meta/context/current-state.md")


def load_snapshot(path: Path) -> CognitionSnapshot:
    """读取 cognition.json → CognitionSnapshot（renderer 的唯一输入）。"""
    if not path.exists():
        raise FileNotFoundError(f"cognition.json 不存在：{path}（请先运行 tools.context.builder）")
    return CognitionSnapshot.from_json(path.read_text(encoding="utf-8"))


def _cell(s: str) -> str:
    """markdown 表格单元格转义（| 会破坏表结构）。"""
    return s.replace("|", "\\|").strip()


def render_markdown(snapshot: CognitionSnapshot) -> str:
    """CognitionSnapshot → current-state.md 文本（纯函数，确定性）。

    保持 snapshot 内既有顺序（builder 已按 id 稳定排序），不在此重排，做忠实投影。
    """
    ident = snapshot.identity
    phase = snapshot.phase
    lines: list[str] = []

    lines.append("# ShanHai — Current State（人读视图）")
    lines.append("")
    lines.append("> 本文件是 `context/cognition.json` 的**人读投影**（由 `tools/context/renderer.py` 渲染）。")
    lines.append("> 派生物，**请勿手改**（会被重渲染覆盖）。要更新内容：改事实源（`project.yaml` /")
    lines.append("> `decisions/registry.jsonl`）→ 重跑 `tools.context.builder` → 重跑 `tools.context.renderer`。")
    if snapshot.generated_at:
        lines.append(f">")
        lines.append(f"> generated_at: `{snapshot.generated_at}`（继承自 cognition.json）")
    lines.append(f">")
    lines.append(f"> cognition_id: `{snapshot.content_fingerprint()}`（content identity，内容不变则不变）")
    lines.append("")

    # Project Identity
    lines.append("## Project Identity")
    lines.append("")
    lines.append(f"- **Project**：{ident.project}")
    lines.append(f"- **Mission**：{ident.mission}")
    lines.append(f"- **Description**：{ident.description}")
    lines.append("")

    # Current Phase
    lines.append("## Current Phase")
    lines.append("")
    lines.append(f"- **Phase**：{phase.name}")
    lines.append(f"- **Status**：{phase.status}")
    lines.append("")

    # Decisions
    lines.append("## Decisions（已确认）")
    lines.append("")
    if snapshot.decisions:
        lines.append("| ID | Type | Title |")
        lines.append("|---|---|---|")
        for d in snapshot.decisions:
            lines.append(f"| {_cell(d.id)} | {_cell(d.type)} | {_cell(d.title)} |")
        lines.append("")
        lines.append("> 「为什么这么决定 / 否决了什么」见 `decisions/registry.jsonl` 的 `reason` 与 "
                     "`decisions/records/*.md`（本视图不内联理由，避免成为第二事实源）。")
    else:
        lines.append("（暂无已确认决策）")
    lines.append("")

    # Constraints (Frozen)
    lines.append("## Constraints（Frozen，AI 不得擅自修改）")
    lines.append("")
    if snapshot.constraints:
        for c in snapshot.constraints:
            lines.append(f"- [{c.type}] {c.value}")
    else:
        lines.append("（暂无冻结约束）")
    lines.append("")

    # Future Direction
    lines.append("## Future Direction（未来方向，当前不开发）")
    lines.append("")
    if snapshot.future_directions:
        for f in snapshot.future_directions:
            suffix = f"（来源 {f.source}）" if f.source else ""
            lines.append(f"- {f.title}{suffix}")
    else:
        lines.append("（暂无）")
    lines.append("")

    # References（仅 link，不内联内容）
    lines.append("## References")
    lines.append("")
    lines.append("- [Decision Registry（结构事实源）](../decisions/registry.jsonl)")
    lines.append("- [Decision Records（人读解释 / 为什么这么决定）](../decisions/records/)")
    lines.append("- [ADR 0000：项目元上下文架构](../../docs/架构决策记录/0000-项目元上下文架构.md)")
    lines.append("")

    return "\n".join(lines)


def write_markdown(text: str, out_path: Path) -> None:
    """写 current-state.md（末尾换行，稳定 diff）。"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text.rstrip("\n") + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tools.context.renderer",
        description="Cognition Snapshot Renderer：context/cognition.json → context/current-state.md（人读视图，纯函数，禁 LLM）",
    )
    parser.add_argument("--cognition", default=str(DEFAULT_COGNITION), help=f"输入（默认 {DEFAULT_COGNITION}）")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help=f"输出（默认 {DEFAULT_OUT}）")
    args = parser.parse_args(argv)

    try:
        snapshot = load_snapshot(Path(args.cognition))
    except FileNotFoundError as exc:
        print(f"[renderer] {exc}", file=sys.stderr)
        return 1

    write_markdown(render_markdown(snapshot), Path(args.out))
    print(
        f"[renderer] current-state.md 已生成：{args.out}"
        f"（decisions={len(snapshot.decisions)}，constraints={len(snapshot.constraints)}，"
        f"future_directions={len(snapshot.future_directions)}）"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
