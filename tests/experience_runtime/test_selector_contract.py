"""ExperienceSelector 契约测试（PR-4.1）。

运行：PYTHONPATH=. .venv/bin/python -m tests.experience_runtime.test_selector_contract
覆盖：
  Case 1 selector interface 输出 ExperienceSelection
  Case 2 ExperienceSelection schema 只含冻结字段
  Case 3 禁止 learning / feedback / Memory / prompt 字段
"""

from __future__ import annotations

from pydantic import ValidationError

from shanhai_experience_runtime import (
    ArtifactRef,
    ExperienceCandidateView,
    ExperienceQuery,
    ExperienceSelection,
    ExperienceSelector,
)


class _DeterministicSelector:
    def select(
        self,
        candidates: tuple[ExperienceCandidateView, ...],
        query: ExperienceQuery,
    ) -> ExperienceSelection:
        del query
        candidate = candidates[0]
        return ExperienceSelection(
            candidate_id=candidate.candidate_id,
            artifact_ref=candidate.artifact_ref,
            relevance_score=0.9,
            selection_reason="first deterministic candidate",
        )


def _candidate() -> ExperienceCandidateView:
    return ExperienceCandidateView(
        candidate_id="candidate_001",
        artifact_ref=ArtifactRef(artifact_id="artifact_001"),
    )


def test_case1_selector_returns_experience_selection() -> None:
    selector: ExperienceSelector = _DeterministicSelector()

    selection = selector.select((_candidate(),), ExperienceQuery(task_type="research"))

    assert isinstance(selection, ExperienceSelection)
    assert selection.candidate_id == "candidate_001"
    assert selection.artifact_ref.artifact_id == "artifact_001"
    assert selection.relevance_score == 0.9
    print("[OK] Case 1：selector interface 输出 ExperienceSelection")


def test_case2_selection_schema_is_frozen_contract() -> None:
    fields = set(ExperienceSelection.model_fields.keys())

    assert fields == {
        "candidate_id",
        "artifact_ref",
        "relevance_score",
        "selection_reason",
    }
    print("[OK] Case 2：ExperienceSelection 只暴露冻结字段")


def test_case3_selection_rejects_forbidden_fields() -> None:
    for field in (
        "artifact_content",
        "embedding",
        "memory_state",
        "learning_weight",
        "feedback_score",
        "model_prompt",
        "agent_instruction",
    ):
        try:
            ExperienceSelection(
                candidate_id="candidate_001",
                artifact_ref=ArtifactRef(artifact_id="artifact_001"),
                **{field: "forbidden"},
            )
            raise AssertionError(f"ExperienceSelection 不应接受 {field}")
        except ValidationError:
            pass
    print("[OK] Case 3：ExperienceSelection 禁止 dump / learning / Memory / prompt 字段")


def main() -> None:
    test_case1_selector_returns_experience_selection()
    test_case2_selection_schema_is_frozen_contract()
    test_case3_selection_rejects_forbidden_fields()
    print("\nExperienceSelector 契约测试全部通过 ✅")


if __name__ == "__main__":
    main()
