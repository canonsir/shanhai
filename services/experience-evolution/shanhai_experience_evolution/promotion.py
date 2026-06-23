"""候选经验晋升闸门接口（见 ADR 0017 修正 5，Stage 2-b）。

PromotionGate 判断一条已验证的 Candidate 是否可晋升，输出 PromotionDecision。
Stage 2-b 只提供 NoopPromotionGate 占位实现，且 Artifact 尚不存在。

特别冻结（ADR 0017 修正 5 / Commit 3 Review）：PromotionDecision 只含
approved / reason / candidate_id / validation_snapshot_ref，**禁止**出现 artifact /
artifact_content / summary / knowledge_document / embedding 等字段——
Candidate → Artifact → Knowledge Projection 属 ADR 0016 Stage 3+。

边界：Gate 只产决策，不创建 Artifact、不调用 CandidateService（不编排）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel

from shanhai_experience_evolution.candidate import ExperienceCandidate


class PromotionDecision(BaseModel):
    """晋升决策（ADR 0017 修正 5：无任何 artifact 相关字段）。

    - approved：是否批准晋升（Validated → Promoted 的依据）。
    - reason：人/Agent 可读的决策理由。
    - candidate_id：被决策的候选标识。
    - validation_snapshot_ref：所依据的验证快照引用（不内嵌证据内容）。
    """

    approved: bool
    reason: str = ""
    candidate_id: str
    validation_snapshot_ref: str | None = None


class PromotionGate(ABC):
    """晋升闸门接口：已验证 Candidate（+验证状态+血缘）→ PromotionDecision。"""

    name: str = "promotion_gate"

    @abstractmethod
    def evaluate(self, candidate: ExperienceCandidate) -> PromotionDecision:
        raise NotImplementedError


class NoopPromotionGate(PromotionGate):
    """占位实现（Stage 2-b）：一律不批准晋升。

    用于打通接口与装配；真实晋升规则（置信阈值 / 一致性 / 人审）属后续阶段。
    """

    name = "noop"

    def evaluate(self, candidate: ExperienceCandidate) -> PromotionDecision:
        return PromotionDecision(
            approved=False,
            reason="noop promotion gate：未实施晋升规则（Stage 2-b 占位）",
            candidate_id=candidate.candidate_id,
        )
