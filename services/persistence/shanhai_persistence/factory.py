"""RunStore 装配工厂（见 ADR 0009）。

local-first 默认：按环境变量选择运行记录存储后端，默认 SQLite 落盘，
无需任何外部服务。存储选择权属于应用装配层，agent-runtime 仍只依赖 RunStore 抽象。

环境变量：
- SHANHAI_RUN_STORE: sqlite(默认) / memory / postgres
- SHANHAI_SQLITE_PATH: sqlite 路径，默认 ./.shanhai/runs.db
- SHANHAI_PG_DSN: postgres DSN（仅 postgres 后端需要）
"""

from __future__ import annotations

import os

from shanhai_agent_runtime import InMemoryRunStore, RunStore

DEFAULT_SQLITE_PATH = ".shanhai/runs.db"


def default_run_store() -> RunStore:
    """按环境变量装配 RunStore；默认 local-first（SQLite 落盘）。"""
    backend = os.environ.get("SHANHAI_RUN_STORE", "sqlite").lower()

    if backend == "memory":
        return InMemoryRunStore()

    if backend == "postgres":
        dsn = os.environ.get("SHANHAI_PG_DSN")
        if not dsn:
            raise ValueError(
                "SHANHAI_RUN_STORE=postgres 需要 SHANHAI_PG_DSN 指定连接串"
            )
        from shanhai_persistence.postgres_run_store import PostgresRunStore

        return PostgresRunStore(dsn)

    if backend == "sqlite":
        from shanhai_persistence.sqlite_run_store import SqliteRunStore

        return SqliteRunStore(os.environ.get("SHANHAI_SQLITE_PATH", DEFAULT_SQLITE_PATH))

    raise ValueError(f"未知的 SHANHAI_RUN_STORE 后端: {backend!r}")
