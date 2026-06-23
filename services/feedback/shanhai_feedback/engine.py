"""FeedbackEngine — 反馈闭环编排（见 ADR 0013 §2/§5 + Addendum，Stage 1）。

把一条评估结果跑通：规则归因 → 候选去重/合并 → 阈值晋升 → 经 ExperienceStore.append
落为 type=lesson 的 ExperienceEvent（事实基座，ADR 0014）。

写经验路径（决策①）：Feedback 是离线系统编排层（非 Agent），经 ExperienceStore.append
（service → service）写经验，不经 MemoryService/MemoryTool；MemoryService EXPERIENCE 对
Agent 保持只读。读侧反哺仍由 ADR 0012 MemoryTool 承担，与本模块解耦。

引用而非复制：lesson 事件经 refs 引用 run_id / evaluation_ref，payload 只存提炼结论与
精简 signals，绝不内嵌原始 metrics。依赖单向：feedback → evaluation + experience + agent-runtime。
"""

from __future__ import annotations

from shanhai_agent_runtime.store import RunRecord
from shanhai_evaluation.models import EvaluationResult
from shanhai_experience import (
    ExperienceEvent,
    ExperienceEventType,
    ExperienceRefs,
    ExperienceStore,
    resolve_episode_id,
)

from shanhai_feedback.models import ExperienceCandidate
from shanhai_feedback.registry import CandidateRegistry
from shanhai_feedback.rules import FailurePatternRule, FeedbackRule


class FeedbackEngine:
    """评估结果 → 候选 → 去重/晋升 → lesson 事件。离线/按需运行。"""

    def __init__(
        self,
        store: ExperienceStore,
        rules: list[FeedbackRule] | None = None,
        registry: CandidateRegistry | None = None,
    ) -> None:
        self._store = store
        self._rules: list[FeedbackRule] = rules or [FailurePatternRule()]
        self._registry = registry or CandidateRegistry()
        # 已晋升的 dedup_key，避免同一模式重复落 lesson 事件
        self._promoted: set[str] = set()

    def process(
        self,
        evaluation: EvaluationResult,
        run: RunRecord | None = None,
    ) -> list[ExperienceEvent]:
        """处理一条评估结果，返回本次新晋升落库的 lesson 事件。"""
        promoted: list[ExperienceEvent] = []
        for rule in self._rules:
            for derived in rule.derive(evaluation, run):
                merged = self._registry.add(derived)
                if (
                    merged.dedup_key not in self._promoted
                    and self._registry.is_promotable(merged)
                ):
                    event = self._promote(merged)
                    self._promoted.add(merged.dedup_key)
                    promoted.append(event)
        return promoted

    def _promote(self, candidate: ExperienceCandidate) -> ExperienceEvent:
        """把达标候选晋升为 type=lesson 的不可变经验事件并 append。"""
        trigger_run = candidate.source_run_ids[-1] if candidate.source_run_ids else ""
        evaluation_ref = (
            f"{trigger_run}:{candidate.source_evaluator}"
            if trigger_run and candidate.source_evaluator
            else None
        )
        event = ExperienceEvent(
            episode_id=resolve_episode_id(None, trigger_run or candidate.dedup_key),
            agent=candidate.agent,
            type=ExperienceEventType.LESSON,
            payload={
                "kind": candidate.kind.value,
                "summary": candidate.summary,
                "occurrences": candidate.occurrences,
                "signals": candidate.signals,
                "source_run_ids": list(candidate.source_run_ids),
                "dedup_key": candidate.dedup_key,
            },
            refs=ExperienceRefs(
                run_id=trigger_run or None,
                evaluation_ref=evaluation_ref,
            ),
        )
        self._store.append(event)
        return event
