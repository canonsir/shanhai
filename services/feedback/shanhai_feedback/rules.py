"""Feedback 归因规则（见 ADR 0013 §4，Stage 1）。

规则输入一条 EvaluationResult（+ 可选只读 RunRecord 作上下文），输出候选经验列表。
Stage 1 仅 FailurePatternRule：确定性、零外部依赖、不调用模型——失败的运行按 error_type
归为一类失败模式候选。

边界：规则只读消费评估产物与运行记录，不直连 DB、不调用模型、不修改任何上游。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from shanhai_agent_runtime.store import RunRecord
from shanhai_evaluation.models import EvaluationResult

from shanhai_feedback.models import CandidateKind, ExperienceCandidate


class FeedbackRule(ABC):
    """归因规则接口：评估结果 → 候选经验。"""

    name: str = "feedback_rule"

    @abstractmethod
    def derive(
        self,
        evaluation: EvaluationResult,
        run: RunRecord | None = None,
    ) -> list[ExperienceCandidate]:
        raise NotImplementedError


class FailurePatternRule(FeedbackRule):
    """失败归因（ADR 0013 §4 规则 1）。

    当 EvaluationResult.passed 为 False 时，按 error_type 生成一条失败模式候选；
    dedup_key = agent + "failure" + error_type，使同类失败在 Registry 中合并计数。
    """

    name = "failure_pattern"

    def derive(
        self,
        evaluation: EvaluationResult,
        run: RunRecord | None = None,
    ) -> list[ExperienceCandidate]:
        if evaluation.passed is not False:
            return []

        agent = evaluation.detail.get("agent") or "unknown"
        error_type = evaluation.value("error_type") or "UnknownError"

        candidate = ExperienceCandidate(
            kind=CandidateKind.FAILURE_PATTERN,
            agent=agent,
            summary=f"{agent} 反复以 {error_type} 失败，下次运行需规避该失败模式",
            dedup_key=f"{agent}|failure|{error_type}",
            source_run_ids=[evaluation.run_id] if evaluation.run_id else [],
            source_evaluator=evaluation.evaluator,
            signals={"passed": False, "error_type": error_type},
        )
        return [candidate]
