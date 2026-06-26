"""Tushare provider for A-share market facts.

The provider uses stdlib HTTP and supports an injected transport for tests. It
does not require Tushare at import time and does not perform network calls in
tests unless a caller explicitly supplies the default transport with a token.
"""

from __future__ import annotations

import json
import os
import urllib.request
from collections.abc import Callable
from datetime import date
from typing import Any

from shanhai_market_data.models import (
    Exchange,
    ListingStatus,
    TushareDailyRecord,
    TushareRequest,
    TushareResponse,
    TushareStockBasicRecord,
)

Transport = Callable[[str, dict[str, Any], float], dict[str, Any]]

TUSHARE_URL = "https://api.tushare.pro"


def _default_transport(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


class TushareProvider:
    """Read-only Tushare provider.

    Token comes from `SHANHAI_TUSHARE_TOKEN` by default. The provider returns
    typed records and keeps entity resolution outside the provider boundary.
    """

    def __init__(
        self,
        token: str | None = None,
        *,
        transport: Transport | None = None,
        endpoint: str = TUSHARE_URL,
        timeout: float = 10.0,
    ) -> None:
        self._token = token if token is not None else os.getenv("SHANHAI_TUSHARE_TOKEN", "")
        self._transport = transport or _default_transport
        self._endpoint = endpoint
        self._timeout = timeout

    def stock_basic(self, ts_codes: tuple[str, ...]) -> tuple[TushareStockBasicRecord, ...]:
        params: dict[str, Any] = {"list_status": "L"}
        fields = "ts_code,symbol,name,area,industry,market,list_date,exchange,list_status"
        rows = self._call("stock_basic", params=params, fields=fields)
        wanted = set(ts_codes)
        records = [
            self._stock_basic_record(row)
            for row in rows
            if not wanted or str(row.get("ts_code", "")) in wanted
        ]
        return tuple(records)

    def daily(
        self,
        ts_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[TushareDailyRecord, ...]:
        params: dict[str, Any] = {"ts_code": ts_code}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        fields = "ts_code,trade_date,open,high,low,close,pre_close,vol,amount"
        rows = self._call("daily", params=params, fields=fields)
        return tuple(self._daily_record(row) for row in rows)

    def _call(
        self,
        api_name: str,
        *,
        params: dict[str, Any],
        fields: str,
    ) -> list[dict[str, Any]]:
        if not self._token:
            raise RuntimeError("Missing SHANHAI_TUSHARE_TOKEN for TushareProvider")
        request = TushareRequest(
            api_name=api_name,
            token=self._token,
            params=params,
            fields=fields,
        )
        raw = self._transport(self._endpoint, request.model_dump(), self._timeout)
        response = self._parse_response(raw)
        if response.code != 0:
            raise RuntimeError(f"Tushare API error: code={response.code}, msg={response.msg}")
        return [dict(zip(response.fields, item, strict=True)) for item in response.items]

    @staticmethod
    def _parse_response(raw: dict[str, Any]) -> TushareResponse:
        data = raw.get("data") or {}
        return TushareResponse(
            code=int(raw.get("code", -1)),
            msg=raw.get("msg"),
            fields=tuple(data.get("fields") or ()),
            items=tuple(tuple(item) for item in data.get("items") or ()),
        )

    @staticmethod
    def _stock_basic_record(row: dict[str, Any]) -> TushareStockBasicRecord:
        return TushareStockBasicRecord(
            ts_code=str(row["ts_code"]),
            symbol=str(row["symbol"]),
            name=str(row["name"]),
            area=row.get("area"),
            industry=row.get("industry"),
            market=row.get("market"),
            list_date=_parse_yyyymmdd(row.get("list_date")),
            exchange=_exchange_from_ts_code(str(row["ts_code"])),
            list_status=_listing_status(row.get("list_status")),
        )

    @staticmethod
    def _daily_record(row: dict[str, Any]) -> TushareDailyRecord:
        return TushareDailyRecord(
            ts_code=str(row["ts_code"]),
            trade_date=_parse_yyyymmdd(row.get("trade_date")) or date.min,
            open=_float_or_none(row.get("open")),
            high=_float_or_none(row.get("high")),
            low=_float_or_none(row.get("low")),
            close=_float_or_none(row.get("close")),
            pre_close=_float_or_none(row.get("pre_close")),
            vol=_float_or_none(row.get("vol")),
            amount=_float_or_none(row.get("amount")),
        )


def _parse_yyyymmdd(value: Any) -> date | None:
    if value in (None, ""):
        return None
    text = str(value)
    return date(int(text[0:4]), int(text[4:6]), int(text[6:8]))


def _float_or_none(value: Any) -> float | None:
    return None if value in (None, "") else float(value)


def _exchange_from_ts_code(ts_code: str) -> Exchange:
    suffix = ts_code.split(".")[-1].upper()
    if suffix == "SH":
        return Exchange.SSE
    if suffix == "SZ":
        return Exchange.SZSE
    if suffix == "BJ":
        return Exchange.BSE
    raise ValueError(f"Unsupported Tushare exchange suffix: {ts_code}")


def _listing_status(value: Any) -> ListingStatus:
    if value == "L":
        return ListingStatus.LISTED
    if value == "D":
        return ListingStatus.DELISTED
    if value == "P":
        return ListingStatus.SUSPENDED
    return ListingStatus.UNKNOWN
