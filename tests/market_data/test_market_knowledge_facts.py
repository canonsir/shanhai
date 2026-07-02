"""M2.5 Phase 2 Market Knowledge Foundation tests.

Covers MarketFact v1 (profile / quote), FinancialFact (fina_indicator),
AnnouncementFact (anns_d), and the unified Company Knowledge Timeline read
model. The fakes here drive the schema from real ingestion shapes — facts must
be producible from provider rows, not hand-authored.

Run:
PYTHONPATH=services/market-data:apps/api:. .venv/bin/python -m tests.market_data.test_market_knowledge_facts
"""

from __future__ import annotations

from datetime import date

from shanhai_market_data import (
    AShareCompanySyncService,
    AnnouncementType,
    CompanyIntelligenceAPI,
    Exchange,
    FactType,
    InMemoryMarketKnowledgeStore,
    ListingStatus,
    SyncTarget,
    TimeBasis,
    TushareAnnouncementRecord,
    TushareDailyRecord,
    TushareFinaIndicatorRecord,
    TushareStockBasicRecord,
)

_MAOTAI = SyncTarget(ts_code="600519.SH", expected_name="贵州茅台")


class _FullProvider:
    """A fake provider that also implements the optional financial/announcement
    capabilities so the full Phase 2 chain can be exercised offline."""

    def stock_basic(self, ts_codes: tuple[str, ...]) -> tuple[TushareStockBasicRecord, ...]:
        return tuple(
            TushareStockBasicRecord(
                ts_code=ts_code,
                symbol=ts_code.split(".")[0],
                name="贵州茅台",
                area="贵州",
                industry="白酒",
                market="主板",
                list_date=date(2001, 8, 27),
                exchange=Exchange.SSE,
                list_status=ListingStatus.LISTED,
            )
            for ts_code in ts_codes
        )

    def daily(
        self,
        ts_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[TushareDailyRecord, ...]:
        return (
            TushareDailyRecord(
                ts_code=ts_code,
                trade_date=date(2026, 6, 26),
                open=1680.0,
                high=1700.0,
                low=1675.0,
                close=1695.0,
                pre_close=1682.0,
                vol=30000.0,
                amount=5_000_000.0,
            ),
        )

    def fina_indicator(
        self,
        ts_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[TushareFinaIndicatorRecord, ...]:
        return (
            TushareFinaIndicatorRecord(
                ts_code=ts_code,
                end_date=date(2025, 12, 31),
                ann_date=date(2026, 3, 28),
                revenue=170_000_000_000.0,
                netprofit=85_000_000_000.0,
                roe=32.5,
                eps=67.8,
                grossprofit_margin=91.5,
                or_yoy=15.0,
                netprofit_yoy=17.0,
            ),
        )

    def anns_d(
        self,
        ts_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[TushareAnnouncementRecord, ...]:
        return (
            TushareAnnouncementRecord(
                ts_code=ts_code,
                ann_date=date(2026, 3, 28),
                title="2025年年度报告",
                ann_type="定期报告",
                url="https://example.com/600519/annual-2025.pdf",
                content="贵州茅台 2025 年度报告全文……",
            ),
            TushareAnnouncementRecord(
                ts_code=ts_code,
                ann_date=date(2026, 5, 10),
                title="关于2024年度利润分配方案的公告",
                ann_type="分红",
                url="https://example.com/600519/dividend-2025.pdf",
                content=None,
            ),
        )


class _BasicOnlyProvider:
    """Implements only the mandatory MarketDataProvider surface (no optional
    financial/announcement capability)."""

    def stock_basic(self, ts_codes: tuple[str, ...]) -> tuple[TushareStockBasicRecord, ...]:
        return _FullProvider().stock_basic(ts_codes)

    def daily(
        self,
        ts_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[TushareDailyRecord, ...]:
        return _FullProvider().daily(ts_code)


def _synced_store(provider) -> InMemoryMarketKnowledgeStore:
    store = InMemoryMarketKnowledgeStore()
    service = AShareCompanySyncService(provider, store)
    report = service.sync_companies((_MAOTAI,))
    assert report.synced_count == 1
    return store, report


def test_market_fact_v1_from_sync() -> None:
    store, report = _synced_store(_FullProvider())
    item = store.get_company_intelligence_by_ts_code("600519.SH")
    assert item is not None

    fact_types = {fact.fact_type for fact in item.facts}
    assert FactType.PROFILE in fact_types
    assert FactType.INDUSTRY in fact_types
    assert FactType.QUOTE in fact_types

    industry_fact = next(f for f in item.facts if f.fact_type is FactType.INDUSTRY)
    assert industry_fact.predicate == "classified_in_industry"
    assert industry_fact.object_value == "白酒"
    # The external code is never an identity on a fact subject.
    assert "600519" not in industry_fact.subject_ref.entity_id
    assert industry_fact.subject_ref.entity_id == item.company.company_id
    assert industry_fact.schema_version == "market_fact.v1"

    quote_fact = next(f for f in item.facts if f.fact_type is FactType.QUOTE)
    assert quote_fact.predicate == "closing_price"
    assert quote_fact.object_value == "1695"
    attr_keys = {a.key for a in quote_fact.attributes}
    assert {"open", "high", "low", "close", "volume"} <= attr_keys

    assert report.market_fact_count >= 3
    print("[OK] MarketFact v1 由 sync 真实派生 (profile/industry/quote)")


def test_financial_fact_via_fina_indicator() -> None:
    store, report = _synced_store(_FullProvider())
    item = store.get_company_intelligence_by_ts_code("600519.SH")
    assert item is not None

    metrics = {f.metric_name: f for f in item.financial_facts}
    assert {"revenue", "net_profit", "roe", "eps", "gross_margin"} <= set(metrics)
    revenue = metrics["revenue"]
    assert revenue.report_period == "2025Q4"
    assert revenue.report_type == "fina_indicator"
    assert revenue.yoy == 15.0
    assert revenue.schema_version == "financial_fact.v1"
    # Subject points at the surrogate security id, not the external code.
    assert "600519" not in revenue.subject_ref.entity_id
    assert revenue.subject_ref.entity_id == item.security.security_id
    assert report.financial_fact_count == 5
    print("[OK] FinancialFact 由 fina_indicator 拆分为多指标事实")


def test_announcement_fact_via_anns_d() -> None:
    store, report = _synced_store(_FullProvider())
    item = store.get_company_intelligence_by_ts_code("600519.SH")
    assert item is not None

    assert report.announcement_fact_count == 2
    by_type = {f.announcement_type for f in item.announcement_facts}
    assert AnnouncementType.PERIODIC_REPORT in by_type
    assert AnnouncementType.DIVIDEND in by_type

    annual = next(
        f for f in item.announcement_facts
        if f.announcement_type is AnnouncementType.PERIODIC_REPORT
    )
    assert annual.title == "2025年年度报告"
    assert annual.document_url.endswith("annual-2025.pdf")
    assert annual.document_hash  # content present -> hashed
    assert "600519" not in annual.subject_ref.entity_id
    assert annual.subject_ref.entity_id == item.company.company_id
    assert annual.schema_version == "announcement_fact.v1"
    print("[OK] AnnouncementFact 由 anns_d 派生并启发式分类")


def test_timeline_unifies_all_fact_families_and_orders() -> None:
    store, _ = _synced_store(_FullProvider())
    item = store.get_company_intelligence_by_ts_code("600519.SH")
    assert item is not None

    event_types = {event.event_type for event in item.timeline}
    # Generic + financial + announcement facts all reach one timeline.
    assert FactType.FINANCIAL in event_types
    assert FactType.ANNOUNCEMENT in event_types
    assert FactType.QUOTE in event_types

    # Default ordering = published_at, latest first.
    times = [event.event_time for event in item.timeline]
    assert times == sorted(times, reverse=True)
    # Every event references the fact it was projected from (read model, not source).
    for event in item.timeline:
        assert event.fact_refs
        assert event.event_id.startswith("event:")

    # Switching ordering basis and direction works without collapsing timestamps.
    asc = store.get_company_timeline(
        "600519.SH", time_basis=TimeBasis.OCCURRED_AT, latest_first=False
    )
    asc_times = [event.event_time for event in asc]
    assert asc_times == sorted(asc_times)
    print("[OK] Timeline 统一三类事实并支持基准/方向切换")


def test_optional_capability_absent_yields_no_financial_or_announcement() -> None:
    store, report = _synced_store(_BasicOnlyProvider())
    item = store.get_company_intelligence_by_ts_code("600519.SH")
    assert item is not None

    # No fina_indicator / anns_d capability -> no financial/announcement facts,
    # but profile/quote MarketFacts and a timeline still exist.
    assert item.financial_facts == ()
    assert item.announcement_facts == ()
    assert report.financial_fact_count == 0
    assert report.announcement_fact_count == 0
    assert item.facts
    assert item.timeline
    print("[OK] 缺少可选能力时优雅降级 (仅 MarketFact + timeline)")


def test_api_payload_and_timeline_endpoint_surface() -> None:
    store, _ = _synced_store(_FullProvider())
    api = CompanyIntelligenceAPI(store)

    payload = api.get_company("600519.SH")
    assert payload is not None
    assert payload["financial_facts"]
    assert payload["announcement_facts"]
    assert payload["timeline"]

    timeline = api.get_company_timeline("600519.SH")
    assert timeline is not None
    assert timeline["time_basis"] == "published_at"
    assert timeline["events"]
    assert api.get_company_timeline("UNKNOWN.SH") is None
    print("[OK] Company Intelligence API 暴露 facts/timeline payload")


def main() -> None:
    test_market_fact_v1_from_sync()
    test_financial_fact_via_fina_indicator()
    test_announcement_fact_via_anns_d()
    test_timeline_unifies_all_fact_families_and_orders()
    test_optional_capability_absent_yields_no_financial_or_announcement()
    test_api_payload_and_timeline_endpoint_surface()
    print("\nMarket Knowledge Foundation (Phase 2) 测试全部通过 ✅")


if __name__ == "__main__":
    main()
