"""Cognition Snapshot Builder（Commit 5A）。

把事实源**确定性装配**为 AI Agent 启动认知契约 `context/cognition.json`：

    project.yaml + decisions/registry.jsonl
            │ build（确定性 join，纯 stdlib，可幂等重跑/可 diff/可审计）
            ▼
    context/cognition.json   ← CognitionSnapshot

铁律（ADR 0000 §D6/§D9，GPT Commit 5 Review）：
- 这是**确定性投影**，不是 LLM 摘要：不调 LLM、不读 conversations/raw、不做 semantic
  extraction / embedding / RAG，不读 stream.jsonl（Commit 5A 仅 project.yaml + registry.jsonl）。
- cognition.json 是派生物，AI 不直接改；要改改事实源再重跑。
- 不引入 PyYAML：project.yaml 由一个**极小的、只服务 cognition 投影**的 reader 读取——
  只认顶层标量（project/description/phase/mission/phase_status）+ 顶层 frozen 块列表；
  participants/baseline 等结构一律忽略；已知标量键若出现不支持的嵌套结构则 fail-loud
  （Meta Layer 最大风险不是失败，而是安静地产生错误认知）。

Commit 5B 再做 cognition.json → current-state.md 的人读 renderer（本模块不产 markdown）。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.context.decisions import load_registry
from tools.context.schema import (
    CognitionConstraint,
    CognitionDecisionRef,
    CognitionFutureDirection,
    CognitionIdentity,
    CognitionPhase,
    CognitionSnapshot,
    DecisionStatus,
    now_iso,
)

DEFAULT_PROJECT = Path(".shanhai-meta/project.yaml")
DEFAULT_REGISTRY = Path(".shanhai-meta/decisions/registry.jsonl")
DEFAULT_OUT = Path(".shanhai-meta/context/cognition.json")

# 仅这些顶层标量参与 cognition 投影；出现于不支持结构时 fail-loud。
_SCALAR_KEYS = frozenset({"project", "description", "phase", "mission", "phase_status"})
# 顶层块列表（- item）键。
_LIST_KEYS = frozenset({"frozen"})


class ProjectYamlError(ValueError):
    """project.yaml 结构不被 cognition reader 支持（fail-loud，不静默降级）。"""


def _unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in {'"', "'"}:
        return s[1:-1]
    return s


def read_project_yaml(path: Path) -> dict[str, object]:
    """极小 project.yaml reader（非通用 YAML parser，只服务 CognitionSnapshot 投影）。

    支持：顶层 `key: value` 标量、顶层 `frozen:` 后的 `  - item` 块列表。
    忽略：participants / baseline 等其它顶层块结构（连同其缩进体一并跳过）。
    fail-loud：已知标量键（_SCALAR_KEYS）出现嵌套结构，或 frozen 出现非列表结构。
    返回：{"project","description","phase","mission","phase_status": str, "frozen": list[str]}。
    """
    if not path.exists():
        raise ProjectYamlError(f"project.yaml 不存在：{path}")

    raw_lines = path.read_text(encoding="utf-8").splitlines()
    # 预处理：丢弃整行注释与空行，保留 (indent, stripped) 供结构判断。
    lines: list[str] = [ln for ln in raw_lines if ln.strip() and not ln.lstrip().startswith("#")]

    result: dict[str, object] = {k: "" for k in _SCALAR_KEYS}
    result["frozen"] = []

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if line[:1].isspace():
            # 顶层循环不应直接遇到缩进行（缩进体应被其 owner 消费）；保险起见跳过。
            i += 1
            continue
        if ":" not in line:
            raise ProjectYamlError(f"无法解析的顶层行（缺 ':'）：{line!r}")

        key, _, inline = line.partition(":")
        key = key.strip()
        inline = inline.strip()

        # 收集该 key 的缩进体（下方所有缩进行）。
        body: list[str] = []
        j = i + 1
        while j < n and lines[j][:1].isspace():
            body.append(lines[j])
            j += 1

        if inline:
            # 顶层标量（带值）。
            if body:
                raise ProjectYamlError(f"unsupported project.yaml structure：标量键 '{key}' 不应再带缩进体")
            if key in _SCALAR_KEYS:
                result[key] = _unquote(inline)
            # 其它带值顶层键（如 version）：忽略。
        else:
            # 空 inline → 块开启（列表/映射）。
            if key in _LIST_KEYS:
                items: list[str] = []
                for b in body:
                    stripped = b.strip()
                    if not stripped.startswith("- "):
                        raise ProjectYamlError(f"unsupported project.yaml structure：'{key}' 期望列表项 '- '，得到 {stripped!r}")
                    items.append(_unquote(stripped[2:]))
                result[key] = items
            elif key in _SCALAR_KEYS:
                # 已知标量键却是块结构（如 phase: 下挂 name/...）→ fail-loud。
                raise ProjectYamlError(f"unsupported project.yaml structure：标量键 '{key}' 不支持嵌套结构")
            # 其它块键（participants/baseline/…）：连同缩进体忽略。
        i = j

    return result


def build_snapshot(
    project_path: Path = DEFAULT_PROJECT,
    registry_path: Path = DEFAULT_REGISTRY,
    generated_at: str | None = None,
) -> CognitionSnapshot:
    """从 project.yaml + registry.jsonl 确定性装配 CognitionSnapshot。

    generated_at 可注入固定值以便测试断言「重建逐字节一致」；默认取 now_iso()。
    """
    proj = read_project_yaml(project_path)
    records = load_registry(registry_path)
    # id 稳定排序，保证可 diff / 幂等。
    records = sorted(records, key=lambda r: r.id)

    identity = CognitionIdentity(
        project=str(proj["project"]),
        mission=str(proj["mission"]),
        description=str(proj["description"]),
    )
    phase = CognitionPhase(name=str(proj["phase"]), status=str(proj["phase_status"]))

    decisions = [
        CognitionDecisionRef(id=r.id, title=r.title or r.decision, type=r.type, source="registry.jsonl")
        for r in records
        if r.status is DecisionStatus.ACCEPTED
    ]
    future_directions = [
        CognitionFutureDirection(title=r.title or r.decision, source=r.id)
        for r in records
        if r.status is DecisionStatus.PROPOSED
    ]
    constraints = [CognitionConstraint(type="frozen", value=v) for v in proj["frozen"]]  # type: ignore[union-attr]

    return CognitionSnapshot(
        identity=identity,
        phase=phase,
        decisions=decisions,
        constraints=constraints,
        future_directions=future_directions,
        generated_at=generated_at if generated_at is not None else now_iso(),
        metadata={
            "generated_by": "tools/context/builder.py",
            "inputs": ["project.yaml", "decisions/registry.jsonl"],
        },
    )


def write_snapshot(snapshot: CognitionSnapshot, out_path: Path) -> None:
    """写 cognition.json（pretty + sort_keys，稳定 diff；末尾换行）。"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)
    out_path.write_text(text + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tools.context.builder",
        description="Cognition Snapshot Builder：project.yaml + registry.jsonl → context/cognition.json（确定性装配，禁 LLM）",
    )
    parser.add_argument("--project", default=str(DEFAULT_PROJECT), help=f"项目元信息（默认 {DEFAULT_PROJECT}）")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY), help=f"决策事实源（默认 {DEFAULT_REGISTRY}）")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help=f"输出（默认 {DEFAULT_OUT}）")
    args = parser.parse_args(argv)

    try:
        snapshot = build_snapshot(Path(args.project), Path(args.registry))
    except ProjectYamlError as exc:
        print(f"[builder] {exc}", file=sys.stderr)
        return 1

    write_snapshot(snapshot, Path(args.out))
    print(
        f"[builder] cognition.json 已生成：{args.out}"
        f"（decisions={len(snapshot.decisions)}，constraints={len(snapshot.constraints)}，"
        f"future_directions={len(snapshot.future_directions)}）"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
