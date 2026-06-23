"""候选经验生命周期服务（见 ADR 0017 修正 1/3，Stage 2-b）。

CandidateService 是 Evolution Layer 的生命周期 facade：依赖注入的 CandidateRepository
（不绑定具体实现，修正 1），统一承担「状态机权限校验 + 转移落地」（修正 3）。
任何调用方禁止直接赋值 candidate.validation_status——必须经 transition()/apply_validation()。

职责边界（Review Gate Commit 2：不做大管家）：
    允许：create / transition / apply_validation / get / list
    禁止：generate / evaluate / summarize / discover —— 那是 Producer / Validator /
          Discovery Layer 的职责，不归本服务。Evolution Layer 不是 Agent。
"""

from __future__ import annotations

from datetime import datetime

from shanhai_experience_evolution.candidate import (
    ExperienceCandidate,
    is_allowed_transition,
)
from shanhai_experience_evolution.models import (
    Actor,
    CandidateSource,
    CandidateStatus,
    Lineage,
    ValidationVerdict,
)
from shanhai_experience_evolution.proposals import CandidateProposal
from shanhai_experience_evolution.repository import CandidateRepository


class TransitionError(RuntimeError):
    """非法状态转移（actor 无权或转移不在合法表内）。"""


class CandidateService:
    """候选经验生命周期管理（repository 注入，actor 权限收敛于此）。"""

    def __init__(self, repository: CandidateRepository) -> None:
        self._repo = repository

    def create(self, proposal: CandidateProposal) -> ExperienceCandidate:
        """Producer 入口：由 Proposal 创建一条 Created 候选（ADR 0017 修正 2/3）。

        Producer 只能创建（产生 Created），不能直接产出更高阶状态。
        """
        lineage = proposal.lineage or Lineage(source=proposal.source.value)
        candidate = ExperienceCandidate(
            source=proposal.source,
            hypothesis=proposal.hypothesis,
            source_refs=proposal.source_refs,
            lineage=lineage,
            validation_status=CandidateStatus.CREATED,
        )
        self._repo.add(candidate)
        return candidate

    def transition(
        self,
        candidate_id: str,
        to_status: CandidateStatus,
        actor: Actor,
    ) -> ExperienceCandidate:
        """按 actor 权限执行状态转移；非法转移抛 TransitionError。

        唯一的状态变更通道：先查合法转移表（from, to, actor），再落库。
        """
        candidate = self._require(candidate_id)
        from_status = candidate.validation_status
        if not is_allowed_transition(from_status, to_status, actor):
            raise TransitionError(
                f"非法转移：{from_status.value} -> {to_status.value}（actor={actor.value}）"
            )
        candidate.validation_status = to_status
        candidate.updated_at = datetime.utcnow()
        self._repo.save(candidate)
        return candidate

    def apply_validation(
        self,
        candidate_id: str,
        verdict: ValidationVerdict,
    ) -> ExperienceCandidate:
        """Validator 裁决落地：Evaluating → Validated / Rejected（ADR 0017 修正 4）。

        仅接受处于 Evaluating 的候选；按 verdict.validated 选择目标态，
        回写 confidence / validation_stats / evidence_refs，再经合法转移落库。
        证据回写与状态转移同属一次原子操作，避免裁决散落调用方。
        """
        candidate = self._require(candidate_id)
        if candidate.validation_status != CandidateStatus.EVALUATING:
            raise TransitionError(
                f"apply_validation 仅接受 Evaluating 候选，当前 {candidate.validation_status.value}"
            )
        to_status = (
            CandidateStatus.VALIDATED if verdict.validated else CandidateStatus.REJECTED
        )
        if not is_allowed_transition(
            candidate.validation_status, to_status, Actor.VALIDATOR
        ):
            raise TransitionError(
                f"非法验证转移：{candidate.validation_status.value} -> {to_status.value}"
            )
        candidate.confidence = verdict.confidence
        candidate.validation_stats = verdict.validation_stats
        candidate.evidence_refs = verdict.evidence_refs
        candidate.validation_status = to_status
        candidate.updated_at = datetime.utcnow()
        self._repo.save(candidate)
        return candidate

    def get(self, candidate_id: str) -> ExperienceCandidate | None:
        """按 id 读取候选；不存在返回 None。"""
        return self._repo.get(candidate_id)

    def list(
        self,
        status: CandidateStatus | None = None,
        source: CandidateSource | None = None,
        limit: int = 50,
    ) -> list[ExperienceCandidate]:
        """列出候选，支持状态/来源过滤。"""
        return self._repo.list(status=status, source=source, limit=limit)

    def _require(self, candidate_id: str) -> ExperienceCandidate:
        candidate = self._repo.get(candidate_id)
        if candidate is None:
            raise KeyError(f"候选不存在：{candidate_id}")
        return candidate
