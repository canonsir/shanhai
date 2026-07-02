"""Context Health Check 测试（见 ADR 0000 Commit 5C：Context Foundation Closure）。

运行：python3 -m tests.test_context_health
覆盖：
  1. 健康仓库：check_health() 返回空列表（OK）
  2. 缺事实源：缺 registry.jsonl → 报 missing source
  3. broken event reference：决策回链指向 stream 不存在的 evt_id → 报 broken event reference
  4. 缺派生物：缺 cognition.json / current-state.md → 报 missing projection
  5. 边界：health 零依赖、不接 LLM/YAML/embedding（仅 stdlib + 本层 decisions）
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from tools.context.health import DEFAULT_ROOT, check_health

_REPO = Path(__file__).resolve().parent.parent
_REAL_ROOT = _REPO / DEFAULT_ROOT


def _make_root(d: Path) -> Path:
    """构造一个最小健康的元上下文层（满足 Source/Integrity/Projection）。"""
    root = d / ".shanhai-meta"
    (root / "decisions").mkdir(parents=True)
    (root / "events").mkdir(parents=True)
    (root / "context").mkdir(parents=True)

    (root / "project.yaml").write_text("project: T\n", encoding="utf-8")
    # 一条事件 + 一条引用它的决策（回链命中）
    (root / "events" / "stream.jsonl").write_text(
        json.dumps({"schema_version": "1.0", "id": "evt_1", "type": "decision",
                    "timestamp": "2026-06-24T00:00:00+00:00"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (root / "decisions" / "registry.jsonl").write_text(
        json.dumps({"schema_version": "1.0", "id": "DEC-1", "decision": "d", "status": "accepted",
                    "related_context_events": ["evt_1"]}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (root / "context" / "cognition.json").write_text("{}", encoding="utf-8")
    (root / "context" / "current-state.md").write_text("# x\n", encoding="utf-8")
    return root


def test_healthy_repo() -> None:
    # 真实仓库应当健康（builder/renderer 已生成产物，回链完整）
    problems = check_health(_REAL_ROOT)
    assert problems == [], f"仓库应健康，却发现：{problems}"
    print("[OK] 健康仓库：check_health 返回空（OK）")


def test_missing_source() -> None:
    with tempfile.TemporaryDirectory() as d:
        root = _make_root(Path(d))
        (root / "decisions" / "registry.jsonl").unlink()
        problems = check_health(root)
        assert any("missing source: registry.jsonl" in p for p in problems), problems
    print("[OK] 缺事实源：缺 registry.jsonl 被报 missing source")


def test_broken_event_reference() -> None:
    with tempfile.TemporaryDirectory() as d:
        root = _make_root(Path(d))
        # 把决策回链改成不存在的 evt_id
        (root / "decisions" / "registry.jsonl").write_text(
            json.dumps({"schema_version": "1.0", "id": "DEC-1", "decision": "d", "status": "accepted",
                        "related_context_events": ["evt_NOPE"]}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        problems = check_health(root)
        assert any("broken event reference" in p and "evt_NOPE" in p for p in problems), problems
    print("[OK] broken event reference：回链指向不存在 evt_id 被报")


def test_missing_projection() -> None:
    with tempfile.TemporaryDirectory() as d:
        root = _make_root(Path(d))
        (root / "context" / "cognition.json").unlink()
        problems = check_health(root)
        assert any("missing projection: cognition.json" in p for p in problems), problems
    print("[OK] 缺派生物：缺 cognition.json 被报 missing projection")


def test_no_llm_or_extra_deps() -> None:
    import ast

    import tools.context.health as mod

    with open(mod.__file__, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    allowed_roots = {"argparse", "json", "sys", "pathlib", "__future__", "tools"}
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    forbidden = {"openai", "anthropic", "numpy", "faiss", "chromadb",
                 "langchain", "sentence_transformers", "pydantic", "yaml"}
    assert not (imported & forbidden), f"health 禁止重依赖/LLM/YAML：{imported & forbidden}"
    assert imported <= allowed_roots, f"出现未预期依赖：{imported - allowed_roots}"
    print("[OK] 边界：health 零依赖，不接 LLM/embedding/RAG，不 import yaml")


def main() -> None:
    test_healthy_repo()
    test_missing_source()
    test_broken_event_reference()
    test_missing_projection()
    test_no_llm_or_extra_deps()
    print("\nContext Health 测试全部通过 ✅")


if __name__ == "__main__":
    main()
