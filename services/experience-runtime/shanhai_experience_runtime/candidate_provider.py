"""ExperienceCandidateProvider public contract（PR-4.1）。

Provider 是 Experience Access Port，不是具体存储实现。PR-4.1 只冻结
interface，不实现 ArtifactReader / Vector / Memory / DB adapter。
"""

from __future__ import annotations

from typing import Protocol

from shanhai_experience_runtime.types import ExperienceCandidateView, ExperienceQuery


class ExperienceCandidateProvider(Protocol):
    """按查询语境返回只读候选经验视图。"""

    def list_candidates(
        self,
        query: ExperienceQuery,
    ) -> tuple[ExperienceCandidateView, ...]:
        """返回候选视图；不得修改 Artifact / Candidate / Memory。"""
        ...
