"""ShanHai Experience Artifact — 候选经验晋升后的稳定资产承载层（见 ADR 0018）。

Stage 2-c MVP：补齐 ADR 0017 在 PromotionDecision 处留空的 Artifact 承载层，
把瞬时的「是否晋升」决策沉淀为可管理 / 可追踪 / 可消费的稳定 ExperienceArtifact。

依赖方向（ADR 0018 §5，单向不成环）：
    feedback ──► experience-evolution ──► experience-artifact ──► experience（只读）
本包仅依赖 pydantic；不依赖 evolution / feedback / experience（artifact 不反向耦合）。

不在范围（ADR 0018 §4 冻结）：ArtifactBuilder（属 evolution 侧 Commit 6）、ArtifactReader
（Commit 7）、Vector / Graph / Retrieval / Memory 写入 / Agent 注入 / Prompt·Skill 自动生成 /
Artifact 持久化后端 / 状态流转 / Candidate 反向血缘。
"""

from shanhai_experience_artifact.models import (
    ArtifactRule,
    ArtifactStatus,
    ArtifactType,
    ExperienceArtifact,
    Provenance,
)
from shanhai_experience_artifact.repository import (
    ArtifactRepository,
    InMemoryArtifactRepository,
)
from shanhai_experience_artifact.service import ArtifactService

__all__ = [
    "ArtifactType",
    "ArtifactStatus",
    "ArtifactRule",
    "Provenance",
    "ExperienceArtifact",
    "ArtifactRepository",
    "InMemoryArtifactRepository",
    "ArtifactService",
]
