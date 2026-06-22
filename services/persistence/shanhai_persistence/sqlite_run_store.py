"""SqliteRunStore — 基于 SQLite 的运行记录存储（见 ADR 0009）。

Local-first 默认后端：标准库 `sqlite3`，零外部依赖、可落盘、可查询。
依赖 agent-runtime 的 RunStore 抽象，与 PostgresRunStore 复用同一逻辑模型
（agent_runs + agent_steps），仅做 SQLite 方言适配（TEXT 存 JSON、AUTOINCREMENT、? 占位符）。
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from shanhai_agent_runtime import RunRecord, RunResult, RunStore
from shanhai_agent_runtime.types import AgentStatus, Step, StepType

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS agent_runs (
    id          TEXT PRIMARY KEY,
    agent       TEXT NOT NULL,
    status      TEXT NOT NULL,
    output      TEXT,
    error       TEXT,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS agent_steps (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id       TEXT NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    step_index   INTEGER NOT NULL,
    type         TEXT NOT NULL,
    content      TEXT,
    tool         TEXT,
    tool_args    TEXT,
    tool_result  TEXT
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_agent ON agent_runs (agent, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_steps_run ON agent_steps (run_id, step_index);
"""


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _loads(value: str | None) -> Any:
    return json.loads(value) if value else None


class SqliteRunStore(RunStore):
    """把 RunResult 落库到 SQLite。path=":memory:" 时为进程内库。"""

    def __init__(self, path: str = ".shanhai/runs.db") -> None:
        self._path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_schema(self) -> None:
        """幂等建表。首跑即自建库表，无需外部服务。"""
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)

    def save_run(self, run: RunResult) -> str:
        run_id = uuid.uuid4().hex
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO agent_runs (id, agent, status, output, error) "
                "VALUES (?, ?, ?, ?, ?)",
                (run_id, run.agent, run.status.value, _dumps(run.output), run.error),
            )
            conn.executemany(
                "INSERT INTO agent_steps "
                "(run_id, step_index, type, content, tool, tool_args, tool_result) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        run_id,
                        step.index,
                        step.type.value,
                        step.content,
                        step.tool,
                        _dumps(step.tool_args),
                        _dumps(step.tool_result),
                    )
                    for step in run.steps
                ],
            )
        return run_id

    def get_run(self, run_id: str) -> RunRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, agent, status, output, error, created_at "
                "FROM agent_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
            if row is None:
                return None
            step_rows = conn.execute(
                "SELECT step_index, type, content, tool, tool_args, tool_result "
                "FROM agent_steps WHERE run_id = ? ORDER BY step_index",
                (run_id,),
            ).fetchall()
        steps = [self._row_to_step(r) for r in step_rows]
        return self._row_to_record(row, steps)

    def list_runs(self, agent: str | None = None, limit: int = 50) -> list[RunRecord]:
        with self._connect() as conn:
            if agent is None:
                rows = conn.execute(
                    "SELECT id FROM agent_runs ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id FROM agent_runs WHERE agent = ? "
                    "ORDER BY created_at DESC LIMIT ?",
                    (agent, limit),
                ).fetchall()
            ids = [r[0] for r in rows]
        return [rec for rid in ids if (rec := self.get_run(rid)) is not None]

    @staticmethod
    def _row_to_step(row: Any) -> Step:
        step_index, type_, content, tool, tool_args, tool_result = row
        return Step(
            index=step_index,
            type=StepType(type_),
            content=content or "",
            tool=tool,
            tool_args=_loads(tool_args) or {},
            tool_result=_loads(tool_result),
        )

    @staticmethod
    def _row_to_record(row: Any, steps: list[Step]) -> RunRecord:
        run_id, agent, status, output, error, created_at = row
        return RunRecord(
            run_id=run_id,
            result=RunResult(
                agent=agent,
                status=AgentStatus(status),
                output=_loads(output),
                steps=steps,
                error=error,
            ),
            created_at=created_at,
        )
