"""PostgresRunStore — 基于 PostgreSQL 的运行记录存储（见 ADR 0008）。

依赖 agent-runtime 的 RunStore 抽象。DB 驱动（psycopg）惰性导入：
未安装时构造即报错，但不影响导入本模块，使无 DB 环境（本机无 Docker）仍可静态检查。
数据模型：agent_runs（运行汇总）+ agent_steps（逐步记录）。
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from shanhai_agent_runtime import RunRecord, RunResult, RunStore
from shanhai_agent_runtime.types import AgentStatus, Step, StepType

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS agent_runs (
    id          UUID PRIMARY KEY,
    agent       TEXT NOT NULL,
    status      TEXT NOT NULL,
    output      JSONB,
    error       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent_steps (
    id           BIGSERIAL PRIMARY KEY,
    run_id       UUID NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    step_index   INTEGER NOT NULL,
    type         TEXT NOT NULL,
    content      TEXT,
    tool         TEXT,
    tool_args    JSONB,
    tool_result  JSONB
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_agent ON agent_runs (agent, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_steps_run ON agent_steps (run_id, step_index);
"""


def _import_psycopg():
    try:
        import psycopg  # type: ignore
    except ImportError as exc:  # pragma: no cover - 取决于运行环境
        raise RuntimeError(
            "PostgresRunStore 需要 psycopg：pip install 'shanhai-persistence[postgres]'"
        ) from exc
    return psycopg


class PostgresRunStore(RunStore):
    """把 RunResult 落库到 PostgreSQL。"""

    def __init__(self, dsn: str) -> None:
        self._psycopg = _import_psycopg()
        self._dsn = dsn

    def _connect(self):
        return self._psycopg.connect(self._dsn)

    def init_schema(self) -> None:
        """幂等建表。"""
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
            conn.commit()

    def save_run(self, run: RunResult) -> str:
        run_id = uuid.uuid4().hex
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO agent_runs (id, agent, status, output, error) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    run_id,
                    run.agent,
                    run.status.value,
                    json.dumps(run.output, ensure_ascii=False, default=str),
                    run.error,
                ),
            )
            for step in run.steps:
                cur.execute(
                    "INSERT INTO agent_steps "
                    "(run_id, step_index, type, content, tool, tool_args, tool_result) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (
                        run_id,
                        step.index,
                        step.type.value,
                        step.content,
                        step.tool,
                        json.dumps(step.tool_args, ensure_ascii=False, default=str),
                        json.dumps(step.tool_result, ensure_ascii=False, default=str),
                    ),
                )
            conn.commit()
        return run_id

    def get_run(self, run_id: str) -> RunRecord | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id, agent, status, output, error, created_at "
                "FROM agent_runs WHERE id = %s",
                (run_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            cur.execute(
                "SELECT step_index, type, content, tool, tool_args, tool_result "
                "FROM agent_steps WHERE run_id = %s ORDER BY step_index",
                (run_id,),
            )
            steps = [self._row_to_step(r) for r in cur.fetchall()]
        return self._row_to_record(row, steps)

    def list_runs(self, agent: str | None = None, limit: int = 50) -> list[RunRecord]:
        with self._connect() as conn, conn.cursor() as cur:
            if agent is None:
                cur.execute(
                    "SELECT id FROM agent_runs ORDER BY created_at DESC LIMIT %s",
                    (limit,),
                )
            else:
                cur.execute(
                    "SELECT id FROM agent_runs WHERE agent = %s "
                    "ORDER BY created_at DESC LIMIT %s",
                    (agent, limit),
                )
            ids = [r[0] for r in cur.fetchall()]
        return [rec for rid in ids if (rec := self.get_run(str(rid))) is not None]

    @staticmethod
    def _row_to_step(row: Any) -> Step:
        step_index, type_, content, tool, tool_args, tool_result = row
        return Step(
            index=step_index,
            type=StepType(type_),
            content=content or "",
            tool=tool,
            tool_args=tool_args or {},
            tool_result=tool_result,
        )

    @staticmethod
    def _row_to_record(row: Any, steps: list[Step]) -> RunRecord:
        run_id, agent, status, output, error, created_at = row
        return RunRecord(
            run_id=str(run_id),
            result=RunResult(
                agent=agent,
                status=AgentStatus(status),
                output=output,
                steps=steps,
                error=error,
            ),
            created_at=created_at,
        )
