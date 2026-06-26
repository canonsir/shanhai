"""PostgreSQL-backed Market Knowledge Store.

The dependency on psycopg is lazy. Local tests can use the in-memory store
without installing a PostgreSQL driver. Production runtime should provide
`SHANHAI_MARKET_PG_DSN`.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any

from shanhai_market_data.models import CompanyIntelligence, QuoteSnapshot
from shanhai_market_data.store import InMemoryMarketKnowledgeStore

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS market_company_intelligence (
    ts_code      TEXT PRIMARY KEY,
    company_id   TEXT NOT NULL,
    company_name TEXT NOT NULL,
    payload      JSONB NOT NULL,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_market_company_name
    ON market_company_intelligence (company_name);
"""


ConnectionFactory = Callable[[], Any]


class PostgresMarketKnowledgeStore(InMemoryMarketKnowledgeStore):
    """PostgreSQL store with an in-process assembly cache.

    The MVP writes the same read model exposed by CompanyIntelligenceAPI into
    Postgres. Raw/fact/entity table normalization remains a later slice.
    """

    def __init__(
        self,
        dsn: str | None = None,
        *,
        connection_factory: ConnectionFactory | None = None,
    ) -> None:
        super().__init__()
        self._dsn = dsn if dsn is not None else os.getenv("SHANHAI_MARKET_PG_DSN", "")
        self._connection_factory = connection_factory
        if self._connection_factory is None and not self._dsn:
            raise RuntimeError("PostgresMarketKnowledgeStore requires SHANHAI_MARKET_PG_DSN")
        self.init_schema()

    def init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(SCHEMA_SQL)

    def upsert_company_bundle(self, **kwargs: Any) -> None:
        super().upsert_company_bundle(**kwargs)
        security = kwargs["security"]
        item = self.get_company_intelligence_by_ts_code(security.ts_code)
        if item is not None:
            self._persist(item)

    def upsert_quote(self, quote: QuoteSnapshot) -> None:
        super().upsert_quote(quote)
        item = next(
            (
                candidate
                for candidate in self.list_company_intelligence(limit=10000)
                if candidate.security.security_id == quote.security_id
            ),
            None,
        )
        if item is not None:
            self._persist(item)

    def get_company_intelligence_by_ts_code(self, ts_code: str) -> CompanyIntelligence | None:
        cached = super().get_company_intelligence_by_ts_code(ts_code)
        if cached is not None:
            return cached
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM market_company_intelligence WHERE ts_code = %s",
                (ts_code,),
            ).fetchone()
        if row is None:
            return None
        payload = row[0]
        if isinstance(payload, str):
            payload = json.loads(payload)
        return CompanyIntelligence.model_validate(payload)

    def list_company_intelligence(self, limit: int = 50) -> tuple[CompanyIntelligence, ...]:
        cached = super().list_company_intelligence(limit=limit)
        if cached:
            return cached
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM market_company_intelligence "
                "ORDER BY company_name ASC LIMIT %s",
                (limit,),
            ).fetchall()
        return tuple(
            CompanyIntelligence.model_validate(json.loads(row[0]) if isinstance(row[0], str) else row[0])
            for row in rows
        )

    def search_company(self, text: str, limit: int = 50) -> tuple[CompanyIntelligence, ...]:
        cached = super().search_company(text=text, limit=limit)
        if cached:
            return cached
        pattern = f"%{text}%"
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM market_company_intelligence "
                "WHERE company_name ILIKE %s OR ts_code ILIKE %s "
                "ORDER BY company_name ASC LIMIT %s",
                (pattern, pattern, limit),
            ).fetchall()
        return tuple(
            CompanyIntelligence.model_validate(json.loads(row[0]) if isinstance(row[0], str) else row[0])
            for row in rows
        )

    def _persist(self, item: CompanyIntelligence) -> None:
        payload = item.model_dump(mode="json")
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO market_company_intelligence "
                "(ts_code, company_id, company_name, payload, updated_at) "
                "VALUES (%s, %s, %s, %s, now()) "
                "ON CONFLICT (ts_code) DO UPDATE SET "
                "company_id = EXCLUDED.company_id, "
                "company_name = EXCLUDED.company_name, "
                "payload = EXCLUDED.payload, "
                "updated_at = now()",
                (
                    item.security.ts_code,
                    item.company.company_id,
                    item.company.name,
                    json.dumps(payload, ensure_ascii=False),
                ),
            )

    def _connect(self) -> Any:
        if self._connection_factory is not None:
            return self._connection_factory()
        try:
            import psycopg  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "PostgresMarketKnowledgeStore requires psycopg; install the postgres extra"
            ) from exc
        return psycopg.connect(self._dsn)
