"""Promotion → Artifact Bridge 回归测试（见 ADR 0018 D4，Stage 2-c Commit 6）。

运行：PYTHONPATH=. .venv/bin/python -m tests.test_artifact_bridge
覆盖：
  Case 1 字段映射：approved=True 时 (Candidate + PromotionDecision) → ExperienceArtifact，
         hypothesis → rule / expected_outcome 提顶层 / confidence 快照 / provenance 来源引用
  Case 2 未晋升拒绝：approved=False → ValueError（未晋升不产资产）
  Case 3 错配拒绝：decision.candidate_id 与 candidate 不一致 → ValueError
  Case 4 纯转换边界：build 不改 Candidate（单向 Candidate → Artifact）、不持久化、
         ArtifactBuilder 不持有 / 不调用 ArtifactService / Repository（生产与存储分离）
  Final  依赖方向：experience-evolution → experience-artifact 允许；
         experience-artifact 不反向 import evolution / feedback / experience
"""

from __future__ import annotations

import ast
import pathlib

from shanhai_experience_artifact import (
    ArtifactStatus,
    ArtifactType,
    ExperienceArtifact,
)

from shanhai_experience_evolution import (
    ArtifactBuilder,
    CandidateSource,
    ExperienceCandidate,
    Hypothesis,
    PromotionDecision,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _candidate() -> ExperienceCandidate:
    return ExperienceCandidate(
        source=CandidateSource.FEEDBACK,
        hypothesis=Hypothesis(
            context="research agent 在高频调用外部 API 时",
            condition="连续 3 次 TimeoutError",
            action="降低并发并指数退避重试",
            expected_outcome="超时率下降、任务成功率回升",
        ),
        confidence=0.87,
    )


def _approved(candidate: ExperienceCandidate) -> PromotionDecision:
    return PromotionDecision(
        approved=True,
        reason="一致性 0.87，达到晋升阈值",
        candidate_id=candidate.candidate_id,
        validation_snapshot_ref="snap_001",
    )


def test_case1_field_mapping() -> None:
    candidate = _candidate()
    decision = _approved(candidate)

    artifact = ArtifactBuilder().build(candidate, decision)

    assert isinstance(artifact, ExperienceArtifact)
    # 默认资产类型与状态
    assert artifact.artifact_type == ArtifactType.EXPERIENCE_RULE
    assert artifact.status == ArtifactStatus.ACTIVE
    # hypothesis → ArtifactRule 映射
    assert artifact.rule.context == candidate.hypothesis.context
    assert artifact.rule.condition == candidate.hypothesis.condition
    assert artifact.rule.action == candidate.hypothesis.action
    # expected_outcome 提到 Artifact 顶层（不在 rule 内）
    assert artifact.expected_outcome == candidate.hypothesis.expected_outcome
    assert not hasattr(artifact.rule, "expected_outcome")
    # confidence 取晋升时刻快照
    assert artifact.confidence == 0.87
    # name 为派生视图（action 派生），非语义载体
    assert artifact.name == candidate.hypothesis.action
    # provenance 仅来源引用（source_type/source_id），无完整 lineage
    assert artifact.provenance.source_type == "promotion_decision"
    assert artifact.provenance.source_id == candidate.candidate_id
    assert set(type(artifact.provenance).model_fields.keys()) == {"source_type", "source_id"}
    print("[OK] Case 1：approved=True → 字段映射正确（rule/expected_outcome/confidence/provenance）")


def test_case2_not_approved_rejected() -> None:
    candidate = _candidate()
    decision = PromotionDecision(approved=False, candidate_id=candidate.candidate_id)
    try:
        ArtifactBuilder().build(candidate, decision)
        raise AssertionError("approved=False 不应能构建 Artifact")
    except ValueError:
        pass
    print("[OK] Case 2：approved=False → ValueError（未晋升不产资产）")


def test_case3_candidate_id_mismatch_rejected() -> None:
    candidate = _candidate()
    decision = PromotionDecision(approved=True, candidate_id="other_candidate_id")
    try:
        ArtifactBuilder().build(candidate, decision)
        raise AssertionError("candidate_id 不一致不应能构建 Artifact")
    except ValueError:
        pass
    print("[OK] Case 3：candidate_id 不一致 → ValueError（防错配）")


def test_case4_pure_transform_boundary() -> None:
    candidate = _candidate()
    decision = _approved(candidate)
    before = candidate.model_dump()

    builder = ArtifactBuilder()
    builder.build(candidate, decision)

    # build 不改 Candidate（单向 Candidate → Artifact，不回写 lineage / status / confidence）
    assert candidate.model_dump() == before

    # 生产与存储分离：Builder 不持有 / 不依赖 ArtifactService 或 Repository
    public = {m for m in dir(builder) if not m.startswith("_")}
    assert public == {"build"}
    assert not any("service" in a.lower() or "repo" in a.lower() for a in vars(builder))
    # AST 校验：builder 源码不 import 也不调用任何存储构件（忽略 docstring 中的描述性提及）
    builder_path = (
        REPO_ROOT
        / "services/experience-evolution/shanhai_experience_evolution/artifact_builder.py"
    )
    tree = ast.parse(builder_path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    called: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(n.name for n in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.update(n.name for n in node.names)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                called.add(func.attr)
            elif isinstance(func, ast.Name):
                called.add(func.id)
    for forbidden in ("ArtifactService", "ArtifactRepository", "InMemoryArtifactRepository"):
        assert forbidden not in imported, f"builder 不应 import {forbidden}"
    for forbidden in ("create", "add", "save", "persist"):
        assert forbidden not in called, f"builder 不应调用存储方法 {forbidden}"
    print("[OK] Case 4：build 不改 Candidate + 不持久化 + 不调用 ArtifactService/Repository")


def _imports_of(pkg_dir: pathlib.Path) -> set[str]:
    modules: set[str] = set()
    for f in pkg_dir.glob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(n.name for n in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
    return modules


def test_final_dependency_direction() -> None:
    evo = _imports_of(
        REPO_ROOT / "services/experience-evolution/shanhai_experience_evolution"
    )
    art = _imports_of(
        REPO_ROOT / "services/experience-artifact/shanhai_experience_artifact"
    )
    # evolution → artifact 允许（Bridge 引用 artifact 契约）
    assert any(m.startswith("shanhai_experience_artifact") for m in evo), evo
    # artifact 不反向依赖 evolution / feedback / experience
    assert not any(m.startswith("shanhai_experience_evolution") for m in art), art
    assert not any(m.startswith("shanhai_feedback") for m in art), art
    assert not any(m == "shanhai_experience" or m.startswith("shanhai_experience.") for m in art), art
    print("[OK] Final：evolution→artifact 单向；artifact 不反向依赖 evolution/feedback/experience")


def main() -> None:
    test_case1_field_mapping()
    test_case2_not_approved_rejected()
    test_case3_candidate_id_mismatch_rejected()
    test_case4_pure_transform_boundary()
    test_final_dependency_direction()
    print("\nPromotion → Artifact Bridge 回归测试全部通过 ✅")


if __name__ == "__main__":
    main()
