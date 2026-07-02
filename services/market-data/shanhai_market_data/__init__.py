"""ShanHai Market Data — Milestone 2 Data Foundation MVP.

This package connects real A-share data provider boundaries to a minimal
market knowledge store and Company Intelligence API. It intentionally has no
RuntimeKernel / Experience Runtime / Memory Evolution dependency.
"""

from shanhai_market_data.acquisition import (
    AcquisitionReport,
    PublicDataAcquisitionService,
)
from shanhai_market_data.api import CompanyIntelligenceAPI
from shanhai_market_data.composition_root import build_provider_registry
from shanhai_market_data.domain.repository import MarketKnowledgeRepository
from shanhai_market_data.models import (
    AnnouncementFact,
    AnnouncementRecord,
    AnnouncementType,
    Board,
    Company,
    CompanyIntelligence,
    CompanyProfileRecord,
    CompanyTimelineEvent,
    EntityLink,
    Exchange,
    FactAttribute,
    FactType,
    FinancialFact,
    FinancialIndicatorRecord,
    IdentityMapping,
    Industry,
    ListedEntity,
    Listing,
    ListingStatus,
    MarketFact,
    MarketSource,
    QuoteRecord,
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
from shanhai_market_data.observation_provider import (
    DataQuery,
    ObservationDraft,
    ObservationProvider,
)
from shanhai_market_data.postgres_store import PostgresMarketKnowledgeStore
from shanhai_market_data.provider import (
    AnnouncementDataProvider,
    FinancialDataProvider,
    MarketDataProvider,
    PublicMarketDataProvider,
)
from shanhai_market_data.provider_registry import (
    ProviderDescriptor,
    ProviderRegistry,
    ProviderTier,
)
from shanhai_market_data.providers import CninfoAnnouncementProvider, EastMoneyProvider
from shanhai_market_data.registry import IdentityRegistry
from shanhai_market_data.resolver import EntityResolver
from shanhai_market_data.scheduler import ScheduledIngestionConfig, TushareScheduledIngestion
from shanhai_market_data.store import (
    InMemoryMarketKnowledgeRepository,
    InMemoryMarketKnowledgeStore,
)
from shanhai_market_data.sync import AShareCompanySyncService, DEFAULT_A_SHARE_TARGETS
from shanhai_market_data.timeline import build_company_timeline
from shanhai_market_data.tushare import TushareProvider

__all__ = [
    "AShareCompanySyncService",
    "AcquisitionReport",
    "AnnouncementDataProvider",
    "AnnouncementFact",
    "AnnouncementRecord",
    "AnnouncementType",
    "Board",
    "CninfoAnnouncementProvider",
    "Company",
    "CompanyIntelligence",
    "CompanyIntelligenceAPI",
    "CompanyProfileRecord",
    "CompanyTimelineEvent",
    "DEFAULT_A_SHARE_TARGETS",
    "DataQuery",
    "EastMoneyProvider",
    "EntityLink",
    "EntityResolver",
    "Exchange",
    "FactAttribute",
    "FactType",
    "FinancialDataProvider",
    "FinancialFact",
    "FinancialIndicatorRecord",
    "IdentityMapping",
    "IdentityRegistry",
    "Industry",
    "InMemoryMarketKnowledgeRepository",
    "InMemoryMarketKnowledgeStore",
    "ListedEntity",
    "Listing",
    "ListingStatus",
    "MarketDataProvider",
    "MarketFact",
    "MarketKnowledgeRepository",
    "MarketSource",
    "ObservationDraft",
    "ObservationProvider",
    "PostgresMarketKnowledgeStore",
    "ProviderDescriptor",
    "ProviderRegistry",
    "ProviderTier",
    "PublicDataAcquisitionService",
    "PublicMarketDataProvider",
    "QuoteRecord",
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
    "build_provider_registry",
]
