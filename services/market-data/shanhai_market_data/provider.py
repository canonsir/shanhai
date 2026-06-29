"""Market data provider contracts."""

from __future__ import annotations

from typing import Protocol

from shanhai_market_data.models import (
    TushareAnnouncementRecord,
    TushareDailyRecord,
    TushareFinaIndicatorRecord,
    TushareStockBasicRecord,
)


class MarketDataProvider(Protocol):
    """Read-only market data provider.

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
