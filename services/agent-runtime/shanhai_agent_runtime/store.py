"""运行记录存储抽象（见 ADR 0008）。

RunStore 把「运行过程」沉淀为可追溯、可复盘的数据，供 evaluation 与经验学习使用。
agent-runtime 只依赖此抽象，不依赖任何数据库驱动，保持模块独立；
具体 DB 实现（PostgresRunStore）置于独立持久化层。
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel, Field

from shanhai_agent_runtime.types import RunResult


class RunRecord(BaseModel):
    """一条持久化的运行记录：run_id + RunResult 快照 + 落库时间。"""

    run_id: str
    result: RunResult
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RunStore(ABC):
    """运行记录存储接口。"""

    @abstractmethod
    def save_run(self, run: RunResult) -> str:
        """持久化一次运行，返回 run_id。"""
        raise NotImplementedError

    @abstractmethod
    def get_run(self, run_id: str) -> RunRecord | None:
        """按 run_id 读取记录；不存在返回 None。"""
        raise NotImplementedError

    @abstractmethod
    def list_runs(self, agent: str | None = None, limit: int = 50) -> list[RunRecord]:
        """按时间倒序列出记录；agent 非空时按 agent 过滤。"""
        raise NotImplementedError


class InMemoryRunStore(RunStore):
    """进程内默认实现，零外部依赖。用于测试与本机无 DB 场景。"""

    def __init__(self) -> None:
        self._records: dict[str, RunRecord] = {}

    def save_run(self, run: RunResult) -> str:
        run_id = uuid.uuid4().hex
        self._records[run_id] = RunRecord(run_id=run_id, result=run)
        return run_id

    def get_run(self, run_id: str) -> RunRecord | None:
        return self._records.get(run_id)

    def list_runs(self, agent: str | None = None, limit: int = 50) -> list[RunRecord]:
        records = sorted(
            self._records.values(), key=lambda r: r.created_at, reverse=True
        )
        if agent is not None:
            records = [r for r in records if r.result.agent == agent]
        return records[:limit]
