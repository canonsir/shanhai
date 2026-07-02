"""ExperienceProjection 契约测试（PR-4.1）。

运行：PYTHONPATH=. .venv/bin/python -m tests.experience_runtime.test_projection_contract
覆盖：
  Case 1 projection interface 输出 ExperienceProjectionResult
  Case 2 projection result 与 RuntimeContext v1 experience_context 形态兼容
  Case 3 projection result 禁止 Artifact dump / Memory / runtime state
"""

from __future__ import annotations

from pydantic import ValidationError

from shanhai_experience_runtime import (
    ArtifactRef,
    DecisionHint,
    ExperienceProjection,
    ExperienceProjectionResult,
    ExperienceSelection,
    Metadata,
    Summary,
)
from shanhai_runtime_kernel import ExperienceContext, SelectedExperienceRef


class _ReferenceProjection:
    def project(self, selection: ExperienceSelection) -> ExperienceProjectionResult:
        return ExperienceProjectionResult(
            experience_refs=(selection.artifact_ref,),
            selection_reason=selection.selection_reason,
            selection_score=selection.relevance_score,
            metadata=Metadata(entries=(("projection", "contract"),)),
            summary=Summary(text="short summary"),
            decision_hint=DecisionHint(text="consider selected artifact ref"),
        )


def _selection() -> ExperienceSelection:
    return ExperienceSelection(
        candidate_id="candidate_001",
        artifact_ref=ArtifactRef(artifact_id="artifact_001"),
        relevance_score=0.88,
        selection_reason="relevant to task",
    )


def test_case1_projection_returns_projection_result() -> None:
    projection: ExperienceProjection = _ReferenceProjection()

    result = projection.project(_selection())

    assert isinstance(result, ExperienceProjectionResult)
    assert result.experience_refs[0].artifact_id == "artifact_001"
    assert result.selection_reason == "relevant to task"
    assert result.selection_score == 0.88
    print("[OK] Case 1：projection interface 输出 ExperienceProjectionResult")


def test_case2_projection_result_maps_to_runtime_context_v1() -> None:
    result = _ReferenceProjection().project(_selection())

    context = ExperienceContext(
        experience_refs=(
            SelectedExperienceRef(
                artifact_id=result.experience_refs[0].artifact_id,
                relevance=result.selection_score,
                reason=result.selection_reason,
            ),
        ),
        selection_reason=result.selection_reason,
        selection_score=result.selection_score,
    )

    assert context.experience_refs[0].artifact_id == "artifact_001"
    assert context.selection_reason == result.selection_reason
    assert context.selection_score == result.selection_score
    print("[OK] Case 2：projection result 可映射到 RuntimeContext v1 experience_context")


def test_case3_projection_result_rejects_forbidden_fields() -> None:
    for field in (
        "artifact_content",
        "full_rule",
        "knowledge_graph",
        "memory_snapshot",
        "runtime_state",
    ):
        try:
            ExperienceProjectionResult(
                experience_refs=(ArtifactRef(artifact_id="artifact_001"),),
                **{field: "forbidden"},
            )
            raise AssertionError(f"ExperienceProjectionResult 不应接受 {field}")
        except ValidationError:
            pass
    print("[OK] Case 3：projection result 禁止 Artifact dump / Memory / runtime state")


def main() -> None:
    test_case1_projection_returns_projection_result()
    test_case2_projection_result_maps_to_runtime_context_v1()
    test_case3_projection_result_rejects_forbidden_fields()
    print("\nExperienceProjection 契约测试全部通过 ✅")


if __name__ == "__main__":
    main()
