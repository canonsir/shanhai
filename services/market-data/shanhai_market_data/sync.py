"""A-share data synchronization for Milestone 2 MVP."""

from __future__ import annotations

from shanhai_market_data.mapper import map_daily_quote, map_stock_basic
from shanhai_market_data.models import SyncReport, SyncTarget
from shanhai_market_data.provider import MarketDataProvider
from shanhai_market_data.store import InMemoryMarketKnowledgeStore

DEFAULT_A_SHARE_TARGETS: tuple[SyncTarget, ...] = (
    SyncTarget(ts_code="600519.SH", expected_name="贵州茅台"),
    SyncTarget(ts_code="300750.SZ", expected_name="宁德时代"),
    SyncTarget(ts_code="002594.SZ", expected_name="比亚迪"),
    SyncTarget(ts_code="000001.SZ", expected_name="平安银行"),
    SyncTarget(ts_code="600036.SH", expected_name="招商银行"),
    SyncTarget(ts_code="601318.SH", expected_name="中国平安"),
    SyncTarget(ts_code="000858.SZ", expected_name="五粮液"),
    SyncTarget(ts_code="601012.SH", expected_name="隆基绿能"),
    SyncTarget(ts_code="000333.SZ", expected_name="美的集团"),
    SyncTarget(ts_code="688981.SH", expected_name="中芯国际"),
)


class AShareCompanySyncService:
    """Synchronize selected A-share company facts into Market Knowledge Store."""

    def __init__(
        self,
        provider: MarketDataProvider,
        store: InMemoryMarketKnowledgeStore,
    ) -> None:
        self._provider = provider
        self._store = store

    def sync_companies(
        self,
        targets: tuple[SyncTarget, ...] = DEFAULT_A_SHARE_TARGETS,
        *,
        quote_start_date: str | None = None,
        quote_end_date: str | None = None,
    ) -> SyncReport:
        requested_codes = tuple(target.ts_code for target in targets)
        basics = self._provider.stock_basic(requested_codes)
        by_code = {item.ts_code: item for item in basics}
        company_ids = []

        for target in targets:
            record = by_code.get(target.ts_code)
            if record is None:
                continue
            company, listed_entity, security, listing, industry, facts = map_stock_basic(record)
            self._store.upsert_company_bundle(
                company=company,
                listed_entity=listed_entity,
                security=security,
                listing=listing,
                industry=industry,
                facts=facts,
            )
            company_ids.append(company.company_id)
            quotes = self._provider.daily(
                target.ts_code,
                start_date=quote_start_date,
                end_date=quote_end_date,
            )
            if quotes:
                latest = sorted(quotes, key=lambda item: item.trade_date)[-1]
                self._store.upsert_quote(map_daily_quote(latest))

        missing = tuple(code for code in requested_codes if code not in by_code)
        return SyncReport(
            synced_count=len(company_ids),
            requested_count=len(requested_codes),
            company_ids=tuple(company_ids),
            missing_ts_codes=missing,
        )
