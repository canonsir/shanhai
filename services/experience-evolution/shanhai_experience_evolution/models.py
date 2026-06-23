"""Experience Evolution 值对象与枚举（见 ADR 0016 §2 / ADR 0017，Stage 2-b）。

本模块是 Evolution Layer 的数据契约基座：只定义不可变语义的值对象与枚举，
不含行为、不含存储、不依赖 experience / feedback（依赖方向见 ADR 0017 §4）。

核心区分（ADR 0017 Decision C）：
- source_refs ——「为什么产生」这条候选（来源事实/候选/外部引用）。
- evidence_refs ——「为什么相信」这条候选（验证证据：outcome / evaluation）。
二者不是同一个概念，故分立。
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class CandidateStatus(str, Enum):
    """候选经验生命周期状态（ADR 0017 Decision D）。

    Rejected 不是终态：context 改变后旧经验可被 Reactivated 或归档为 Archived，
    保留知识血缘而非删除。Promoted 由 PromotionGate 写入（Validated → Promoted）。
    """

    CREATED = "created"
    EVALUATING = "evaluating"
    VALIDATED = "validated"
    REJECTED = "rejected"
    PROMOTED = "promoted"
    ARCHIVED = "archived"
    REACTIVATED = "reactivated"


class CandidateSource(str, Enum):
    """候选经验来源（ADR 0017 Decision B：Feedback 只是其中之一）。"""

    FEEDBACK = "feedback"
    OUTCOME = "outcome"
    MINING = "mining"
    HUMAN = "human"
    AGENT_DISCOVERY = "agent_discovery"


class Actor(str, Enum):
    """生命周期操作者（ADR 0017 Decision F / Stage 2-b 权限模型）。

    不同 actor 拥有不同的状态转移权限，统一经 CandidateService.transition() 校验，
    禁止任何调用方直接赋值 candidate.validation_status。
    """

    # 候选生产者（feedback / outcome / mining / human / agent_discovery）：只能 create
    PRODUCER = "producer"
    # 验证者：Created → Evaluating → Validated / Rejected
    VALIDATOR = "validator"
    # 晋升闸门：Validated → Promoted
    PROMOTION_GATE = "promotion_gate"
    # 系统：Rejected → Reactivated / Archived，Reactivated → Evaluating
    SYSTEM = "system"


class Hypothesis(BaseModel):
    """候选经验承载的可验证假设（ADR 0017 Decision C）。

    Candidate 的本质是「可能成立的规律」，而非一句话总结；用结构化字段表达
    「在什么情境、满足什么条件、采取什么动作、期望什么结果」，以便后续验证与演化。
    """

    context: str = ""
    condition: str = ""
    action: str = ""
    expected_outcome: str = ""


class SourceRefs(BaseModel):
    """来源引用——「为什么产生」（ADR 0014 §4 引用而非复制）。

    只持标识符：原始事实归 ExperienceStore / 上游候选所有，不复制内容。
    """

    event_ids: list[str] = Field(default_factory=list)
    candidate_ids: list[str] = Field(default_factory=list)
    external_refs: list[str] = Field(default_factory=list)


class EvidenceRefs(BaseModel):
    """验证证据引用——「为什么相信」（ADR 0017 Decision C/E）。

    与 source_refs 区分：证据来自验证过程（outcome 复核 / evaluation），
    同样只持引用，不内嵌度量。
    """

    event_ids: list[str] = Field(default_factory=list)
    outcome_refs: list[str] = Field(default_factory=list)
    evaluation_refs: list[str] = Field(default_factory=list)


class ValidationStats(BaseModel):
    """验证统计（ADR 0017 Decision E：validation != occurrence count）。

    occurrence 只证明「问题常发生」；真实学习靠 decision → outcome → validation。
    本结构记录验证窗口内的成败与一致性，由 CandidateService.apply_validation 更新。
    """

    success_count: int = 0
    failure_count: int = 0
    window: int = 0
    consistency: float = 0.0


class Lineage(BaseModel):
    """知识血缘（ADR 0017 Decision D：失效不删除，保留血缘）。

    记录候选从何而来：来源标识、上游候选、派生事实，以及演化备注。
    """

    source: str = ""
    parent_candidate_id: str | None = None
    derived_from_event_ids: list[str] = Field(default_factory=list)
    notes: str = ""
