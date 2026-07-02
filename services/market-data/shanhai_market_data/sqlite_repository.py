"""SQLite adapter for the Market Knowledge Store (M3.3 Phase 2).

``SQLiteMarketKnowledgeRepository`` is the durable, local-first adapter behind
the ``MarketKnowledgeRepository`` boundary (domain/repository.py). It realises
the frozen Option C schema — a single append-only ``knowledge_observation``
spine plus typed observation detail tables (financial / quote / announcement) —
without redesigning it. The business layer keeps depending only on the Protocol;
this module never leaks SQL into callers.

Prior art = RunStore (ADR 0008 / 0009): standard-library ``sqlite3``, idempotent
``init_schema()`` (``CREATE TABLE IF NOT EXISTS``), no Alembic / SQLAlchemy,
JSON columns for provenance. Two write semantics never mix: the four-layer
identity model is current-truth upsert (overwrite by surrogate PK); only
observations are append-only and idempotent on ``(logical_key, content_hash)``.

Two frozen invariants this adapter must keep true to stay behaviourally
identical to the in-memory adapter:

1. Quote convergence — the QUOTE ``MarketFact`` carried in a bundle and a
   ``upsert_quote`` snapshot share one ``logical_key`` AND one ``content_hash``,
   so they land on a single spine row. ``upsert_quote`` therefore re-derives the
   same fact via ``build_quote_fact`` and writes through the same spine path,
   then attaches the structured ``quote_observation`` detail.
2. Extension payload — ``subject_ref.label`` and domain leftover (a fact's
   ``attributes`` / an announcement's ``mentioned_entities``) ride the spine
   ``attributes`` JSON column and are rebuilt on read, so projected facts equal
   what the in-memory adapter returns.

Boundary (Phase 2 Step 1): this file only. No factory switch, no InMemory
deletion, no Postgres, no migration framework.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Any

from shanhai_market_data.fact_mapper import build_quote_fact
from shanhai_market_data.models import (
    AnnouncementFact,
    AnnouncementType,
    Board,
    Company,
    CompanyIntelligence,
    CompanyTimelineEvent,
    EntityLink,
    Exchange,
    FactAttribute,
    FactType,
    FinancialFact,
    Industry,
    ListedEntity,
    Listing,
    ListingStatus,
    MarketFact,
    QuoteSnapshot,
    Security,
    SecurityType,
    SourceRef,
    SubjectRef,
    TimeBasis,
)
from shanhai_market_data.timeline import build_company_timeline

SCHEMA_VERSION = 1

# Spine attributes JSON keys reserved for the extension payload (never a column).
_ATTR_SUBJECT_LABEL = "__subject_label__"
_ATTR_FACT_ATTRIBUTES = "__fact_attributes__"
_ATTR_MENTIONED_ENTITIES = "__mentioned_entities__"

SCHEMA_SQL = """
-- ── Identity (four-layer, surrogate PK, current-truth upsert) ───────────────
CREATE TABLE IF NOT EXISTS company (
    company_id   TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    aliases      TEXT,            -- json array
    region       TEXT,
    external_ids TEXT             -- json array
);

CREATE TABLE IF NOT EXISTS listed_entity (
    listed_entity_id TEXT PRIMARY KEY,
    company_id       TEXT NOT NULL REFERENCES company(company_id),
    disclosure_name  TEXT NOT NULL,
    source_ref       TEXT NOT NULL  -- json
);

CREATE TABLE IF NOT EXISTS security (
    security_id      TEXT PRIMARY KEY,
    listed_entity_id TEXT NOT NULL REFERENCES listed_entity(listed_entity_id),
    ts_code          TEXT NOT NULL,
    symbol           TEXT NOT NULL,
    name             TEXT NOT NULL,
    exchange         TEXT NOT NULL,
    security_type    TEXT NOT NULL,
    currency         TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_security_ts_code ON security (ts_code);
CREATE INDEX IF NOT EXISTS idx_security_listed_entity ON security (listed_entity_id);

CREATE TABLE IF NOT EXISTS listing (
    listing_id  TEXT PRIMARY KEY,
    security_id TEXT NOT NULL REFERENCES security(security_id),
    exchange    TEXT NOT NULL,
    board       TEXT NOT NULL,
    listed_at   TEXT,
    delisted_at TEXT,
    status      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_listing_security ON listing (security_id);

CREATE TABLE IF NOT EXISTS industry (
    industry_id TEXT PRIMARY KEY,
    taxonomy    TEXT NOT NULL,
    name        TEXT NOT NULL,
    code        TEXT,
    level       INTEGER
);

CREATE TABLE IF NOT EXISTS company_industry (
    company_id  TEXT NOT NULL REFERENCES company(company_id),
    industry_id TEXT NOT NULL REFERENCES industry(industry_id),
    PRIMARY KEY (company_id, industry_id)
);

-- ── Knowledge Observation Spine (append-only cognition timeline) ────────────
CREATE TABLE IF NOT EXISTS knowledge_observation (
    observation_id   INTEGER PRIMARY KEY AUTOINCREMENT,  -- immutable surrogate
    logical_key      TEXT NOT NULL,                      -- = old fact_id (lineage)
    content_hash     TEXT NOT NULL,                      -- idempotency
    fact_type        TEXT NOT NULL,
    subject_type     TEXT NOT NULL,
    subject_id       TEXT NOT NULL,
    predicate        TEXT,
    object_type      TEXT,
    object_value     TEXT,
    occurred_at      TEXT,
    published_at     TEXT,
    captured_at      TEXT NOT NULL,
    confidence       REAL NOT NULL DEFAULT 1.0,
    source_ref       TEXT,                               -- json
    attributes       TEXT,                               -- json: extension payload
    schema_version   TEXT,
    created_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_observation_identity
    ON knowledge_observation (logical_key, content_hash);
CREATE INDEX IF NOT EXISTS idx_observation_logical_captured
    ON knowledge_observation (logical_key, captured_at);
CREATE INDEX IF NOT EXISTS idx_observation_subject_type
    ON knowledge_observation (subject_id, fact_type);

-- ── Typed observation detail (1:1 on observation_id) ────────────────────────
CREATE TABLE IF NOT EXISTS financial_observation (
    observation_id INTEGER PRIMARY KEY
        REFERENCES knowledge_observation(observation_id) ON DELETE CASCADE,
    metric_name   TEXT NOT NULL,
    report_period TEXT NOT NULL,
    report_type   TEXT,
    metric_value  REAL,
    unit          TEXT,
    currency      TEXT,
    yoy           REAL,
    qoq           REAL,
    restated      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS quote_observation (
    observation_id INTEGER PRIMARY KEY
        REFERENCES knowledge_observation(observation_id) ON DELETE CASCADE,
    security_id    TEXT NOT NULL,
    quote_id       TEXT NOT NULL,
    trade_date     TEXT NOT NULL,
    open           REAL,
    high           REAL,
    low            REAL,
    close          REAL,
    previous_close REAL,
    volume         REAL,
    amount         REAL
);
CREATE INDEX IF NOT EXISTS idx_quote_observation_security
    ON quote_observation (security_id, trade_date);

CREATE TABLE IF NOT EXISTS announcement_observation (
    observation_id    INTEGER PRIMARY KEY
        REFERENCES knowledge_observation(observation_id) ON DELETE CASCADE,
    announcement_id   TEXT NOT NULL,
    announcement_type TEXT,
    title             TEXT,
    publish_date      TEXT,
    document_url      TEXT,
    document_hash     TEXT,
    extracted_summary TEXT
);

-- ── Schema version (no Alembic) ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
"""


def _dumps(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=str)


def _loads(value: str | None) -> Any:
    return json.loads(value) if value else None


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


class SQLiteMarketKnowledgeRepository:
    """Durable SQLite adapter implementing ``MarketKnowledgeRepository``.

    ``path=":memory:"`` keeps a single shared connection alive for the process
    (a fresh connection to ``:memory:`` would see an empty database). Disk-backed
    paths reconnect per call like RunStore.
    """

    def __init__(self, path: str = ".shanhai/market.db") -> None:
        self._path = path
        self._lock = threading.Lock()
        self._memory_conn: sqlite3.Connection | None = None
        if path == ":memory:":
            self._memory_conn = sqlite3.connect(path, check_same_thread=False)
            self._memory_conn.execute("PRAGMA foreign_keys = ON")
        else:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    # --- connection / schema --------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        if self._memory_conn is not None:
            return self._memory_conn
        conn = sqlite3.connect(self._path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_schema(self) -> None:
        """Idempotent table creation + schema version stamp."""
        with self._lock:
            conn = self._connect()
            try:
                conn.executescript(SCHEMA_SQL)
                conn.execute(
                    "INSERT OR IGNORE INTO schema_version (version) VALUES (?)",
                    (SCHEMA_VERSION,),
                )
                conn.commit()
            finally:
                self._close(conn)

    def _close(self, conn: sqlite3.Connection) -> None:
        if conn is not self._memory_conn:
            conn.close()

    # --- write (ingestion) ----------------------------------------------------

    def upsert_company_bundle(
        self,
        *,
        company: Company,
        listed_entity: ListedEntity,
        security: Security,
        listing: Listing,
        industry: Industry | None = None,
        facts: tuple[MarketFact, ...] = (),
        financial_facts: tuple[FinancialFact, ...] = (),
        announcement_facts: tuple[AnnouncementFact, ...] = (),
    ) -> None:
        with self._lock:
            conn = self._connect()
            try:
                self._write_company(conn, company)
                self._write_listed_entity(conn, listed_entity)
                self._write_security(conn, security)
                self._write_listing(conn, listing)
                if industry is not None:
                    self._write_industry(conn, industry)
                    conn.execute(
                        "INSERT OR IGNORE INTO company_industry (company_id, industry_id) "
                        "VALUES (?, ?)",
                        (company.company_id, industry.industry_id),
                    )
                for fact in facts:
                    self._insert_market_fact(conn, fact)
                for fact in financial_facts:
                    self._insert_financial_fact(conn, fact)
                for fact in announcement_facts:
                    self._insert_announcement_fact(conn, fact)
                conn.commit()
            finally:
                self._close(conn)

    def upsert_market_facts(self, company_id: str, facts: tuple[MarketFact, ...]) -> None:
        with self._lock:
            conn = self._connect()
            try:
                for fact in facts:
                    self._insert_market_fact(conn, fact)
                conn.commit()
            finally:
                self._close(conn)

    def upsert_financial_facts(
        self, company_id: str, facts: tuple[FinancialFact, ...]
    ) -> None:
        with self._lock:
            conn = self._connect()
            try:
                for fact in facts:
                    self._insert_financial_fact(conn, fact)
                conn.commit()
            finally:
                self._close(conn)

    def upsert_announcement_facts(
        self, company_id: str, facts: tuple[AnnouncementFact, ...]
    ) -> None:
        with self._lock:
            conn = self._connect()
            try:
                for fact in facts:
                    self._insert_announcement_fact(conn, fact)
                conn.commit()
            finally:
                self._close(conn)

    def upsert_quote(self, quote: QuoteSnapshot) -> None:
        with self._lock:
            conn = self._connect()
            try:
                self._insert_quote(conn, quote)
                conn.commit()
            finally:
                self._close(conn)

    # --- identity writers (current-truth upsert) ------------------------------

    @staticmethod
    def _write_company(conn: sqlite3.Connection, company: Company) -> None:
        conn.execute(
            "INSERT INTO company "
            "(company_id, name, aliases, region, external_ids) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(company_id) DO UPDATE SET "
            "name=excluded.name, aliases=excluded.aliases, region=excluded.region, "
            "external_ids=excluded.external_ids",
            (
                company.company_id,
                company.name,
                _dumps(list(company.aliases)),
                company.region,
                _dumps(list(company.external_ids)),
            ),
        )

    @staticmethod
    def _write_listed_entity(conn: sqlite3.Connection, entity: ListedEntity) -> None:
        conn.execute(
            "INSERT INTO listed_entity "
            "(listed_entity_id, company_id, disclosure_name, source_ref) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(listed_entity_id) DO UPDATE SET "
            "company_id=excluded.company_id, disclosure_name=excluded.disclosure_name, "
            "source_ref=excluded.source_ref",
            (
                entity.listed_entity_id,
                entity.company_id,
                entity.disclosure_name,
                _dumps(entity.source_ref.model_dump(mode="json")),
            ),
        )

    @staticmethod
    def _write_security(conn: sqlite3.Connection, security: Security) -> None:
        conn.execute(
            "INSERT INTO security "
            "(security_id, listed_entity_id, ts_code, symbol, name, exchange, "
            "security_type, currency) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(security_id) DO UPDATE SET "
            "listed_entity_id=excluded.listed_entity_id, ts_code=excluded.ts_code, "
            "symbol=excluded.symbol, name=excluded.name, exchange=excluded.exchange, "
            "security_type=excluded.security_type, currency=excluded.currency",
            (
                security.security_id,
                security.listed_entity_id,
                security.ts_code,
                security.symbol,
                security.name,
                security.exchange.value,
                security.security_type.value,
                security.currency,
            ),
        )

    @staticmethod
    def _write_listing(conn: sqlite3.Connection, listing: Listing) -> None:
        conn.execute(
            "INSERT INTO listing "
            "(listing_id, security_id, exchange, board, listed_at, delisted_at, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(listing_id) DO UPDATE SET "
            "security_id=excluded.security_id, exchange=excluded.exchange, "
            "board=excluded.board, listed_at=excluded.listed_at, "
            "delisted_at=excluded.delisted_at, status=excluded.status",
            (
                listing.listing_id,
                listing.security_id,
                listing.exchange.value,
                listing.board.value,
                _iso(listing.listed_at),
                _iso(listing.delisted_at),
                listing.status.value,
            ),
        )

    @staticmethod
    def _write_industry(conn: sqlite3.Connection, industry: Industry) -> None:
        conn.execute(
            "INSERT INTO industry "
            "(industry_id, taxonomy, name, code, level) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(industry_id) DO UPDATE SET "
            "taxonomy=excluded.taxonomy, name=excluded.name, code=excluded.code, "
            "level=excluded.level",
            (
                industry.industry_id,
                industry.taxonomy,
                industry.name,
                industry.code,
                industry.level,
            ),
        )

    # --- observation writers (append-only, idempotent) -----------------------

    def _insert_observation(
        self,
        conn: sqlite3.Connection,
        *,
        logical_key: str,
        content_hash: str,
        fact_type: str,
        subject: SubjectRef,
        predicate: str | None,
        object_value: str | None,
        occurred_at: Any,
        published_at: Any,
        captured_at: Any,
        confidence: float,
        source_ref: SourceRef | None,
        attributes: dict[str, Any] | None,
        schema_version: str | None,
    ) -> int | None:
        """Append one observation; idempotent on (logical_key, content_hash).

        Returns the observation_id backing this (logical_key, content_hash) row
        — newly inserted or pre-existing — or None when it cannot be resolved.
        """
        cur = conn.execute(
            "INSERT OR IGNORE INTO knowledge_observation "
            "(logical_key, content_hash, fact_type, subject_type, subject_id, "
            "predicate, object_type, object_value, occurred_at, published_at, "
            "captured_at, confidence, source_ref, attributes, schema_version) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                logical_key,
                content_hash,
                fact_type,
                subject.entity_type,
                subject.entity_id,
                predicate,
                "text",
                object_value,
                _iso(occurred_at),
                _iso(published_at),
                _iso(captured_at),
                confidence,
                _dumps(source_ref.model_dump(mode="json")) if source_ref else None,
                _dumps(attributes) if attributes else None,
                schema_version,
            ),
        )
        if cur.lastrowid and cur.rowcount:
            return int(cur.lastrowid)
        row = conn.execute(
            "SELECT observation_id FROM knowledge_observation "
            "WHERE logical_key = ? AND content_hash = ?",
            (logical_key, content_hash),
        ).fetchone()
        return int(row[0]) if row is not None else None

    def _insert_market_fact(self, conn: sqlite3.Connection, fact: MarketFact) -> int | None:
        return self._insert_observation(
            conn,
            logical_key=fact.fact_id,
            content_hash=_market_fact_hash(fact),
            fact_type=fact.fact_type.value,
            subject=fact.subject_ref,
            predicate=fact.predicate,
            object_value=fact.object_value,
            occurred_at=fact.occurred_at,
            published_at=fact.published_at,
            captured_at=fact.captured_at,
            confidence=fact.confidence,
            source_ref=fact.source_ref,
            attributes=_market_attributes(fact),
            schema_version=fact.schema_version,
        )

    def _insert_financial_fact(self, conn: sqlite3.Connection, fact: FinancialFact) -> None:
        observation_id = self._insert_observation(
            conn,
            logical_key=fact.fact_id,
            content_hash=_financial_fact_hash(fact),
            fact_type=fact.fact_type.value,
            subject=fact.subject_ref,
            predicate=f"financial.{fact.metric_name}",
            object_value=_num_text(fact.metric_value),
            occurred_at=fact.occurred_at,
            published_at=fact.published_at,
            captured_at=fact.captured_at,
            confidence=fact.confidence,
            source_ref=fact.source_ref,
            attributes=_subject_label_payload(fact.subject_ref),
            schema_version=fact.schema_version,
        )
        if observation_id is None:
            return
        conn.execute(
            "INSERT OR IGNORE INTO financial_observation "
            "(observation_id, metric_name, report_period, report_type, metric_value, "
            "unit, currency, yoy, qoq, restated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                observation_id,
                fact.metric_name,
                fact.report_period,
                fact.report_type,
                fact.metric_value,
                fact.unit,
                fact.currency,
                fact.yoy,
                fact.qoq,
                1 if fact.restated else 0,
            ),
        )

    def _insert_announcement_fact(
        self, conn: sqlite3.Connection, fact: AnnouncementFact
    ) -> None:
        observation_id = self._insert_observation(
            conn,
            logical_key=fact.fact_id,
            content_hash=_announcement_fact_hash(fact),
            fact_type=fact.fact_type.value,
            subject=fact.subject_ref,
            predicate="disclosed_announcement",
            object_value=fact.title,
            occurred_at=fact.occurred_at,
            published_at=fact.published_at,
            captured_at=fact.captured_at,
            confidence=fact.confidence,
            source_ref=fact.source_ref,
            attributes=_announcement_attributes(fact),
            schema_version=fact.schema_version,
        )
        if observation_id is None:
            return
        conn.execute(
            "INSERT OR IGNORE INTO announcement_observation "
            "(observation_id, announcement_id, announcement_type, title, publish_date, "
            "document_url, document_hash, extracted_summary) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                observation_id,
                fact.announcement_id,
                fact.announcement_type.value,
                fact.title,
                _iso(fact.published_at),
                fact.document_url,
                fact.document_hash,
                fact.extracted_summary,
            ),
        )

    def _insert_quote(self, conn: sqlite3.Connection, quote: QuoteSnapshot) -> None:
        """Converge a quote snapshot onto the same spine row as its QUOTE fact.

        The bundle's QUOTE ``MarketFact`` (built by ``build_quote_fact``) and a
        standalone ``upsert_quote`` share one ``logical_key`` and one
        ``content_hash`` because both go through ``build_quote_fact`` +
        ``_insert_market_fact``. This call then attaches the structured quote
        detail to that single observation.
        """
        label = self._security_label(conn, quote.security_id)
        fact = build_quote_fact(quote, label=label)
        observation_id = self._insert_market_fact(conn, fact)
        if observation_id is None:
            return
        conn.execute(
            "INSERT OR IGNORE INTO quote_observation "
            "(observation_id, security_id, quote_id, trade_date, open, high, low, "
            "close, previous_close, volume, amount) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                observation_id,
                quote.security_id,
                quote.quote_id,
                quote.trade_date.isoformat(),
                quote.open,
                quote.high,
                quote.low,
                quote.close,
                quote.previous_close,
                quote.volume,
                quote.amount,
            ),
        )

    @staticmethod
    def _security_label(conn: sqlite3.Connection, security_id: str) -> str | None:
        row = conn.execute(
            "SELECT name FROM security WHERE security_id = ?",
            (security_id,),
        ).fetchone()
        return row[0] if row is not None else None

    # --- read (read model) ----------------------------------------------------

    def get_company_intelligence_by_ts_code(
        self, ts_code: str
    ) -> CompanyIntelligence | None:
        with self._lock:
            conn = self._connect()
            try:
                return self._assemble_intelligence(conn, ts_code)
            finally:
                self._close(conn)

    def get_company_timeline(
        self,
        ts_code: str,
        *,
        time_basis: TimeBasis = TimeBasis.PUBLISHED_AT,
        latest_first: bool = True,
    ) -> tuple[CompanyTimelineEvent, ...]:
        with self._lock:
            conn = self._connect()
            try:
                resolved = self._resolve_company(conn, ts_code)
                if resolved is None:
                    return ()
                company_id = resolved[0]
                facts, financial_facts, announcement_facts = self._load_facts(conn, company_id)
                return build_company_timeline(
                    company_id,
                    market_facts=facts,
                    financial_facts=financial_facts,
                    announcement_facts=announcement_facts,
                    time_basis=time_basis,
                    latest_first=latest_first,
                )
            finally:
                self._close(conn)

    def list_company_intelligence(self, limit: int = 50) -> tuple[CompanyIntelligence, ...]:
        with self._lock:
            conn = self._connect()
            try:
                ts_codes = [
                    row[0]
                    for row in conn.execute("SELECT ts_code FROM security").fetchall()
                ]
                results = [
                    item
                    for ts_code in ts_codes
                    if (item := self._assemble_intelligence(conn, ts_code)) is not None
                ]
                return tuple(results[:limit])
            finally:
                self._close(conn)

    def search_company(self, text: str, limit: int = 50) -> tuple[CompanyIntelligence, ...]:
        needle = text.lower()
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT company_id, name, aliases FROM company"
                ).fetchall()
                matched: list[str] = []
                for company_id, name, aliases_json in rows:
                    aliases = [a.lower() for a in (_loads(aliases_json) or [])]
                    if needle in name.lower() or any(needle in alias for alias in aliases):
                        ts_code = self._ts_code_for_company(conn, company_id)
                        if ts_code is not None:
                            matched.append(ts_code)
                results = [
                    item
                    for ts_code in matched[:limit]
                    if (item := self._assemble_intelligence(conn, ts_code)) is not None
                ]
                return tuple(results)
            finally:
                self._close(conn)

    # --- read helpers ---------------------------------------------------------

    def _resolve_company(
        self, conn: sqlite3.Connection, ts_code: str
    ) -> tuple[str, str, str] | None:
        """Return (company_id, listed_entity_id, security_id) for a ts_code."""
        row = conn.execute(
            "SELECT s.security_id, s.listed_entity_id, le.company_id "
            "FROM security s JOIN listed_entity le ON s.listed_entity_id = le.listed_entity_id "
            "WHERE lower(s.ts_code) = ?",
            (ts_code.lower(),),
        ).fetchone()
        if row is None:
            return None
        security_id, listed_entity_id, company_id = row
        return company_id, listed_entity_id, security_id

    def _ts_code_for_company(self, conn: sqlite3.Connection, company_id: str) -> str | None:
        row = conn.execute(
            "SELECT s.ts_code FROM security s "
            "JOIN listed_entity le ON s.listed_entity_id = le.listed_entity_id "
            "WHERE le.company_id = ? LIMIT 1",
            (company_id,),
        ).fetchone()
        return row[0] if row is not None else None

    def _assemble_intelligence(
        self, conn: sqlite3.Connection, ts_code: str
    ) -> CompanyIntelligence | None:
        resolved = self._resolve_company(conn, ts_code)
        if resolved is None:
            return None
        company_id, listed_entity_id, security_id = resolved

        company = self._read_company(conn, company_id)
        listed_entity = self._read_listed_entity(conn, listed_entity_id)
        security = self._read_security(conn, security_id)
        listing = self._read_listing(conn, security_id)
        if company is None or listed_entity is None or security is None or listing is None:
            return None
        industry = self._read_industry(conn, company_id)
        latest_quote = self._latest_quote(conn, security_id)
        facts, financial_facts, announcement_facts = self._load_facts(conn, company_id)
        timeline = build_company_timeline(
            company_id,
            market_facts=facts,
            financial_facts=financial_facts,
            announcement_facts=announcement_facts,
        )
        source_refs = self._collect_source_refs(
            listed_entity, latest_quote, facts, financial_facts, announcement_facts
        )
        return CompanyIntelligence(
            company=company,
            listed_entity=listed_entity,
            security=security,
            listing=listing,
            industry=industry,
            latest_quote=latest_quote,
            facts=facts,
            financial_facts=financial_facts,
            announcement_facts=announcement_facts,
            timeline=timeline,
            source_refs=source_refs,
        )

    @staticmethod
    def _read_company(conn: sqlite3.Connection, company_id: str) -> Company | None:
        row = conn.execute(
            "SELECT company_id, name, aliases, region, external_ids "
            "FROM company WHERE company_id = ?",
            (company_id,),
        ).fetchone()
        if row is None:
            return None
        return Company(
            company_id=row[0],
            name=row[1],
            aliases=tuple(_loads(row[2]) or ()),
            region=row[3],
            external_ids=tuple(_loads(row[4]) or ()),
        )

    @staticmethod
    def _read_listed_entity(
        conn: sqlite3.Connection, listed_entity_id: str
    ) -> ListedEntity | None:
        row = conn.execute(
            "SELECT listed_entity_id, company_id, disclosure_name, source_ref "
            "FROM listed_entity WHERE listed_entity_id = ?",
            (listed_entity_id,),
        ).fetchone()
        if row is None:
            return None
        return ListedEntity(
            listed_entity_id=row[0],
            company_id=row[1],
            disclosure_name=row[2],
            source_ref=SourceRef.model_validate(_loads(row[3])),
        )

    @staticmethod
    def _read_security(conn: sqlite3.Connection, security_id: str) -> Security | None:
        row = conn.execute(
            "SELECT security_id, listed_entity_id, ts_code, symbol, name, exchange, "
            "security_type, currency FROM security WHERE security_id = ?",
            (security_id,),
        ).fetchone()
        if row is None:
            return None
        return Security(
            security_id=row[0],
            listed_entity_id=row[1],
            ts_code=row[2],
            symbol=row[3],
            name=row[4],
            exchange=Exchange(row[5]),
            security_type=SecurityType(row[6]),
            currency=row[7],
        )

    @staticmethod
    def _read_listing(conn: sqlite3.Connection, security_id: str) -> Listing | None:
        row = conn.execute(
            "SELECT listing_id, security_id, exchange, board, listed_at, delisted_at, status "
            "FROM listing WHERE security_id = ? LIMIT 1",
            (security_id,),
        ).fetchone()
        if row is None:
            return None
        return Listing(
            listing_id=row[0],
            security_id=row[1],
            exchange=Exchange(row[2]),
            board=Board(row[3]),
            listed_at=_date_or_none(row[4]),
            delisted_at=_date_or_none(row[5]),
            status=ListingStatus(row[6]),
        )

    @staticmethod
    def _read_industry(conn: sqlite3.Connection, company_id: str) -> Industry | None:
        row = conn.execute(
            "SELECT i.industry_id, i.taxonomy, i.name, i.code, i.level "
            "FROM industry i JOIN company_industry ci ON i.industry_id = ci.industry_id "
            "WHERE ci.company_id = ? LIMIT 1",
            (company_id,),
        ).fetchone()
        if row is None:
            return None
        return Industry(
            industry_id=row[0],
            taxonomy=row[1],
            name=row[2],
            code=row[3],
            level=row[4],
        )

    def _latest_quote(
        self, conn: sqlite3.Connection, security_id: str
    ) -> QuoteSnapshot | None:
        row = conn.execute(
            "SELECT q.quote_id, q.security_id, q.trade_date, q.open, q.high, q.low, "
            "q.close, q.previous_close, q.volume, q.amount, o.source_ref "
            "FROM quote_observation q "
            "JOIN knowledge_observation o ON q.observation_id = o.observation_id "
            "WHERE q.security_id = ? ORDER BY q.trade_date DESC, q.observation_id DESC LIMIT 1",
            (security_id,),
        ).fetchone()
        if row is None:
            return None
        return QuoteSnapshot(
            quote_id=row[0],
            security_id=row[1],
            trade_date=_date_or_none(row[2]),
            open=row[3],
            high=row[4],
            low=row[5],
            close=row[6],
            previous_close=row[7],
            volume=row[8],
            amount=row[9],
            source_ref=SourceRef.model_validate(_loads(row[10])),
        )

    def _load_facts(
        self, conn: sqlite3.Connection, company_id: str
    ) -> tuple[
        tuple[MarketFact, ...],
        tuple[FinancialFact, ...],
        tuple[AnnouncementFact, ...],
    ]:
        """Project the latest observation per logical_key back into domain facts.

        Mirrors the in-memory adapter: every ingested MarketFact (including the
        QUOTE MarketFact) is returned in ``facts``; FinancialFact and
        AnnouncementFact come from their detail tables.
        """
        subject_ids = self._subject_ids_for_company(conn, company_id)
        if not subject_ids:
            return (), (), ()
        rows = self._latest_observations(conn, subject_ids)

        market: list[MarketFact] = []
        financial: list[FinancialFact] = []
        announcement: list[AnnouncementFact] = []
        for row in rows:
            fact_type = row["fact_type"]
            if fact_type == FactType.FINANCIAL.value:
                fact = self._row_to_financial_fact(conn, row)
                if fact is not None:
                    financial.append(fact)
            elif fact_type == FactType.ANNOUNCEMENT.value:
                fact = self._row_to_announcement_fact(conn, row)
                if fact is not None:
                    announcement.append(fact)
            else:
                market.append(self._row_to_market_fact(row))
        return tuple(market), tuple(financial), tuple(announcement)

    def _subject_ids_for_company(
        self, conn: sqlite3.Connection, company_id: str
    ) -> list[str]:
        """Surrogate ids a company's facts can be filed under (company + securities)."""
        ids = [company_id]
        rows = conn.execute(
            "SELECT s.security_id FROM security s "
            "JOIN listed_entity le ON s.listed_entity_id = le.listed_entity_id "
            "WHERE le.company_id = ?",
            (company_id,),
        ).fetchall()
        ids.extend(r[0] for r in rows)
        return ids

    def _latest_observations(
        self, conn: sqlite3.Connection, subject_ids: list[str]
    ) -> list[dict[str, Any]]:
        placeholders = ",".join("?" for _ in subject_ids)
        rows = conn.execute(
            "SELECT observation_id, logical_key, content_hash, fact_type, subject_type, "
            "subject_id, predicate, object_value, occurred_at, published_at, captured_at, "
            "confidence, source_ref, attributes, schema_version "
            "FROM knowledge_observation "
            f"WHERE subject_id IN ({placeholders}) "
            "ORDER BY logical_key, captured_at DESC, observation_id DESC",
            tuple(subject_ids),
        ).fetchall()
        latest: dict[str, dict[str, Any]] = {}
        for row in rows:
            record = {
                "observation_id": row[0],
                "logical_key": row[1],
                "content_hash": row[2],
                "fact_type": row[3],
                "subject_type": row[4],
                "subject_id": row[5],
                "predicate": row[6],
                "object_value": row[7],
                "occurred_at": row[8],
                "published_at": row[9],
                "captured_at": row[10],
                "confidence": row[11],
                "source_ref": row[12],
                "attributes": row[13],
                "schema_version": row[14],
            }
            latest.setdefault(record["logical_key"], record)
        return list(latest.values())

    def _row_to_market_fact(self, row: dict[str, Any]) -> MarketFact:
        payload = _loads(row["attributes"]) or {}
        attributes = tuple(
            FactAttribute(key=item["key"], value=item["value"])
            for item in payload.get(_ATTR_FACT_ATTRIBUTES, ())
        )
        return MarketFact(
            fact_id=row["logical_key"],
            fact_type=FactType(row["fact_type"]),
            subject_ref=_subject_ref(row, payload),
            predicate=row["predicate"] or "",
            object_value=row["object_value"] or "",
            occurred_at=_dt_or_none(row["occurred_at"]),
            published_at=_dt_or_none(row["published_at"]),
            captured_at=_dt_or_none(row["captured_at"]),
            source_ref=SourceRef.model_validate(_loads(row["source_ref"])),
            confidence=row["confidence"],
            attributes=attributes,
            schema_version=row["schema_version"] or "market_fact.v1",
        )

    def _row_to_financial_fact(
        self, conn: sqlite3.Connection, row: dict[str, Any]
    ) -> FinancialFact | None:
        detail = conn.execute(
            "SELECT metric_name, report_period, report_type, metric_value, unit, "
            "currency, yoy, qoq, restated FROM financial_observation WHERE observation_id = ?",
            (row["observation_id"],),
        ).fetchone()
        if detail is None:
            return None
        payload = _loads(row["attributes"]) or {}
        return FinancialFact(
            fact_id=row["logical_key"],
            subject_ref=_subject_ref(row, payload),
            report_period=detail[1],
            report_type=detail[2] or "",
            metric_name=detail[0],
            metric_value=detail[3],
            unit=detail[4] or "",
            currency=detail[5] or "CNY",
            yoy=detail[6],
            qoq=detail[7],
            restated=bool(detail[8]),
            occurred_at=_dt_or_none(row["occurred_at"]),
            published_at=_dt_or_none(row["published_at"]),
            captured_at=_dt_or_none(row["captured_at"]),
            source_ref=SourceRef.model_validate(_loads(row["source_ref"])),
            confidence=row["confidence"],
            schema_version=row["schema_version"] or "financial_fact.v1",
        )

    def _row_to_announcement_fact(
        self, conn: sqlite3.Connection, row: dict[str, Any]
    ) -> AnnouncementFact | None:
        detail = conn.execute(
            "SELECT announcement_id, announcement_type, title, publish_date, "
            "document_url, document_hash, extracted_summary "
            "FROM announcement_observation WHERE observation_id = ?",
            (row["observation_id"],),
        ).fetchone()
        if detail is None:
            return None
        payload = _loads(row["attributes"]) or {}
        mentioned = tuple(
            EntityLink.model_validate(item)
            for item in payload.get(_ATTR_MENTIONED_ENTITIES, ())
        )
        return AnnouncementFact(
            fact_id=row["logical_key"],
            subject_ref=_subject_ref(row, payload),
            announcement_id=detail[0],
            announcement_type=AnnouncementType(detail[1]) if detail[1] else AnnouncementType.OTHER,
            title=detail[2] or "",
            published_at=_dt_or_none(row["published_at"]),
            occurred_at=_dt_or_none(row["occurred_at"]),
            captured_at=_dt_or_none(row["captured_at"]),
            document_url=detail[4] or "",
            document_hash=detail[5] or "",
            extracted_summary=detail[6] or "",
            mentioned_entities=mentioned,
            source_ref=SourceRef.model_validate(_loads(row["source_ref"])),
            confidence=row["confidence"],
            schema_version=row["schema_version"] or "announcement_fact.v1",
        )

    @staticmethod
    def _collect_source_refs(
        listed_entity: ListedEntity,
        latest_quote: QuoteSnapshot | None,
        facts: tuple[MarketFact, ...],
        financial_facts: tuple[FinancialFact, ...],
        announcement_facts: tuple[AnnouncementFact, ...],
    ) -> tuple[SourceRef, ...]:
        refs = [listed_entity.source_ref]
        refs.extend(fact.source_ref for fact in facts)
        refs.extend(fact.source_ref for fact in financial_facts)
        refs.extend(fact.source_ref for fact in announcement_facts)
        if latest_quote is not None:
            refs.append(latest_quote.source_ref)
        deduped: dict[tuple[str, str | None], SourceRef] = {}
        for ref in refs:
            deduped[(ref.source_id, ref.external_id)] = ref
        return tuple(deduped.values())


# --- extension payload (spine attributes JSON) --------------------------------


def _subject_label_payload(subject: SubjectRef) -> dict[str, Any] | None:
    if subject.label is None:
        return None
    return {_ATTR_SUBJECT_LABEL: subject.label}


def _market_attributes(fact: MarketFact) -> dict[str, Any] | None:
    payload: dict[str, Any] = {}
    if fact.subject_ref.label is not None:
        payload[_ATTR_SUBJECT_LABEL] = fact.subject_ref.label
    if fact.attributes:
        payload[_ATTR_FACT_ATTRIBUTES] = [
            {"key": attr.key, "value": attr.value} for attr in fact.attributes
        ]
    return payload or None


def _announcement_attributes(fact: AnnouncementFact) -> dict[str, Any] | None:
    payload: dict[str, Any] = {}
    if fact.subject_ref.label is not None:
        payload[_ATTR_SUBJECT_LABEL] = fact.subject_ref.label
    if fact.mentioned_entities:
        payload[_ATTR_MENTIONED_ENTITIES] = [
            entity.model_dump(mode="json") for entity in fact.mentioned_entities
        ]
    return payload or None


def _subject_ref(row: dict[str, Any], payload: dict[str, Any]) -> SubjectRef:
    return SubjectRef(
        entity_type=row["subject_type"],
        entity_id=row["subject_id"],
        label=payload.get(_ATTR_SUBJECT_LABEL),
    )


# --- content hashing (idempotency on the semantic fields) ---------------------


def _market_fact_hash(fact: MarketFact) -> str:
    return _content_hash(
        fact.fact_id,
        fact.object_value,
        (
            fact.fact_type.value,
            fact.predicate,
            tuple((attr.key, attr.value) for attr in fact.attributes),
        ),
    )


def _financial_fact_hash(fact: FinancialFact) -> str:
    return _content_hash(
        fact.fact_id,
        _num_text(fact.metric_value),
        (
            fact.report_period,
            fact.metric_name,
            _num_text(fact.metric_value),
            _num_text(fact.yoy),
            _num_text(fact.qoq),
            fact.unit,
            fact.report_type,
        ),
    )


def _announcement_fact_hash(fact: AnnouncementFact) -> str:
    return _content_hash(
        fact.fact_id,
        fact.title,
        (
            fact.announcement_id,
            fact.announcement_type.value,
            fact.title,
            fact.document_hash,
        ),
    )


def _content_hash(
    logical_key: str, object_value: str | None, hash_parts: tuple[Any, ...]
) -> str:
    payload = json.dumps(
        [logical_key, object_value, hash_parts],
        ensure_ascii=False,
        default=str,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _num_text(value: float | None) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _date_or_none(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value[:10])


def _dt_or_none(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)
