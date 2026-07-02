"""Market data provider contracts.

Two contracts live here, both read-only and both forbidden from resolving
ShanHai entity identity, writing knowledge, calling Runtime, or producing
trading signals.

1. ``PublicMarketDataProvider`` (M3.2 Data Acquisition Foundation) is the
   source-neutral interface ShanHai owns. Every provider — free or commercial —
   implements the same five ``fetch_*`` methods and returns ShanHai's own
   normalized records, each carrying a ``SourceRef`` for provenance. Concrete
   implementations (``providers/eastmoney.py``, ``providers/cninfo.py``,
   ``providers/tushare.py`` ...) are all peers; no single vendor defines the
   shape.

2. The legacy ``MarketDataProvider`` / ``FinancialDataProvider`` /
   ``AnnouncementDataProvider`` Protocols below are the original Tushare-shaped
   contracts still consumed by ``sync.py``. They are retained so the existing
   ingestion path keeps working while the source-neutral interface is adopted.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from shanhai_market_data.models import (
    AnnouncementRecord,
    CompanyProfileRecord,
    FinancialIndicatorRecord,
    QuoteRecord,
    SourceRef,
    TushareAnnouncementRecord,
    TushareDailyRecord,
    TushareFinaIndicatorRecord,
    TushareStockBasicRecord,
)


@runtime_checkable
class PublicMarketDataProvider(Protocol):
    """Source-neutral market data provider (M3.2).

    Each method returns ``(record, SourceRef)`` pairs (or just records when the
    SourceRef is uniform per call) so provenance travels with the data from the
    moment it leaves the network boundary. A provider may raise
    ``NotImplementedError`` for a capability it does not cover; callers degrade
    gracefully rather than assume one vendor covers everything.
    """

    name: str

    def fetch_company_profile(self, ts_code: str) -> tuple[CompanyProfileRecord, SourceRef]:
        ...

    def fetch_security(self, ts_code: str) -> tuple[CompanyProfileRecord, SourceRef]:
        ...

    def fetch_quote(self, ts_code: str) -> tuple[QuoteRecord, SourceRef]:
        ...

    def fetch_financial(
        self, ts_code: str, *, limit: int = 8
    ) -> tuple[tuple[FinancialIndicatorRecord, SourceRef], ...]:
        ...

    def fetch_announcement(
        self, ts_code: str, *, limit: int = 20
    ) -> tuple[tuple[AnnouncementRecord, SourceRef], ...]:
        ...


class MarketDataProvider(Protocol):
    """Legacy Tushare-shaped provider still consumed by ``sync.py``.

    Providers fetch external market facts only. They must not resolve ShanHai
    entity identity, write knowledge, call Runtime, or produce trading signals.
    """

    def stock_basic(self, ts_codes: tuple[str, ...]) -> tuple[TushareStockBasicRecord, ...]:
        ...

    def daily(
        self,
        ts_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[TushareDailyRecord, ...]:
        ...


class FinancialDataProvider(Protocol):
    """Optional structured-financial capability.

    A provider may implement this in addition to MarketDataProvider. Sync only
    requests financial facts when the provider supports it.
    """

    def fina_indicator(
        self,
        ts_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[TushareFinaIndicatorRecord, ...]:
        ...


class AnnouncementDataProvider(Protocol):
    """Optional disclosed-announcement capability."""

    def anns_d(
        self,
        ts_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[TushareAnnouncementRecord, ...]:
        ...
