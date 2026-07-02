"""经验资产服务（见 ADR 0018 D4，Stage 2-c MVP）。

ArtifactService 是 Artifact 承载层的极简 facade：依赖注入的 ArtifactRepository
（不绑定具体实现），只承担资产的「写入 / 读取 / 列举」。

职责边界（ADR 0018 D4，严格收敛）：
    允许：create / get / list
    禁止：generate / retrieve / embed / project / inject —— 那是 Builder（evolution 侧）
          与未来 Projection / Retrieval Layer 的职责；ArtifactService 不参与
          promotion / validation / lifecycle / builder。Artifact 承载层不是智能层。
"""

from __future__ import annotations

from shanhai_experience_artifact.models import (
    ArtifactStatus,
    ArtifactType,
    ExperienceArtifact,
)
from shanhai_experience_artifact.repository import ArtifactRepository


class ArtifactService:
    """经验资产管理（repository 注入；仅 create/get/list，不参与晋升/验证/生命周期）。"""

    def __init__(self, repository: ArtifactRepository) -> None:
        self._repo = repository

    def create(self, artifact: ExperienceArtifact) -> ExperienceArtifact:
        """登记一条已构建好的经验资产。

        Artifact 由 evolution 侧 ArtifactBuilder 构建（Commit 6），Service 只负责承载，
        不在此生成内容（不 generate / 不 summarize / 不 embed）。
        """
        self._repo.add(artifact)
        return artifact

    def get(self, artifact_id: str) -> ExperienceArtifact | None:
        """按 id 读取资产；不存在返回 None。"""
        return self._repo.get(artifact_id)

    def list(
        self,
        status: ArtifactStatus | None = None,
        artifact_type: ArtifactType | None = None,
        limit: int = 50,
    ) -> list[ExperienceArtifact]:
        """列出资产，支持状态/类型过滤。"""
        return self._repo.list(status=status, artifact_type=artifact_type, limit=limit)
