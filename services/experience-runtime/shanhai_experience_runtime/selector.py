"""ExperienceSelector public contract（PR-4.1）。

Selector 只做 per-run selection；Selector 不学习，Evolution 学习。本模块不实现
真实 ranking / model-based selection。
"""

from __future__ import annotations

from typing import Protocol

from shanhai_experience_runtime.types import (
    ExperienceCandidateView,
    ExperienceQuery,
    ExperienceSelection,
)


class ExperienceSelector(Protocol):
    """从候选视图中选择一次运行要使用的经验引用。"""

    def select(
        self,
        candidates: tuple[ExperienceCandidateView, ...],
        query: ExperienceQuery,
    ) -> ExperienceSelection:
        """返回 per-run selection；不得学习 / 回写 / 访问 Memory。"""
        ...
