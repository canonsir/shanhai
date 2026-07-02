"""Runtime factories for market data MVP.

Storage selection is an application-assembly concern; the business layer keeps
depending only on the ``MarketKnowledgeRepository`` abstraction. Local-first per
ADR 0009: default to durable SQLite (survives restart, no Docker). InMemory
stays as the reference-semantics adapter; Postgres is opt-in.

Env:
- SHANHAI_MARKET_STORE: sqlite (default) / memory / postgres
- SHANHAI_MARKET_SQLITE_PATH: sqlite path, default .shanhai/market.db
- SHANHAI_MARKET_PG_DSN: postgres DSN (postgres backend only)
"""

from __future__ import annotations

import os

from shanhai_market_data.domain.repository import MarketKnowledgeRepository
from shanhai_market_data.postgres_store import PostgresMarketKnowledgeStore
from shanhai_market_data.store import InMemoryMarketKnowledgeRepository
from shanhai_market_data.tushare import TushareProvider

DEFAULT_MARKET_SQLITE_PATH = ".shanhai/market.db"


def default_market_store() -> MarketKnowledgeRepository:
    backend = os.getenv("SHANHAI_MARKET_STORE", "sqlite").lower()
    if backend == "memory":
        return InMemoryMarketKnowledgeRepository()
    if backend == "sqlite":
        from shanhai_market_data.sqlite_repository import (
            SQLiteMarketKnowledgeRepository,
        )

        path = os.getenv("SHANHAI_MARKET_SQLITE_PATH", DEFAULT_MARKET_SQLITE_PATH)
        return SQLiteMarketKnowledgeRepository(path=path)
    if backend == "postgres":
        return PostgresMarketKnowledgeStore()
    raise ValueError(f"Unknown SHANHAI_MARKET_STORE backend: {backend!r}")


def default_tushare_provider() -> TushareProvider:
    return TushareProvider()
