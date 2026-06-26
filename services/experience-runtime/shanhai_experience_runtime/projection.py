"""ExperienceProjection public contract（PR-4.1）。

Projection 只把 ExperienceSelection 转成 RuntimeContext v1 可承载的经验引用视图；
不得扩展 RuntimeContext schema，不得复制 Artifact content。
"""

from __future__ import annotations

from typing import Protocol

from shanhai_experience_runtime.types import (
    ExperienceProjectionResult,
    ExperienceSelection,
)


class ExperienceProjection(Protocol):
    """将 selection 投影成运行期可消费表示。"""

    def project(self, selection: ExperienceSelection) -> ExperienceProjectionResult:
        """返回 RuntimeContext-compatible projection；不得持久化或回写。"""
        ...
