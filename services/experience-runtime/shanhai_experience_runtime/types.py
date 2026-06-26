"""Experience Runtime PR-4.1 类型契约。

本模块只定义 Experience Runtime contract layer 的不可变值对象：
query / candidate view / selection / projection result。它不读取 Artifact，
不访问 Memory，不调用 AgentRuntime，也不承载学习权重。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _FrozenModel(BaseModel):
    """不可变契约基类：未知字段拒绝，构造后不可回写。"""

    model_config = ConfigDict(frozen=True, extra="forbid")


class ArtifactRef(_FrozenModel):
    """Artifact 的运行期引用，不是 Artifact 实体或内容 dump。"""

    artifact_id: str
    artifact_type: str | None = None


class Metadata(_FrozenModel):
    """Projection 可携带的只读元信息。"""

    entries: tuple[tuple[str, str], ...] = ()


class Summary(_FrozenModel):
    """运行期可消费摘要，不承载完整规则 / 原始文档。"""

    text: str = ""


class DecisionHint(_FrozenModel):
    """给运行期的决策提示，不是 Agent instruction 或 prompt。"""

    text: str = ""


class ExperienceQuery(_FrozenModel):
    """经验查询语境：来自 RuntimeContext 的任务 / 意图 / 约束 / 环境信号。"""

    task_type: str | None = None
    intent: str | None = None
    constraints: tuple[str, ...] = ()
    environment: tuple[tuple[str, str], ...] = ()


class ExperienceCandidateView(_FrozenModel):
    """Provider 返回的只读候选视图；只含引用和摘要，不含 Artifact 内容。"""

    candidate_id: str
    artifact_ref: ArtifactRef
    summary: Summary = Field(default_factory=Summary)
    metadata: Metadata = Field(default_factory=Metadata)


class ExperienceSelection(_FrozenModel):
    """Selector 的 per-run 输出；不包含学习权重 / Memory / Artifact 内容。"""

    candidate_id: str
    artifact_ref: ArtifactRef
    relevance_score: float | None = None
    selection_reason: str | None = None


class ExperienceProjectionResult(_FrozenModel):
    """Projection 输出：可映射到 RuntimeContext.experience_context 的引用形态。"""

    experience_refs: tuple[ArtifactRef, ...] = ()
    selection_reason: str | None = None
    selection_score: float | None = None
    metadata: Metadata = Field(default_factory=Metadata)
    summary: Summary = Field(default_factory=Summary)
    decision_hint: DecisionHint = Field(default_factory=DecisionHint)
