"""Cognition Snapshot Builder 测试（见 ADR 0000 Commit 5A：Cognition Snapshot Builder MVP）。

运行：python3 -m tests.test_cognition_builder
覆盖：
  1. CognitionSnapshot object→dict→json 可逆（含嵌套 identity/phase/decisions/constraints/future_directions）
  2. mini yaml reader：顶层标量 + frozen 块列表正确解析，participants/baseline 被忽略
  3. yaml reader fail-loud：已知标量键出现嵌套结构 → ProjectYamlError（不静默降级产生错误认知）
  4. 确定性装配：accepted→decisions、proposed→future_directions、frozen→constraints，id 稳定排序
  5. 确定性重建：固定 generated_at 时同输入逐字节一致（幂等可 diff）
  6. 仓库 cognition.json 可被 schema 回读，且与 builder 现算结果一致（派生未漂移）
  7. 边界：builder 不接 LLM/embedding/RAG，不 import yaml（仅 stdlib + 本层 schema/decisions）
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from tools.context.builder import (
    DEFAULT_OUT,
    DEFAULT_PROJECT,
    DEFAULT_REGISTRY,
    ProjectYamlError,
    build_snapshot,
    read_project_yaml,
    write_snapshot,
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

_GOOD_YAML = """\
# comment
project: ShanHai
description: desc here
mission: do the thing
phase: "Phase X（建设中）"
phase_status: building

baseline:
  develop: abc123
  main: def456

participants:
  - { id: human-owner, role: Owner }

frozen:
  - Frozen A
  - "Frozen B"
"""

_BAD_YAML = """\
project: ShanHai
phase:
  name: nested-not-supported
  status: building
"""


def _write(dir_: Path, name: str, text: str) -> Path:
    p = dir_ / name
    p.write_text(text, encoding="utf-8")
    return p


def test_snapshot_roundtrip() -> None:
    snap = CognitionSnapshot(
        identity=CognitionIdentity(project="P", mission="M", description="D"),
        phase=CognitionPhase(name="ph", status="building"),
        decisions=[CognitionDecisionRef(id="DEC-1", title="t", type="architecture")],
        constraints=[CognitionConstraint(type="frozen", value="X")],
        future_directions=[CognitionFutureDirection(title="f", source="DEC-9")],
        generated_at="2026-06-24T00:00:00+00:00",
        metadata={"generated_by": "tools/context/builder.py"},
    )
    back = CognitionSnapshot.from_json(snap.to_json())
    assert back == snap
    assert back.identity.mission == "M"
    assert back.decisions[0].source == "registry.jsonl"  # 默认 provenance
    print("[OK] CognitionSnapshot object→dict→json 可逆（含嵌套与 _metadata）")


def test_yaml_reader_supported_structure() -> None:
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        proj = _write(d, "project.yaml", _GOOD_YAML)
        parsed = read_project_yaml(proj)
    assert parsed["project"] == "ShanHai"
    assert parsed["description"] == "desc here"
    assert parsed["mission"] == "do the thing"
    assert parsed["phase"] == "Phase X（建设中）"  # 引号被去除
    assert parsed["phase_status"] == "building"
    assert parsed["frozen"] == ["Frozen A", "Frozen B"]  # 块列表 + 去引号
    print("[OK] mini yaml reader：标量 + frozen 列表正确，participants/baseline 忽略")


def test_yaml_reader_fail_loud() -> None:
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        proj = _write(d, "project.yaml", _BAD_YAML)
        raised = False
        try:
            read_project_yaml(proj)
        except ProjectYamlError as exc:
            raised = True
            assert "unsupported project.yaml structure" in str(exc)
        assert raised, "已知标量键的嵌套结构必须 fail-loud，不得静默降级"
    print("[OK] fail-loud：标量键嵌套结构抛 ProjectYamlError（不静默产生错误认知）")


def test_deterministic_assembly() -> None:
    import json

    registry = (
        json.dumps({
            "schema_version": "1.0", "id": "DEC-0002", "decision": "d2", "status": "accepted",
            "type": "architecture", "title": "T2",
        }, ensure_ascii=False)
        + "\n"
        + json.dumps({
            "schema_version": "1.0", "id": "DEC-0001", "decision": "d1", "status": "accepted",
            "type": "architecture", "title": "T1",
        }, ensure_ascii=False)
        + "\n"
        + json.dumps({
            "schema_version": "1.0", "id": "DEC-0009", "decision": "future", "status": "proposed",
            "type": "strategy", "title": "F9",
        }, ensure_ascii=False)
        + "\n"
    )
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        proj = _write(d, "project.yaml", _GOOD_YAML)
        reg = _write(d, "registry.jsonl", registry)
        snap = build_snapshot(proj, reg, generated_at="2026-06-24T00:00:00+00:00")

    # accepted → decisions（id 升序），proposed → future_directions
    assert [x.id for x in snap.decisions] == ["DEC-0001", "DEC-0002"]
    assert snap.decisions[0].title == "T1"
    assert [x.source for x in snap.future_directions] == ["DEC-0009"]
    # frozen → constraints
    assert [c.value for c in snap.constraints] == ["Frozen A", "Frozen B"]
    assert all(c.type == "frozen" for c in snap.constraints)
    # provenance metadata
    assert snap.metadata["generated_by"] == "tools/context/builder.py"
    print("[OK] 确定性装配：accepted/proposed/frozen 正确分流，id 稳定排序")


def test_deterministic_rebuild_byte_identical() -> None:
    registry = (
        '{"schema_version":"1.0","id":"DEC-0001","decision":"d","status":"accepted","type":"architecture","title":"T"}\n'
    )
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        proj = _write(d, "project.yaml", _GOOD_YAML)
        reg = _write(d, "registry.jsonl", registry)
        out = d / "context" / "cognition.json"

        s1 = build_snapshot(proj, reg, generated_at="2026-06-24T00:00:00+00:00")
        write_snapshot(s1, out)
        first = out.read_bytes()

        s2 = build_snapshot(proj, reg, generated_at="2026-06-24T00:00:00+00:00")
        write_snapshot(s2, out)
        second = out.read_bytes()
    assert first == second, "同输入 + 固定 generated_at 必须逐字节一致（幂等可 diff）"
    print("[OK] 确定性重建：同输入逐字节一致")


def test_repo_cognition_matches_builder() -> None:
    out = _REPO / DEFAULT_OUT
    assert out.exists(), "仓库应已生成 cognition.json"
    on_disk = CognitionSnapshot.from_json(out.read_text(encoding="utf-8"))
    # 用磁盘上的 generated_at 现算，排除时间戳差异后应完全一致（派生未手改/未漂移）
    fresh = build_snapshot(
        _REPO / DEFAULT_PROJECT, _REPO / DEFAULT_REGISTRY, generated_at=on_disk.generated_at
    )
    assert fresh.to_dict() == on_disk.to_dict(), "cognition.json 与现算结果不一致：派生漂移或被手改"
    print(f"[OK] 仓库 cognition.json 与 builder 现算一致（decisions={len(on_disk.decisions)}）")


def test_no_llm_or_yaml_parse_deps() -> None:
    import ast

    import tools.context.builder as mod

    with open(mod.__file__, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    allowed_roots = {
        "argparse", "json", "sys", "pathlib", "__future__", "tools",
    }
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    forbidden = {"openai", "anthropic", "numpy", "faiss", "chromadb",
                 "langchain", "sentence_transformers", "pydantic", "yaml"}
    assert not (imported & forbidden), f"builder 禁止重依赖/LLM/YAML解析：{imported & forbidden}"
    assert imported <= allowed_roots, f"出现未预期依赖：{imported - allowed_roots}"
    print("[OK] 边界：不接 LLM/embedding/RAG，不 import yaml（仅 stdlib + 本层 schema/decisions）")


def main() -> None:
    test_snapshot_roundtrip()
    test_yaml_reader_supported_structure()
    test_yaml_reader_fail_loud()
    test_deterministic_assembly()
    test_deterministic_rebuild_byte_identical()
    test_repo_cognition_matches_builder()
    test_no_llm_or_yaml_parse_deps()
    print("\nCognition Builder 测试全部通过 ✅")


if __name__ == "__main__":
    main()
