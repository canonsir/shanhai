"""Market Data MVP schemas.

Milestone 2 Data Foundation keeps market reality separate from Runtime /
Experience. These models describe A-share facts, identities, and derived
company intelligence views; they do not carry trading instructions.
"""

from __future__ import annotations

from datetime import date, datetime
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


class MarketFact(_FrozenModel):
    fact_id: str
    entity_id: str
    fact_type: str
    value: str
    source_ref: SourceRef
    observed_at: datetime = Field(default_factory=datetime.utcnow)
    valid_from: date | None = None
    valid_to: date | None = None


class CompanyIntelligence(_FrozenModel):
    company: Company
    listed_entity: ListedEntity
    security: Security
    listing: Listing
    industry: Industry | None = None
    latest_quote: QuoteSnapshot | None = None
    facts: tuple[MarketFact, ...] = ()
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


CompanyApiPayload = dict[Literal["company"], dict[str, Any]]
