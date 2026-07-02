"""M3.2 Data Acquisition Foundation — offline provider + acquisition tests.

These drive the source-neutral public providers (EastMoney + CNInfo) and the
PublicDataAcquisitionService entirely offline through an injected fake transport,
so real network shapes are exercised without hitting live endpoints. The point
is to prove the spike closed loop: real-shaped provider response -> normalized
record -> mapper/fact_mapper -> store -> Company Intelligence, with each fact
carrying its own truthful SourceRef provenance.

Run:
PYTHONPATH=services/market-data:apps/api:. .venv/bin/python -m tests.market_data.test_public_providers
"""

from __future__ import annotations

import json

from shanhai_market_data import (
    CninfoAnnouncementProvider,
    CompanyIntelligenceAPI,
    EastMoneyProvider,
    InMemoryMarketKnowledgeStore,
    PublicDataAcquisitionService,
    SourceTrustLevel,
)

# --- canned real-shaped payloads ---------------------------------------------

_PUSH2 = {
    "data": {
        "f43": 119496,  # close * 100
        "f44": 120000,  # high * 100
        "f45": 118500,  # low * 100
        "f46": 119000,  # open * 100
        "f47": 31000,   # volume
        "f48": 3.7e9,   # amount
        "f57": "600519",
        "f58": "贵州茅台",
        "f60": 119000,  # prev_close * 100
        "f86": 1782000000,  # epoch seconds
        "f127": "白酒Ⅱ",
        "f128": "贵州板块",
        "f189": 20010827,  # list date yyyymmdd
    }
}

_F10 = {
    "result": {
        "data": [
            {
                "SECUCODE": "600519.SH",
                "SECURITY_CODE": "600519",
                "REPORT_DATE": "2026-03-31 00:00:00",
                "REPORT_TYPE": "一季报",
                "EPSJB": 21.76,
                "TOTALOPERATEREVE": 54702912385.23,
                "PARENTNETPROFIT": 27242512886.45,
                "ROEJQ": 10.57,
                "XSMLL": 89.76,
            },
            {
                "SECUCODE": "600519.SH",
                "SECURITY_CODE": "600519",
                "REPORT_DATE": "2025-12-31 00:00:00",
                "REPORT_TYPE": "年报",
                "EPSJB": 68.64,
                "TOTALOPERATEREVE": 172054171890.91,
                "PARENTNETPROFIT": 86228146421.62,
                "ROEJQ": 32.53,
                "XSMLL": 91.93,
            },
        ]
    }
}

_TOP_SEARCH = [
    {"code": "600519", "orgId": "gssh0600519", "zwjc": "贵州茅台"},
]

_HIS_ANN = {
    "announcements": [
        {
            "announcementId": "1225379934",
            "announcementTitle": "贵州茅台2025年年度权益分派实施公告",
            "announcementTime": 1782086400000,
            "adjunctUrl": "finalpage/2026-06-22/1225379934.PDF",
        },
        {
            "announcementId": "1225366265",
            "announcementTitle": "贵州茅台2025年度股东会决议公告",
            "announcementTime": 1781136000000,
            "adjunctUrl": "/finalpage/2026-06-12/1225366265.PDF",
        },
    ]
}


def _eastmoney_transport(method: str, url: str, *, data=None, headers=None, timeout=15.0):
    if "push2.eastmoney.com" in url:
        return 200, json.dumps(_PUSH2)
    if "datacenter.eastmoney.com" in url:
        return 200, json.dumps(_F10)
    raise AssertionError(f"unexpected eastmoney url: {url}")


def _cninfo_transport(method: str, url: str, *, data=None, headers=None, timeout=15.0):
    if "topSearch" in url:
        return 200, json.dumps(_TOP_SEARCH)
    if "hisAnnouncement" in url:
        return 200, json.dumps(_HIS_ANN)
    raise AssertionError(f"unexpected cninfo url: {url}")


def test_eastmoney_profile_quote_financial_offline() -> None:
    provider = EastMoneyProvider(transport=_eastmoney_transport)

    profile, profile_ref = provider.fetch_company_profile("600519.SH")
    assert profile.name == "贵州茅台"
    assert profile.symbol == "600519"
    assert profile.exchange.value == "SSE"
    assert profile.industry == "白酒Ⅱ"
    assert profile.list_date and profile.list_date.isoformat() == "2001-08-27"
    # Provenance travels from the network edge.
    assert profile_ref.provider == "eastmoney"
    assert profile_ref.dataset == "eastmoney.company_profile"
    assert profile_ref.trust_level is SourceTrustLevel.PUBLIC_AGGREGATOR
    assert profile_ref.hash and profile_ref.hash.startswith("sha256:")
    assert profile_ref.raw_snapshot_ref and profile_ref.raw_snapshot_ref.startswith("raw://")

    quote, quote_ref = provider.fetch_quote("600519.SH")
    assert quote.close == 1194.96  # 119496 / 100
    assert quote.open == 1190.0
    assert quote.pre_close == 1190.0
    assert quote_ref.dataset == "eastmoney.daily"

    rows = provider.fetch_financial("600519.SH")
    assert len(rows) == 2
    first, first_ref = rows[0]
    assert first.end_date.isoformat() == "2026-03-31"
    assert first.report_type_label == "一季报"
    assert first.roe == 10.57
    assert first.revenue == 54702912385.23
    assert first_ref.dataset == "eastmoney.f10_main_finance"
    print("[OK] EastMoney profile/quote/financial 离线解析 + provenance 通过")


def test_eastmoney_announcement_degrades() -> None:
    provider = EastMoneyProvider(transport=_eastmoney_transport)
    try:
        provider.fetch_announcement("600519.SH")
        assert False, "EastMoney 不覆盖公告，应抛 NotImplementedError"
    except NotImplementedError:
        pass
    print("[OK] EastMoney 不覆盖公告时优雅声明 NotImplementedError")


def test_cninfo_announcement_offline() -> None:
    provider = CninfoAnnouncementProvider(transport=_cninfo_transport)
    rows = provider.fetch_announcement("600519.SH")
    assert len(rows) == 2
    record, ref = rows[0]
    assert record.title == "贵州茅台2025年年度权益分派实施公告"
    assert record.ann_date.isoformat() == "2026-06-22"
    assert record.url == "http://static.cninfo.com.cn/finalpage/2026-06-22/1225379934.PDF"
    # Second one had a leading slash — must not double up the prefix.
    assert rows[1][0].url == "http://static.cninfo.com.cn/finalpage/2026-06-12/1225366265.PDF"
    assert ref.provider == "cninfo"
    assert ref.dataset == "cninfo.announcement"
    assert ref.trust_level is SourceTrustLevel.OFFICIAL
    print("[OK] CNInfo 公告离线解析 (两步 orgId + PDF 前缀) 通过")


def test_acquisition_closed_loop_offline() -> None:
    store = InMemoryMarketKnowledgeStore()
    service = PublicDataAcquisitionService(
        store,
        profile_provider=EastMoneyProvider(transport=_eastmoney_transport),
        announcement_provider=CninfoAnnouncementProvider(transport=_cninfo_transport),
    )
    report = service.acquire_company("600519.SH")

    assert report.name == "贵州茅台"
    assert report.has_quote is True
    assert report.financial_fact_count == 10  # 2 periods * 5 metrics
    assert report.announcement_fact_count == 2
    assert report.providers == ("eastmoney", "cninfo")
    # The external code is never an identity.
    assert "600519" not in report.company_id

    api = CompanyIntelligenceAPI(store)
    payload = api.get_company("600519.SH")
    assert payload is not None
    assert payload["industry"]["name"] == "白酒Ⅱ"
    assert payload["latest_quote"]["close"] == 1194.96

    # Different facts on the same company carry different, truthful provenance.
    fin_src = {f["source_ref"]["dataset"] for f in payload["financial_facts"]}
    assert fin_src == {"eastmoney.f10_main_finance"}
    ann_src = {f["source_ref"]["dataset"] for f in payload["announcement_facts"]}
    assert ann_src == {"cninfo.announcement"}
    src_datasets = {s["dataset"] for s in payload["source_refs"]}
    assert "eastmoney.daily" in src_datasets
    assert "cninfo.announcement" in src_datasets
    for s in payload["source_refs"]:
        assert s["hash"] and s["hash"].startswith("sha256:")
        assert s["raw_snapshot_ref"] and s["raw_snapshot_ref"].startswith("raw://")
    print("[OK] 公共数据采集闭环 (provider->mapper->store->API) 离线 + provenance 通过")


def main() -> None:
    test_eastmoney_profile_quote_financial_offline()
    test_eastmoney_announcement_degrades()
    test_cninfo_announcement_offline()
    test_acquisition_closed_loop_offline()
    print("\nM3.2 Data Acquisition Foundation 离线测试全部通过 ✅")


if __name__ == "__main__":
    main()
