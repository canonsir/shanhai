"""A-share data synchronization for Milestone 2 MVP."""

from __future__ import annotations

from shanhai_market_data.domain.repository import MarketKnowledgeRepository
from shanhai_market_data.fact_mapper import (
    build_quote_fact,
    map_announcement,
    map_financial_indicator,
)
from shanhai_market_data.mapper import map_daily_quote, map_stock_basic
from shanhai_market_data.models import (
    AnnouncementFact,
    FinancialFact,
    MarketFact,
    SyncReport,
    SyncTarget,
)
from shanhai_market_data.provider import MarketDataProvider
from shanhai_market_data.resolver import EntityResolver

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
        repository: MarketKnowledgeRepository,
        *,
        resolver: EntityResolver | None = None,
    ) -> None:
        self._provider = provider
        self._store = repository
        self._resolver = resolver if resolver is not None else EntityResolver()

    def sync_companies(
        self,
        targets: tuple[SyncTarget, ...] = DEFAULT_A_SHARE_TARGETS,
        *,
        quote_start_date: str | None = None,
        quote_end_date: str | None = None,
        report_start_date: str | None = None,
        report_end_date: str | None = None,
    ) -> SyncReport:
        requested_codes = tuple(target.ts_code for target in targets)
        basics = self._provider.stock_basic(requested_codes)
        by_code = {item.ts_code: item for item in basics}
        company_ids = []
        market_fact_count = 0
        financial_fact_count = 0
        announcement_fact_count = 0

        for target in targets:
            record = by_code.get(target.ts_code)
            if record is None:
                continue
            company, listed_entity, security, listing, industry, facts = map_stock_basic(
                record, resolver=self._resolver
            )
            market_facts: list[MarketFact] = list(facts)

            quotes = self._provider.daily(
                target.ts_code,
                start_date=quote_start_date,
                end_date=quote_end_date,
            )
            latest_quote = None
            if quotes:
                latest = sorted(quotes, key=lambda item: item.trade_date)[-1]
                latest_quote = map_daily_quote(latest, resolver=self._resolver)
                market_facts.append(build_quote_fact(latest_quote, label=record.name))

            financial_facts = self._fetch_financial_facts(
                target.ts_code,
                security_id=security.security_id,
                label=record.name,
                start_date=report_start_date,
                end_date=report_end_date,
            )
            announcement_facts = self._fetch_announcement_facts(
                target.ts_code,
                company_id=company.company_id,
                label=record.name,
                start_date=report_start_date,
                end_date=report_end_date,
            )

            self._store.upsert_company_bundle(
                company=company,
                listed_entity=listed_entity,
                security=security,
                listing=listing,
                industry=industry,
                facts=tuple(market_facts),
                financial_facts=financial_facts,
                announcement_facts=announcement_facts,
            )
            if latest_quote is not None:
                self._store.upsert_quote(latest_quote)

            company_ids.append(company.company_id)
            market_fact_count += len(market_facts)
            financial_fact_count += len(financial_facts)
            announcement_fact_count += len(announcement_facts)

        missing = tuple(code for code in requested_codes if code not in by_code)
        return SyncReport(
            synced_count=len(company_ids),
            requested_count=len(requested_codes),
            company_ids=tuple(company_ids),
            missing_ts_codes=missing,
            market_fact_count=market_fact_count,
            financial_fact_count=financial_fact_count,
            announcement_fact_count=announcement_fact_count,
        )

    def _fetch_financial_facts(
        self,
        ts_code: str,
        *,
        security_id: str,
        label: str,
        start_date: str | None,
        end_date: str | None,
    ) -> tuple[FinancialFact, ...]:
        fetch = getattr(self._provider, "fina_indicator", None)
        if fetch is None:
            return ()
        records = fetch(ts_code, start_date=start_date, end_date=end_date)
        facts: list[FinancialFact] = []
        for record in records:
            facts.extend(
                map_financial_indicator(record, security_id=security_id, label=label)
            )
        return tuple(facts)

    def _fetch_announcement_facts(
        self,
        ts_code: str,
        *,
        company_id: str,
        label: str,
        start_date: str | None,
        end_date: str | None,
    ) -> tuple[AnnouncementFact, ...]:
        fetch = getattr(self._provider, "anns_d", None)
        if fetch is None:
            return ()
        records = fetch(ts_code, start_date=start_date, end_date=end_date)
        return tuple(
            map_announcement(record, company_id=company_id, label=label)
            for record in records
        )
