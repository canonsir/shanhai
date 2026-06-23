"""经验事件存储抽象（见 ADR 0014 §6，Stage 1：Event Infrastructure）。

ExperienceStore 是 append-only 的经验事件日志：只追加、可读、可过滤，
不提供 update/delete（不可变铁律）。沿用 RunStore 范式：抽象 + 进程内默认实现，
local-first、零外部依赖即可运行；可选 DB 实现留待后续置于 services/persistence。

Stage 1 范围：append / get / list(filter)。不含 Episode 投影、语义经验、向量检索。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from shanhai_experience.models import ExperienceEvent, ExperienceEventType


class ExperienceStore(ABC):
    """经验事件存储接口（append-only）。"""

    @abstractmethod
    def append(self, event: ExperienceEvent) -> str:
        """追加一条经验事件，返回 event_id。只追加，不提供 update/delete。"""
        raise NotImplementedError

    @abstractmethod
    def get(self, event_id: str) -> ExperienceEvent | None:
        """按 event_id 读取事件；不存在返回 None。"""
        raise NotImplementedError

    @abstractmethod
    def list(
        self,
        agent: str | None = None,
        type: ExperienceEventType | None = None,
        entity_id: str | None = None,
        since: datetime | None = None,
        limit: int = 50,
        episode_id: str | None = None,
        parent_event_id: str | None = None,
    ) -> list[ExperienceEvent]:
        """按 occurred_at 倒序列出事件；字段过滤，无向量检索。

        - agent：按产生事件的 Agent 过滤
        - type：按事件类型过滤
        - entity_id：命中 refs.entity_ids 的事件（关于某知识实体）
        - since：只取 occurred_at >= since 的事件
        - limit：返回上限
        - episode_id：按情景聚合（跨 run 研究主题，ADR 0015）
        - parent_event_id：命中 refs.parent_event_id 的事件（如某 decision 的 outcome 回填）
        """
        raise NotImplementedError


class InMemoryExperienceStore(ExperienceStore):
    """进程内默认实现，零外部依赖。用于测试与本机无 DB 场景。"""

    def __init__(self) -> None:
        self._events: dict[str, ExperienceEvent] = {}

    def append(self, event: ExperienceEvent) -> str:
        if event.event_id in self._events:
            raise ValueError(f"事件已存在，不可覆盖（append-only）：{event.event_id}")
        self._events[event.event_id] = event
        return event.event_id

    def get(self, event_id: str) -> ExperienceEvent | None:
        return self._events.get(event_id)

    def list(
        self,
        agent: str | None = None,
        type: ExperienceEventType | None = None,
        entity_id: str | None = None,
        since: datetime | None = None,
        limit: int = 50,
        episode_id: str | None = None,
        parent_event_id: str | None = None,
    ) -> list[ExperienceEvent]:
        events = sorted(
            self._events.values(), key=lambda e: e.occurred_at, reverse=True
        )
        if agent is not None:
            events = [e for e in events if e.agent == agent]
        if type is not None:
            events = [e for e in events if e.type == type]
        if entity_id is not None:
            events = [e for e in events if entity_id in e.refs.entity_ids]
        if since is not None:
            events = [e for e in events if e.occurred_at >= since]
        if episode_id is not None:
            events = [e for e in events if e.episode_id == episode_id]
        if parent_event_id is not None:
            events = [e for e in events if e.refs.parent_event_id == parent_event_id]
        return events[:limit]
