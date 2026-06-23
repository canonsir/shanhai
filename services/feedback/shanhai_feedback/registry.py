"""候选经验去重注册表（见 ADR 0013 §4，Stage 1）。

进程内 dedup_key → ExperienceCandidate 映射：相同 dedup_key 的候选**合并计数**而非重复存，
并累加来源 run_id 与 score。离线/按需运行，不持久化（Stage 1 本就如此）。

晋升阈值在此判定：occurrences 达到阈值的候选才可晋升为 lesson 事件，
避免一次性噪声（偶发失败）污染经验库。
"""

from __future__ import annotations

from shanhai_feedback.models import ExperienceCandidate


class CandidateRegistry:
    """候选去重/合并/计数 + 阈值晋升判定。"""

    def __init__(self, promote_threshold: int = 2) -> None:
        self._threshold = max(1, promote_threshold)
        self._candidates: dict[str, ExperienceCandidate] = {}

    def add(self, candidate: ExperienceCandidate) -> ExperienceCandidate:
        """登记候选；同 dedup_key 合并计数并返回合并后的对象。"""
        existing = self._candidates.get(candidate.dedup_key)
        if existing is None:
            self._candidates[candidate.dedup_key] = candidate
            return candidate

        existing.occurrences += candidate.occurrences
        existing.score = float(existing.occurrences)
        for run_id in candidate.source_run_ids:
            if run_id not in existing.source_run_ids:
                existing.source_run_ids.append(run_id)
        return existing

    def is_promotable(self, candidate: ExperienceCandidate) -> bool:
        """是否达到晋升阈值。"""
        return candidate.occurrences >= self._threshold

    def candidates(self) -> list[ExperienceCandidate]:
        """当前所有候选（合并后）。"""
        return list(self._candidates.values())
