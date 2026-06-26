"""Milestone 2 Data Foundation MVP tests.

Run:
PYTHONPATH=services/market-data:. .venv/bin/python -m tests.market_data.test_data_foundation_mvp
"""

from __future__ import annotations

from datetime import date

from shanhai_market_data import (
    AShareCompanySyncService,
    CompanyIntelligenceAPI,
    DEFAULT_A_SHARE_TARGETS,
    Exchange,
    InMemoryMarketKnowledgeStore,
    ListingStatus,
    TushareDailyRecord,
    TushareStockBasicRecord,
)


class _FakeMarketDataProvider:
    _names = {
        "600519.SH": ("600519", "贵州茅台", "贵州", "白酒", "主板", Exchange.SSE, date(2001, 8, 27)),
        "300750.SZ": ("300750", "宁德时代", "福建", "电池", "创业板", Exchange.SZSE, date(2018, 6, 11)),
        "002594.SZ": ("002594", "比亚迪", "广东", "汽车", "中小板", Exchange.SZSE, date(2011, 6, 30)),
        "000001.SZ": ("000001", "平安银行", "深圳", "银行", "主板", Exchange.SZSE, date(1991, 4, 3)),
        "600036.SH": ("600036", "招商银行", "深圳", "银行", "主板", Exchange.SSE, date(2002, 4, 9)),
        "601318.SH": ("601318", "中国平安", "深圳", "保险", "主板", Exchange.SSE, date(2007, 3, 1)),
        "000858.SZ": ("000858", "五粮液", "四川", "白酒", "主板", Exchange.SZSE, date(1998, 4, 27)),
        "601012.SH": ("601012", "隆基绿能", "陕西", "光伏", "主板", Exchange.SSE, date(2012, 4, 11)),
        "000333.SZ": ("000333", "美的集团", "广东", "家电", "主板", Exchange.SZSE, date(2013, 9, 18)),
        "688981.SH": ("688981", "中芯国际", "上海", "半导体", "科创板", Exchange.SSE, date(2020, 7, 16)),
    }

    def stock_basic(self, ts_codes: tuple[str, ...]) -> tuple[TushareStockBasicRecord, ...]:
        records = []
        for ts_code in ts_codes:
            symbol, name, area, industry, market, exchange, list_date = self._names[ts_code]
            records.append(
                TushareStockBasicRecord(
                    ts_code=ts_code,
                    symbol=symbol,
                    name=name,
                    area=area,
                    industry=industry,
                    market=market,
                    list_date=list_date,
                    exchange=exchange,
                    list_status=ListingStatus.LISTED,
                )
            )
        return tuple(records)

    def daily(
        self,
        ts_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[TushareDailyRecord, ...]:
        return (
            TushareDailyRecord(
                ts_code=ts_code,
                trade_date=date(2024, 6, 26),
                open=10.0,
                high=11.0,
                low=9.5,
                close=10.5,
                pre_close=10.0,
                vol=100.0,
                amount=1000.0,
            ),
        )


def _synced_store() -> InMemoryMarketKnowledgeStore:
    store = InMemoryMarketKnowledgeStore()
    service = AShareCompanySyncService(_FakeMarketDataProvider(), store)
    report = service.sync_companies(DEFAULT_A_SHARE_TARGETS)

    assert report.requested_count == 10
    assert report.synced_count == 10
    assert report.missing_ts_codes == ()
    return store


def test_sync_ten_a_share_companies() -> None:
    store = _synced_store()

    maotai = store.get_company_intelligence_by_ts_code("600519.SH")
    catl = store.get_company_intelligence_by_ts_code("300750.SZ")

    assert maotai is not None
    assert catl is not None
    assert maotai.company.name == "贵州茅台"
    assert catl.company.name == "宁德时代"
    assert maotai.company.company_id != maotai.security.security_id
    assert maotai.listed_entity.company_id == maotai.company.company_id
    assert maotai.security.listed_entity_id == maotai.listed_entity.listed_entity_id
    assert maotai.latest_quote is not None
    print("[OK] 贵州茅台/宁德时代等 10 家公司同步闭环通过")


def test_company_intelligence_api() -> None:
    store = _synced_store()
    api = CompanyIntelligenceAPI(store)

    payload = api.get_company("600519.SH")
    assert payload is not None
    assert payload["company"]["name"] == "贵州茅台"
    assert payload["security"]["ts_code"] == "600519.SH"
    assert payload["industry"]["name"] == "白酒"
    assert payload["latest_quote"]["close"] == 10.5

    search = api.search_companies("宁德")
    assert len(search) == 1
    assert search[0]["company"]["name"] == "宁德时代"

    listed = api.list_companies()
    assert len(listed) == 10
    print("[OK] Company Intelligence API 查询通过")


def test_market_entity_schema_does_not_collapse_identity() -> None:
    store = _synced_store()
    item = store.get_company_intelligence_by_ts_code("002594.SZ")
    assert item is not None

    ids = {
        item.company.company_id,
        item.listed_entity.listed_entity_id,
        item.security.security_id,
        item.listing.listing_id,
    }
    assert len(ids) == 4
    assert item.security.ts_code == "002594.SZ"
    assert item.company.company_id != item.security.ts_code
    print("[OK] Company / ListedEntity / Security / Listing 身份未塌缩")


def main() -> None:
    test_sync_ten_a_share_companies()
    test_company_intelligence_api()
    test_market_entity_schema_does_not_collapse_identity()
    print("\nMarket Data Foundation MVP 测试全部通过 ✅")


if __name__ == "__main__":
    main()
