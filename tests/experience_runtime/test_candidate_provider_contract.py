"""ExperienceCandidateProvider 契约测试（PR-4.1）。

运行：PYTHONPATH=. .venv/bin/python -m tests.experience_runtime.test_candidate_provider_contract
覆盖：
  Case 1 package public contracts 可 import
  Case 2 provider interface 返回只读 candidate refs
  Case 3 candidate view schema 禁止 Artifact dump / Memory / learning 字段
"""

from __future__ import annotations

from pydantic import ValidationError

from shanhai_experience_runtime import (
    ArtifactRef,
    ExperienceCandidateProvider,
    ExperienceCandidateView,
    ExperienceQuery,
    Metadata,
    Summary,
)


class _StaticProvider:
    def list_candidates(
        self,
        query: ExperienceQuery,
    ) -> tuple[ExperienceCandidateView, ...]:
        return (
            ExperienceCandidateView(
                candidate_id="candidate_001",
                artifact_ref=ArtifactRef(artifact_id="artifact_001"),
                summary=Summary(text=f"task={query.task_type}"),
                metadata=Metadata(entries=(("source", "contract"),)),
            ),
        )


def test_case1_public_contract_imports() -> None:
    assert ExperienceCandidateProvider is not None
    assert ExperienceQuery(task_type="research").task_type == "research"
    print("[OK] Case 1：ExperienceCandidateProvider public contract 可 import")


def test_case2_provider_returns_read_only_candidate_refs() -> None:
    provider: ExperienceCandidateProvider = _StaticProvider()
    candidates = provider.list_candidates(ExperienceQuery(task_type="research"))

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.candidate_id == "candidate_001"
    assert candidate.artifact_ref.artifact_id == "artifact_001"
    assert candidate.summary.text == "task=research"
    assert not hasattr(candidate, "artifact_content")
    print("[OK] Case 2：provider 返回 candidate refs，不返回 Artifact content")


def test_case3_candidate_view_rejects_forbidden_fields() -> None:
    for field in (
        "artifact_content",
        "raw_document",
        "embedding",
        "memory_state",
        "learning_weight",
    ):
        try:
            ExperienceCandidateView(
                candidate_id="candidate_001",
                artifact_ref=ArtifactRef(artifact_id="artifact_001"),
                **{field: "forbidden"},
            )
            raise AssertionError(f"ExperienceCandidateView 不应接受 {field}")
        except ValidationError:
            pass
    print("[OK] Case 3：candidate view 禁止 Artifact dump / Memory / learning 字段")


def main() -> None:
    test_case1_public_contract_imports()
    test_case2_provider_returns_read_only_candidate_refs()
    test_case3_candidate_view_rejects_forbidden_fields()
    print("\nExperienceCandidateProvider 契约测试全部通过 ✅")


if __name__ == "__main__":
    main()
