"""Cognition Snapshot Renderer 测试（见 ADR 0000 Commit 5B：Cognition Snapshot Renderer）。

运行：python3 -m tests.test_cognition_renderer
覆盖：
  1. render 是纯函数：同一 snapshot → 同一 markdown（确定性 / 幂等）
  2. 视图忠实投影：identity/phase/decisions/constraints/future_directions 全部出现，且无杜撰理由
  3. References 只给 link（不内联「为什么」）；frozen 约束逐条出现
  4. 仓库 current-state.md 与 renderer 现算一致（派生未漂移 / 未被手改）
  5. renderer 是 cognition.json 的纯函数：缺文件 fail（不静默重跑 build）
  6. 边界：renderer 不接 LLM/embedding/RAG，不 import yaml，不读 project.yaml/registry（仅 stdlib + 本层 schema）
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from tools.context.renderer import (
    DEFAULT_COGNITION,
    DEFAULT_OUT,
    load_snapshot,
    render_markdown,
    write_markdown,
)
from tools.context.schema import (
    CognitionConstraint,
    CognitionDecisionRef,
    CognitionFutureDirection,
    CognitionIdentity,
    CognitionPhase,
    CognitionSnapshot,
)

_REPO = Path(__file__).resolve().parent.parent


def _sample() -> CognitionSnapshot:
    return CognitionSnapshot(
        identity=CognitionIdentity(project="ShanHai", mission="M-mission", description="D-desc"),
        phase=CognitionPhase(name="Phase X", status="building"),
        decisions=[
            CognitionDecisionRef(id="DEC-0001", title="决策一", type="architecture"),
            CognitionDecisionRef(id="DEC-0003", title="决策三", type="strategy"),
        ],
        constraints=[
            CognitionConstraint(type="frozen", value="冻结 A"),
            CognitionConstraint(type="frozen", value="冻结 B"),
        ],
        future_directions=[CognitionFutureDirection(title="未来方向 X", source="DEC-0004")],
        generated_at="2026-06-24T00:00:00+00:00",
        metadata={"generated_by": "tools/context/builder.py"},
    )


def test_render_deterministic() -> None:
    snap = _sample()
    a = render_markdown(snap)
    b = render_markdown(snap)
    assert a == b, "render 必须是纯函数：同输入逐字符一致"
    print("[OK] render 确定性：同一 snapshot 渲染逐字符一致（幂等）")


def test_render_faithful_projection() -> None:
    md = render_markdown(_sample())
    # identity / phase
    assert "M-mission" in md and "D-desc" in md
    assert "Phase X" in md and "building" in md
    # decisions（id + type + title 都在）
    for token in ["DEC-0001", "决策一", "architecture", "DEC-0003", "决策三", "strategy"]:
        assert token in md, f"决策投影缺失：{token}"
    # constraints
    assert "冻结 A" in md and "冻结 B" in md
    # future direction + provenance
    assert "未来方向 X" in md and "DEC-0004" in md
    print("[OK] 忠实投影：identity/phase/decisions/constraints/future_directions 全部出现")


def test_no_fabricated_reason() -> None:
    md = render_markdown(_sample())
    # 「为什么」只能 link 到 registry/records，不在视图内联编造叙述
    assert "registry.jsonl" in md and "records/" in md
    assert "因为未来" not in md, "renderer 不得自行杜撰决策理由"
    print("[OK] 不杜撰理由：why 仅 link 至 registry/records，视图不内联")


def test_repo_current_state_matches_renderer() -> None:
    cog = _REPO / DEFAULT_COGNITION
    out = _REPO / DEFAULT_OUT
    assert cog.exists(), "仓库应已生成 cognition.json"
    assert out.exists(), "仓库应已生成 current-state.md"
    snap = load_snapshot(cog)
    fresh = render_markdown(snap).rstrip("\n") + "\n"
    on_disk = out.read_text(encoding="utf-8")
    assert fresh == on_disk, "current-state.md 与现算结果不一致：派生漂移或被手改"
    print("[OK] 仓库 current-state.md 与 renderer 现算一致（派生未漂移）")


def test_renderer_is_pure_function_of_cognition() -> None:
    # 缺 cognition.json 应直接 fail（不回退去重跑 build / 不读其它事实源）
    with tempfile.TemporaryDirectory() as d:
        missing = Path(d) / "nope.json"
        raised = False
        try:
            load_snapshot(missing)
        except FileNotFoundError:
            raised = True
        assert raised, "renderer 唯一输入是 cognition.json，缺失必须 fail-loud"

        # 给定 snapshot → 写出 → 内容可被复算（纯函数闭环）
        snap = _sample()
        out = Path(d) / "current-state.md"
        write_markdown(render_markdown(snap), out)
        assert out.read_text(encoding="utf-8") == render_markdown(snap).rstrip("\n") + "\n"
    print("[OK] 纯函数：renderer 只依赖 cognition.json，缺失 fail-loud")


def test_no_llm_or_extra_deps() -> None:
    import ast

    import tools.context.renderer as mod

    with open(mod.__file__, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    allowed_roots = {"argparse", "sys", "pathlib", "__future__", "tools"}
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    forbidden = {"openai", "anthropic", "numpy", "faiss", "chromadb",
                 "langchain", "sentence_transformers", "pydantic", "yaml"}
    assert not (imported & forbidden), f"renderer 禁止重依赖/LLM/YAML：{imported & forbidden}"
    assert imported <= allowed_roots, f"出现未预期依赖：{imported - allowed_roots}"
    # 不读 builder/decisions（不重跑 build，不读 project.yaml/registry）——保持纯视图
    assert "builder" not in {n for n in imported}, "renderer 不应 import builder（避免二次构建）"
    print("[OK] 边界：renderer 不接 LLM/embedding/RAG，不 import yaml，仅 stdlib + schema")


def main() -> None:
    test_render_deterministic()
    test_render_faithful_projection()
    test_no_fabricated_reason()
    test_repo_current_state_matches_renderer()
    test_renderer_is_pure_function_of_cognition()
    test_no_llm_or_extra_deps()
    print("\nCognition Renderer 测试全部通过 ✅")


if __name__ == "__main__":
    main()
