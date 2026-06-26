"""Market data provider contracts."""

from __future__ import annotations

from typing import Protocol

from shanhai_market_data.models import TushareDailyRecord, TushareStockBasicRecord


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
