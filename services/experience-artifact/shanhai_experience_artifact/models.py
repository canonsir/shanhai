"""Experience Artifact 值对象、枚举与实体（见 ADR 0018，Stage 2-c MVP）。

本模块是 Artifact 承载层的数据契约基座：只定义不可变语义的值对象、枚举与实体，
不含行为、不含存储、不依赖 evolution / feedback / experience（依赖方向见 ADR 0018 §5）。

定位（ADR 0018 §2）：经验资产化（experience as a stable asset），而非经验智能化。
ExperienceArtifact 是 PromotionDecision(approved=true) 之后的稳定资产形态——
对 Candidate「相变固化」，confidence 取晋升快照、status 本期无流转（ADR 0018 D2/D3）。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ArtifactType(str, Enum):
    """Artifact 类型（ADR 0018 D1）。

    MVP 仅 EXPERIENCE_RULE（被验证的条件化经验规则，与 Candidate.Hypothesis 同构）。
    Skill / Prompt / Policy / KnowledgeUnit 等留作后续扩展位，本期不实现。
    """

    EXPERIENCE_RULE = "experience_rule"


class ArtifactStatus(str, Enum):
    """Artifact 状态（ADR 0018 D2）。

    MVP 仅 ACTIVE；ARCHIVED 为预留枚举值，本期无状态流转逻辑
    （archive / supersede / 再验证回退属后续阶段，见 ADR 0018 §6）。
    """

    ACTIVE = "active"
    ARCHIVED = "archived"


class ArtifactRule(BaseModel):
    """经验规则能力核心（ADR 0018 D2）。

    与 Candidate.Hypothesis 的 context/condition/action 同构，承载「在什么情境、
    满足什么条件、采取什么动作」。预期结果 expected_outcome 提升至 Artifact 顶层
    （供未来 Evaluation 判断资产价值），不放在此处。
    """

    context: str = ""
    condition: str = ""
    action: str = ""


class Provenance(BaseModel):
    """来源引用（ADR 0018 D2：引用而非复制，MVP 仅 source_type + source_id）。

    本期只记录「资产从哪条晋升决策而来」，不提前建
    Artifact → Candidate → Event → Feedback 完整 lineage（留 Projection Layer）。
    """

    source_type: str = "promotion_decision"
    source_id: str = ""


class ExperienceArtifact(BaseModel):
    """一条稳定经验资产（Artifact 承载层核心实体，ADR 0018 D2）。

    由被验证晋升的 Candidate「相变固化」而来：rule + expected_outcome 承载语义，
    confidence 为晋升时刻快照（不随 Candidate 后续变化漂移），provenance 持来源引用。
    name 仅人类可读派生视图，非语义载体 / 非匹配依据。
    """

    artifact_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    artifact_type: ArtifactType = ArtifactType.EXPERIENCE_RULE
    status: ArtifactStatus = ArtifactStatus.ACTIVE
    name: str = ""
    rule: ArtifactRule = Field(default_factory=ArtifactRule)
    expected_outcome: str = ""
    confidence: float = 0.0
    provenance: Provenance = Field(default_factory=Provenance)
    created_at: datetime = Field(default_factory=datetime.utcnow)
