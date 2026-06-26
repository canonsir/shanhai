"""ShanHai Market Data — Milestone 2 Data Foundation MVP.

This package connects real A-share data provider boundaries to a minimal
market knowledge store and Company Intelligence API. It intentionally has no
RuntimeKernel / Experience Runtime / Memory Evolution dependency.
"""

from shanhai_market_data.api import CompanyIntelligenceAPI
from shanhai_market_data.models import (
    Board,
    Company,
    CompanyIntelligence,
    Exchange,
    Industry,
    ListedEntity,
    Listing,
    ListingStatus,
    MarketFact,
    MarketSource,
    QuoteSnapshot,
    ResolvedMarketIdentity,
    Security,
    SecurityType,
    SourceRef,
    SourceTrustLevel,
    SyncReport,
    SyncTarget,
    TushareDailyRecord,
    TushareStockBasicRecord,
)
from shanhai_market_data.postgres_store import PostgresMarketKnowledgeStore
from shanhai_market_data.provider import MarketDataProvider
from shanhai_market_data.resolver import EntityResolver
from shanhai_market_data.scheduler import ScheduledIngestionConfig, TushareScheduledIngestion
from shanhai_market_data.store import InMemoryMarketKnowledgeStore
from shanhai_market_data.sync import AShareCompanySyncService, DEFAULT_A_SHARE_TARGETS
from shanhai_market_data.tushare import TushareProvider

__all__ = [
    "AShareCompanySyncService",
    "Board",
    "Company",
    "CompanyIntelligence",
    "CompanyIntelligenceAPI",
    "DEFAULT_A_SHARE_TARGETS",
    "Exchange",
    "Industry",
    "InMemoryMarketKnowledgeStore",
    "ListedEntity",
    "Listing",
    "ListingStatus",
    "MarketDataProvider",
    "MarketFact",
    "MarketSource",
    "QuoteSnapshot",
    "ResolvedMarketIdentity",
    "Security",
    "SecurityType",
    "SourceRef",
    "SourceTrustLevel",
    "SyncReport",
    "SyncTarget",
    "EntityResolver",
    "TushareDailyRecord",
    "PostgresMarketKnowledgeStore",
    "ScheduledIngestionConfig",
    "TushareScheduledIngestion",
    "TushareProvider",
    "TushareStockBasicRecord",
]
