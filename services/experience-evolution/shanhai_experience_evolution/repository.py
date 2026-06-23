"""候选经验存储抽象（见 ADR 0017 修正 1，Stage 2-b）。

CandidateService 依赖 CandidateRepository 抽象，而非具体实现——冻结这条边界，
使未来 memory → database → vector → graph 的迁移不污染 Service（ADR 0017 修正 1）。

Stage 2-b 只实现 InMemoryCandidateRepository；PersistentCandidateRepository 属后续阶段
（Candidate persistence 仍在冻结清单内）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from shanhai_experience_evolution.candidate import ExperienceCandidate
from shanhai_experience_evolution.models import CandidateSource, CandidateStatus


class CandidateRepository(ABC):
    """候选经验存储接口。Service 仅依赖此抽象。"""

    @abstractmethod
    def add(self, candidate: ExperienceCandidate) -> str:
        """新增一条候选，返回 candidate_id。重复 id 应拒绝。"""
        raise NotImplementedError

    @abstractmethod
    def get(self, candidate_id: str) -> ExperienceCandidate | None:
        """按 id 读取候选；不存在返回 None。"""
        raise NotImplementedError

    @abstractmethod
    def save(self, candidate: ExperienceCandidate) -> None:
        """保存对已存在候选的状态更新（由 Service 在转移/验证后调用）。"""
        raise NotImplementedError

    @abstractmethod
    def list(
        self,
        status: CandidateStatus | None = None,
        source: CandidateSource | None = None,
        limit: int = 50,
    ) -> list[ExperienceCandidate]:
        """按 created_at 倒序列出候选，支持状态/来源过滤。"""
        raise NotImplementedError


class InMemoryCandidateRepository(CandidateRepository):
    """进程内默认实现，零外部依赖。用于测试与本机无 DB 场景（非持久化）。"""

    def __init__(self) -> None:
        self._candidates: dict[str, ExperienceCandidate] = {}

    def add(self, candidate: ExperienceCandidate) -> str:
        if candidate.candidate_id in self._candidates:
            raise ValueError(f"候选已存在：{candidate.candidate_id}")
        self._candidates[candidate.candidate_id] = candidate
        return candidate.candidate_id

    def get(self, candidate_id: str) -> ExperienceCandidate | None:
        return self._candidates.get(candidate_id)

    def save(self, candidate: ExperienceCandidate) -> None:
        if candidate.candidate_id not in self._candidates:
            raise ValueError(f"候选不存在，无法保存：{candidate.candidate_id}")
        self._candidates[candidate.candidate_id] = candidate

    def list(
        self,
        status: CandidateStatus | None = None,
        source: CandidateSource | None = None,
        limit: int = 50,
    ) -> list[ExperienceCandidate]:
        items = sorted(
            self._candidates.values(), key=lambda c: c.created_at, reverse=True
        )
        if status is not None:
            items = [c for c in items if c.validation_status == status]
        if source is not None:
            items = [c for c in items if c.source == source]
        return items[:limit]
