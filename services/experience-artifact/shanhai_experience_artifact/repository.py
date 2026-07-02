"""Artifact 存储抽象（见 ADR 0018 D4，Stage 2-c MVP）。

ArtifactService 依赖 ArtifactRepository 抽象，而非具体实现——冻结这条边界，
使未来 memory → database → vector → graph 的迁移不污染 Service（对齐 ADR 0017 修正 1）。

Stage 2-c 只实现 InMemoryArtifactRepository；DB / Vector / Graph 后端属后续阶段
（均在 ADR 0018 §4 冻结清单内，本期禁止）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from shanhai_experience_artifact.models import ArtifactStatus, ArtifactType, ExperienceArtifact


class ArtifactRepository(ABC):
    """经验资产存储接口。Service 仅依赖此抽象。"""

    @abstractmethod
    def add(self, artifact: ExperienceArtifact) -> str:
        """新增一条资产，返回 artifact_id。重复 id 应拒绝。"""
        raise NotImplementedError

    @abstractmethod
    def get(self, artifact_id: str) -> ExperienceArtifact | None:
        """按 id 读取资产；不存在返回 None。"""
        raise NotImplementedError

    @abstractmethod
    def list(
        self,
        status: ArtifactStatus | None = None,
        artifact_type: ArtifactType | None = None,
        limit: int = 50,
    ) -> list[ExperienceArtifact]:
        """按 created_at 倒序列出资产，支持状态/类型过滤。"""
        raise NotImplementedError


class InMemoryArtifactRepository(ArtifactRepository):
    """进程内默认实现，零外部依赖。用于测试与本机无 DB 场景（非持久化）。"""

    def __init__(self) -> None:
        self._artifacts: dict[str, ExperienceArtifact] = {}

    def add(self, artifact: ExperienceArtifact) -> str:
        if artifact.artifact_id in self._artifacts:
            raise ValueError(f"资产已存在：{artifact.artifact_id}")
        self._artifacts[artifact.artifact_id] = artifact
        return artifact.artifact_id

    def get(self, artifact_id: str) -> ExperienceArtifact | None:
        return self._artifacts.get(artifact_id)

    def list(
        self,
        status: ArtifactStatus | None = None,
        artifact_type: ArtifactType | None = None,
        limit: int = 50,
    ) -> list[ExperienceArtifact]:
        items = sorted(
            self._artifacts.values(), key=lambda a: a.created_at, reverse=True
        )
        if status is not None:
            items = [a for a in items if a.status == status]
        if artifact_type is not None:
            items = [a for a in items if a.artifact_type == artifact_type]
        return items[:limit]
