"""Tushare Provider contract tests.

Run:
PYTHONPATH=services/market-data:. .venv/bin/python -m tests.market_data.test_tushare_provider
"""

from __future__ import annotations

from shanhai_market_data import TushareProvider


class _FakeTushareTransport:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __call__(self, url: str, payload: dict, timeout: float) -> dict:
        self.calls.append({"url": url, "payload": payload, "timeout": timeout})
        if payload["api_name"] == "stock_basic":
            return {
                "code": 0,
                "msg": None,
                "data": {
                    "fields": [
                        "ts_code",
                        "symbol",
                        "name",
                        "area",
                        "industry",
                        "market",
                        "list_date",
                        "exchange",
                        "list_status",
                    ],
                    "items": [
                        [
                            "600519.SH",
                            "600519",
                            "贵州茅台",
                            "贵州",
                            "白酒",
                            "主板",
                            "20010827",
                            "SSE",
                            "L",
                        ]
                    ],
                },
            }
        if payload["api_name"] == "daily":
            return {
                "code": 0,
                "msg": None,
                "data": {
                    "fields": [
                        "ts_code",
                        "trade_date",
                        "open",
                        "high",
                        "low",
                        "close",
                        "pre_close",
                        "vol",
                        "amount",
                    ],
                    "items": [
                        ["600519.SH", "20240626", 1500.0, 1510.0, 1490.0, 1505.0, 1498.0, 1.0, 2.0]
                    ],
                },
            }
        raise AssertionError(f"unexpected api_name: {payload['api_name']}")


def test_stock_basic_request_and_parse() -> None:
    fake = _FakeTushareTransport()
    provider = TushareProvider(token="token-test", transport=fake)

    records = provider.stock_basic(("600519.SH",))

    assert len(records) == 1
    record = records[0]
    assert record.ts_code == "600519.SH"
    assert record.name == "贵州茅台"
    assert record.exchange.value == "SSE"
    assert record.list_date and record.list_date.isoformat() == "2001-08-27"

    call = fake.calls[-1]
    assert call["payload"]["token"] == "token-test"
    assert call["payload"]["api_name"] == "stock_basic"
    print("[OK] Tushare stock_basic 请求与解析通过")


def test_daily_request_and_parse() -> None:
    fake = _FakeTushareTransport()
    provider = TushareProvider(token="token-test", transport=fake)

    records = provider.daily("600519.SH", start_date="20240601", end_date="20240626")

    assert len(records) == 1
    record = records[0]
    assert record.ts_code == "600519.SH"
    assert record.trade_date.isoformat() == "2024-06-26"
    assert record.close == 1505.0

    call = fake.calls[-1]
    assert call["payload"]["params"]["ts_code"] == "600519.SH"
    assert call["payload"]["params"]["start_date"] == "20240601"
    assert call["payload"]["params"]["end_date"] == "20240626"
    print("[OK] Tushare daily 请求与解析通过")


def test_missing_token_raises() -> None:
    provider = TushareProvider(token="", transport=_FakeTushareTransport())
    try:
        provider.stock_basic(("600519.SH",))
        assert False, "缺少 token 应抛错"
    except RuntimeError as exc:
        assert "SHANHAI_TUSHARE_TOKEN" in str(exc)
    print("[OK] Tushare 缺 token 明确报错通过")


def main() -> None:
    test_stock_basic_request_and_parse()
    test_daily_request_and_parse()
    test_missing_token_raises()
    print("\nTushare Provider 契约测试全部通过 ✅")


if __name__ == "__main__":
    main()
