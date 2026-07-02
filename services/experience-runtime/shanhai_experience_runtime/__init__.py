"""ShanHai Experience Runtime — 经验读侧运行时契约层（PR-4.1）。

定位：
    Experience Runtime = experience access + selection + projection。

PR-4.1 只冻结 public contracts / types / dependency boundary，不实现真实
provider、selector algorithm、projection runtime，也不接 RuntimeKernel / AgentRunner /
Memory / Evolution / E2E。
"""

from shanhai_experience_runtime.candidate_provider import ExperienceCandidateProvider
from shanhai_experience_runtime.projection import ExperienceProjection
from shanhai_experience_runtime.selector import ExperienceSelector
from shanhai_experience_runtime.types import (
    ArtifactRef,
    DecisionHint,
    ExperienceCandidateView,
    ExperienceProjectionResult,
    ExperienceQuery,
    ExperienceSelection,
    Metadata,
    Summary,
)

__all__ = [
    "ExperienceCandidateProvider",
    "ExperienceSelector",
    "ExperienceProjection",
    "ArtifactRef",
    "Metadata",
    "Summary",
    "DecisionHint",
    "ExperienceQuery",
    "ExperienceCandidateView",
    "ExperienceSelection",
    "ExperienceProjectionResult",
]
