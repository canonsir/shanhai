"""Market Data MVP schemas.

Milestone 2 Data Foundation keeps market reality separate from Runtime /
Experience. These models describe A-share facts, identities, and derived
company intelligence views; they do not carry trading instructions.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Exchange(str, Enum):
    SSE = "SSE"
    SZSE = "SZSE"
    BSE = "BSE"


class Board(str, Enum):
    MAIN = "main"
    SME = "sme"
    CHINEXT = "chinext"
    STAR = "star"
    BSE = "bse"
    UNKNOWN = "unknown"


class SecurityType(str, Enum):
    A_SHARE = "a_share"


class ListingStatus(str, Enum):
    LISTED = "listed"
    DELISTED = "delisted"
    SUSPENDED = "suspended"
    UNKNOWN = "unknown"


class SourceTrustLevel(str, Enum):
    OFFICIAL = "L1_official"
    LICENSED_AGGREGATOR = "L2_licensed_aggregator"
    PUBLIC_AGGREGATOR = "L3_public_aggregator"
    DERIVED = "L4_derived"


class FactType(str, Enum):
    """Market Knowledge fact taxonomy (frozen in M2.3 design review)."""

    QUOTE = "quote"
    FINANCIAL = "financial"
    ANNOUNCEMENT = "announcement"
    NEWS = "news"
    INDUSTRY = "industry"
    PROFILE = "profile"
    POLICY = "policy"
    ANOMALY = "anomaly"
    CAPITAL_FLOW = "capital_flow"
    SHAREHOLDER = "shareholder"


class TimeBasis(str, Enum):
    """Which timestamp a timeline event was ordered by.

    Knowledge facts keep three timestamps and never collapse to one: when the
    event actually happened, when the market could see it, and when ShanHai
    captured it.
    """

    OCCURRED_AT = "occurred_at"
    PUBLISHED_AT = "published_at"
    CAPTURED_AT = "captured_at"


class AnnouncementType(str, Enum):
    PERIODIC_REPORT = "periodic_report"
    EARNINGS_PREVIEW = "earnings_preview"
    DIVIDEND = "dividend"
    MAJOR_CONTRACT = "major_contract"
    MERGER_ACQUISITION = "merger_acquisition"
    REGULATORY_INQUIRY = "regulatory_inquiry"
    RISK_WARNING = "risk_warning"
    SHAREHOLDER_CHANGE = "shareholder_change"
    OTHER = "other"


class SourceRef(_FrozenModel):
    source_id: str
    source_name: str
    trust_level: SourceTrustLevel = SourceTrustLevel.PUBLIC_AGGREGATOR
    external_id: str | None = None
    captured_at: datetime = Field(default_factory=datetime.utcnow)


class ResolvedMarketIdentity(_FrozenModel):
    ts_code: str
    company_id: str
    listed_entity_id: str
    security_id: str
    listing_id: str
    external_ids: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()


class MarketSource(_FrozenModel):
    source_id: str
    source_name: str
    source_type: str
    trust_level: SourceTrustLevel
    license_notes: str = ""
    rate_limit: str = ""
    freshness_expectation: str = ""
    historical_coverage: str = ""
    identifier_scheme: str = ""
    failure_mode: str = ""


class Company(_FrozenModel):
    company_id: str
    name: str
    aliases: tuple[str, ...] = ()
    region: str | None = None
    external_ids: tuple[str, ...] = ()


class IdentityMapping(_FrozenModel):
    """Identity Registry row (``entity_identity_mapping``).

    Resolves an external/legacy identifier to a surrogate ``internal_id``. It is
    the single source of truth for deterministic resolution and for old -> new
    migration traceability. Two relations share one shape:

    - legacy migration: ``source="legacy"`` maps an old ts_code-derived id
      (``external_id``) to the new surrogate ``internal_id``.
    - external mapping: ``source="tushare" | ...`` maps a vendor identifier
      (``external_id``) to the surrogate ``internal_id``.

    Rollback is supported by bidirectional lookup: every mapping retains both
    ends, so ``internal_id`` can recover all external/legacy ids and vice versa.
    """

    entity_type: str
    internal_id: str
    source: str
    external_id: str
    migration_version: str = ""
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ListedEntity(_FrozenModel):
    listed_entity_id: str
    company_id: str
    disclosure_name: str
    source_ref: SourceRef


class Security(_FrozenModel):
    security_id: str
    listed_entity_id: str
    ts_code: str
    symbol: str
    name: str
    exchange: Exchange
    security_type: SecurityType = SecurityType.A_SHARE
    currency: str = "CNY"


class Listing(_FrozenModel):
    listing_id: str
    security_id: str
    exchange: Exchange
    board: Board = Board.UNKNOWN
    listed_at: date | None = None
    delisted_at: date | None = None
    status: ListingStatus = ListingStatus.UNKNOWN


class Industry(_FrozenModel):
    industry_id: str
    taxonomy: str
    name: str
    code: str | None = None
    level: int | None = None


class QuoteSnapshot(_FrozenModel):
    quote_id: str
    security_id: str
    trade_date: date
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    previous_close: float | None = None
    volume: float | None = None
    amount: float | None = None
    source_ref: SourceRef


class SubjectRef(_FrozenModel):
    """The entity a fact is about.

    Points at a surrogate identity (company / listed_entity / security /
    industry). The external code is never an identity here; it only appears in
    SourceRef.external_id or fact attributes.
    """

    entity_type: str
    entity_id: str
    label: str | None = None


class FactAttribute(_FrozenModel):
    """Domain-specific key/value payload.

    Kept as a tuple of these (not a dict) so facts stay frozen-hashable. It
    must not replace the top-level semantic fields of a fact.
    """

    key: str
    value: str


class EntityLink(_FrozenModel):
    """A resolved or candidate entity reference carried by a fact.

    The linking process is preserved (resolver + confidence + reason), not only
    the final entity, so low-confidence links can stay auditable instead of
    silently binding to a company.
    """

    entity_type: str
    entity_id: str | None = None
    mention: str | None = None
    resolver: str = "deterministic"
    confidence: float = 1.0
    reason: str = ""


class MarketFact(_FrozenModel):
    """MarketFact v1 — the minimal cognition unit over the capital market.

    A MarketFact says: some subject, at some time, had/disclosed a traceable
    fact, sourced from some evidence, with a confidence and time semantics. It
    is not a quote row, a UI card, an Agent memory, or an ExperienceArtifact.

    Structured financial and announcement facts live in their own sibling
    models (FinancialFact / AnnouncementFact); this is the generic fact for
    profile / industry / quote / policy style facts. They all feed one timeline
    read model rather than collapsing into a single super table.
    """

    fact_id: str
    fact_type: FactType
    subject_ref: SubjectRef
    predicate: str
    object_value: str
    object_ref: SubjectRef | None = None
    occurred_at: datetime | None = None
    published_at: datetime | None = None
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_ref: SourceRef
    evidence_refs: tuple[str, ...] = ()
    confidence: float = 1.0
    entity_links: tuple[EntityLink, ...] = ()
    attributes: tuple[FactAttribute, ...] = ()
    schema_version: str = "market_fact.v1"


class FinancialFact(_FrozenModel):
    """Structured financial fact from a disclosed report or financial API.

    Independent from MarketFact on purpose: financial reporting is structured
    (period / metric / unit / yoy), so it gets its own shape instead of being
    flattened into a generic object_value string.
    """

    fact_id: str
    subject_ref: SubjectRef
    report_period: str
    report_type: str
    metric_name: str
    metric_value: float | None = None
    unit: str = ""
    currency: str = "CNY"
    yoy: float | None = None
    qoq: float | None = None
    restated: bool = False
    occurred_at: datetime | None = None
    published_at: datetime | None = None
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_ref: SourceRef
    confidence: float = 1.0
    fact_type: FactType = FactType.FINANCIAL
    schema_version: str = "financial_fact.v1"


class AnnouncementFact(_FrozenModel):
    """A disclosed company announcement.

    Stores the announcement reference and metadata only (title / type / link /
    optional extracted summary). It does not store ratings, trade advice, or
    unsupported inferences.
    """

    fact_id: str
    subject_ref: SubjectRef
    announcement_id: str
    announcement_type: AnnouncementType = AnnouncementType.OTHER
    title: str = ""
    published_at: datetime | None = None
    occurred_at: datetime | None = None
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    document_url: str = ""
    document_hash: str = ""
    extracted_summary: str = ""
    mentioned_entities: tuple[EntityLink, ...] = ()
    source_ref: SourceRef
    confidence: float = 1.0
    fact_type: FactType = FactType.ANNOUNCEMENT
    schema_version: str = "announcement_fact.v1"


class CompanyTimelineEvent(_FrozenModel):
    """Unified company knowledge timeline event (a read model, not a fact source).

    Generic / financial / announcement facts are projected onto one ordered
    timeline. The chosen ordering timestamp is recorded as ``event_time_basis``;
    the three underlying timestamps are never collapsed into one.
    """

    event_id: str
    company_id: str
    event_time: datetime
    event_time_basis: TimeBasis
    event_type: FactType
    title: str
    summary: str = ""
    fact_refs: tuple[str, ...] = ()
    source_refs: tuple[SourceRef, ...] = ()
    confidence: float = 1.0


class CompanyIntelligence(_FrozenModel):
    company: Company
    listed_entity: ListedEntity
    security: Security
    listing: Listing
    industry: Industry | None = None
    latest_quote: QuoteSnapshot | None = None
    facts: tuple[MarketFact, ...] = ()
    financial_facts: tuple[FinancialFact, ...] = ()
    announcement_facts: tuple[AnnouncementFact, ...] = ()
    timeline: tuple[CompanyTimelineEvent, ...] = ()
    source_refs: tuple[SourceRef, ...] = ()


class TushareStockBasicRecord(_FrozenModel):
    ts_code: str
    symbol: str
    name: str
    area: str | None = None
    industry: str | None = None
    market: str | None = None
    list_date: date | None = None
    exchange: Exchange
    list_status: ListingStatus = ListingStatus.UNKNOWN


class TushareDailyRecord(_FrozenModel):
    ts_code: str
    trade_date: date
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    pre_close: float | None = None
    vol: float | None = None
    amount: float | None = None


class TushareFinaIndicatorRecord(_FrozenModel):
    """Tushare ``fina_indicator`` row (a structured financial indicator)."""

    ts_code: str
    end_date: date
    ann_date: date | None = None
    revenue: float | None = None
    netprofit: float | None = None
    roe: float | None = None
    eps: float | None = None
    grossprofit_margin: float | None = None
    or_yoy: float | None = None
    netprofit_yoy: float | None = None


class TushareAnnouncementRecord(_FrozenModel):
    """Tushare ``anns_d`` row (a disclosed announcement reference)."""

    ts_code: str
    ann_date: date
    title: str
    ann_type: str | None = None
    url: str | None = None
    content: str | None = None


class TushareRequest(_FrozenModel):
    api_name: str
    token: str
    params: dict[str, Any] = Field(default_factory=dict)
    fields: str = ""


class TushareResponse(_FrozenModel):
    code: int
    msg: str | None = None
    fields: tuple[str, ...] = ()
    items: tuple[tuple[Any, ...], ...] = ()


class SyncTarget(_FrozenModel):
    ts_code: str
    expected_name: str


class SyncReport(_FrozenModel):
    synced_count: int
    requested_count: int
    company_ids: tuple[str, ...]
    missing_ts_codes: tuple[str, ...] = ()
    market_fact_count: int = 0
    financial_fact_count: int = 0
    announcement_fact_count: int = 0


CompanyApiPayload = dict[Literal["company"], dict[str, Any]]
