"""ShanHai Market Data — Milestone 2 Data Foundation MVP.

This package connects real A-share data provider boundaries to a minimal
market knowledge store and Company Intelligence API. It intentionally has no
RuntimeKernel / Experience Runtime / Memory Evolution dependency.
"""

from shanhai_market_data.api import CompanyIntelligenceAPI
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
    IdentityMapping,
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
    SubjectRef,
    SyncReport,
    SyncTarget,
    TimeBasis,
    TushareAnnouncementRecord,
    TushareDailyRecord,
    TushareFinaIndicatorRecord,
    TushareStockBasicRecord,
)
from shanhai_market_data.postgres_store import PostgresMarketKnowledgeStore
from shanhai_market_data.provider import (
    AnnouncementDataProvider,
    FinancialDataProvider,
    MarketDataProvider,
)
from shanhai_market_data.registry import IdentityRegistry
from shanhai_market_data.resolver import EntityResolver
from shanhai_market_data.scheduler import ScheduledIngestionConfig, TushareScheduledIngestion
from shanhai_market_data.store import InMemoryMarketKnowledgeStore
from shanhai_market_data.sync import AShareCompanySyncService, DEFAULT_A_SHARE_TARGETS
from shanhai_market_data.timeline import build_company_timeline
from shanhai_market_data.tushare import TushareProvider

__all__ = [
    "AShareCompanySyncService",
    "AnnouncementDataProvider",
    "AnnouncementFact",
    "AnnouncementType",
    "Board",
    "Company",
    "CompanyIntelligence",
    "CompanyIntelligenceAPI",
    "CompanyTimelineEvent",
    "DEFAULT_A_SHARE_TARGETS",
    "EntityLink",
    "EntityResolver",
    "Exchange",
    "FactAttribute",
    "FactType",
    "FinancialDataProvider",
    "FinancialFact",
    "IdentityMapping",
    "IdentityRegistry",
    "Industry",
    "InMemoryMarketKnowledgeStore",
    "ListedEntity",
    "Listing",
    "ListingStatus",
    "MarketDataProvider",
    "MarketFact",
    "MarketSource",
    "PostgresMarketKnowledgeStore",
    "QuoteSnapshot",
    "ResolvedMarketIdentity",
    "ScheduledIngestionConfig",
    "Security",
    "SecurityType",
    "SourceRef",
    "SourceTrustLevel",
    "SubjectRef",
    "SyncReport",
    "SyncTarget",
    "TimeBasis",
    "TushareAnnouncementRecord",
    "TushareDailyRecord",
    "TushareFinaIndicatorRecord",
    "TushareProvider",
    "TushareScheduledIngestion",
    "TushareStockBasicRecord",
    "build_company_timeline",
]
