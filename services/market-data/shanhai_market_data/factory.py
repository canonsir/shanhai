"""Runtime factories for market data MVP."""

from __future__ import annotations

import os

from shanhai_market_data.postgres_store import PostgresMarketKnowledgeStore
from shanhai_market_data.store import InMemoryMarketKnowledgeStore
from shanhai_market_data.tushare import TushareProvider


def default_market_store() -> InMemoryMarketKnowledgeStore:
    backend = os.getenv("SHANHAI_MARKET_STORE", "memory").lower()
    if backend == "memory":
        return InMemoryMarketKnowledgeStore()
    if backend == "postgres":
        return PostgresMarketKnowledgeStore()
    raise ValueError(f"Unknown SHANHAI_MARKET_STORE backend: {backend!r}")


def default_tushare_provider() -> TushareProvider:
    return TushareProvider()
