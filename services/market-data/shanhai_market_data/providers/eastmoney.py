"""EastMoney public market data provider (free, no token).

Covers profile / security / quote / financial via EastMoney's public web APIs:

- quote + profile: ``push2.eastmoney.com/api/qt/stock/get`` (real-time snapshot,
  industry, list date).
- financial: ``datacenter.eastmoney.com`` F10 ``RPT_F10_FINANCE_MAINFINADATA``
  (per-period main financial indicators).

EastMoney does not expose a clean disclosed-announcement feed, so
``fetch_announcement`` is left to the CNInfo provider. This is exactly why the
data layer is multi-provider: no single free source covers everything.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from shanhai_market_data.models import (
    CompanyProfileRecord,
    Exchange,
    FinancialIndicatorRecord,
    ListingStatus,
    QuoteRecord,
    SourceRef,
    SourceTrustLevel,
)
from shanhai_market_data.providers._http import (
    Transport,
    content_hash,
    get_json,
    secid_for,
    stdlib_transport,
)

_PUSH2_URL = "https://push2.eastmoney.com/api/qt/stock/get"
_QUOTE_FIELDS = "f43,f44,f45,f46,f47,f48,f57,f58,f60,f86,f127,f128,f189"
_DATACENTER_URL = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
_F10_COLUMNS = (
    "SECUCODE,SECURITY_CODE,REPORT_DATE,REPORT_TYPE,"
    "EPSJB,TOTALOPERATEREVE,PARENTNETPROFIT,ROEJQ,XSMLL"
)
_DATACENTER_HEADERS = {"Referer": "https://emweb.securities.eastmoney.com/"}

_PROVIDER = "eastmoney"


class EastMoneyProvider:
    """Source-neutral EastMoney adapter (a peer of every other provider)."""

    name = _PROVIDER

    def __init__(self, *, transport: Transport | None = None, timeout: float = 15.0) -> None:
        self._transport = transport or stdlib_transport
        self._timeout = timeout

    # --- profile / security -------------------------------------------------

    def fetch_company_profile(self, ts_code: str) -> tuple[CompanyProfileRecord, SourceRef]:
        payload, raw = self._stock_get(ts_code)
        data = payload.get("data") or {}
        record = CompanyProfileRecord(
            ts_code=ts_code,
            symbol=str(data.get("f57") or ts_code.split(".")[0]),
            name=str(data.get("f58") or ""),
            exchange=_exchange_from_ts_code(ts_code),
            industry=_clean(data.get("f127")),
            list_date=_parse_yyyymmdd(data.get("f189")),
            list_status=ListingStatus.LISTED,
        )
        return record, self._source_ref(ts_code, "company_profile", raw)

    def fetch_security(self, ts_code: str) -> tuple[CompanyProfileRecord, SourceRef]:
        # Security identity is carried on the same snapshot as the profile.
        record, ref = self.fetch_company_profile(ts_code)
        return record, ref.model_copy(update={"dataset": f"{_PROVIDER}.security"})

    # --- quote --------------------------------------------------------------

    def fetch_quote(self, ts_code: str) -> tuple[QuoteRecord, SourceRef]:
        payload, raw = self._stock_get(ts_code)
        data = payload.get("data") or {}
        record = QuoteRecord(
            ts_code=ts_code,
            trade_date=_quote_date(data.get("f86")),
            open=_price(data.get("f46")),
            high=_price(data.get("f44")),
            low=_price(data.get("f45")),
            close=_price(data.get("f43")),
            pre_close=_price(data.get("f60")),
            vol=_float_or_none(data.get("f47")),
            amount=_float_or_none(data.get("f48")),
        )
        return record, self._source_ref(ts_code, "daily", raw)

    # --- financial ----------------------------------------------------------

    def fetch_financial(
        self, ts_code: str, *, limit: int = 8
    ) -> tuple[tuple[FinancialIndicatorRecord, SourceRef], ...]:
        secucode = ts_code.upper()
        url = (
            f"{_DATACENTER_URL}?reportName=RPT_F10_FINANCE_MAINFINADATA"
            f"&columns={_F10_COLUMNS}"
            f"&filter=(SECUCODE=%22{secucode}%22)"
            f"&pageNumber=1&pageSize={limit}"
            f"&sortColumns=REPORT_DATE&sortTypes=-1&source=HSF10&client=PC"
        )
        payload, raw = get_json(
            url, transport=self._transport, headers=_DATACENTER_HEADERS, timeout=self._timeout
        )
        result = payload.get("result") or {}
        rows = result.get("data") or []
        out: list[tuple[FinancialIndicatorRecord, SourceRef]] = []
        for row in rows:
            end_date = _parse_iso_date(row.get("REPORT_DATE"))
            if end_date is None:
                continue
            record = FinancialIndicatorRecord(
                ts_code=ts_code,
                end_date=end_date,
                report_type_label=_clean(row.get("REPORT_TYPE")),
                revenue=_float_or_none(row.get("TOTALOPERATEREVE")),
                netprofit=_float_or_none(row.get("PARENTNETPROFIT")),
                roe=_float_or_none(row.get("ROEJQ")),
                eps=_float_or_none(row.get("EPSJB")),
                grossprofit_margin=_float_or_none(row.get("XSMLL")),
            )
            out.append((record, self._source_ref(ts_code, "f10_main_finance", raw)))
        return tuple(out)

    def fetch_announcement(self, ts_code: str, *, limit: int = 20):
        raise NotImplementedError(
            "EastMoney provider does not cover disclosed announcements; "
            "use the CNInfo provider."
        )

    # --- internals ----------------------------------------------------------

    def _stock_get(self, ts_code: str):
        url = f"{_PUSH2_URL}?secid={secid_for(ts_code)}&fields={_QUOTE_FIELDS}"
        return get_json(url, transport=self._transport, timeout=self._timeout)

    @staticmethod
    def _source_ref(ts_code: str, dataset: str, raw: str) -> SourceRef:
        captured_at = datetime.now(timezone.utc)
        ymd = captured_at.strftime("%Y%m%d")
        return SourceRef(
            source_id=_PROVIDER,
            source_name="东方财富 EastMoney",
            trust_level=SourceTrustLevel.PUBLIC_AGGREGATOR,
            external_id=ts_code,
            captured_at=captured_at,
            provider=_PROVIDER,
            dataset=f"{_PROVIDER}.{dataset}",
            raw_snapshot_ref=f"raw://{_PROVIDER}/{dataset}/{ymd}/{ts_code}.json",
            version="v1",
            hash=content_hash(raw),
        )


def _exchange_from_ts_code(ts_code: str) -> Exchange:
    suffix = ts_code.split(".")[-1].upper()
    if suffix == "SH":
        return Exchange.SSE
    if suffix == "SZ":
        return Exchange.SZSE
    if suffix == "BJ":
        return Exchange.BSE
    raise ValueError(f"Unsupported exchange suffix: {ts_code}")


def _price(value) -> float | None:
    """EastMoney returns prices scaled by 100 (integer fen)."""
    if value in (None, "", "-"):
        return None
    return round(float(value) / 100.0, 4)


def _float_or_none(value) -> float | None:
    if value in (None, "", "-"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clean(value) -> str | None:
    if value in (None, "", "-"):
        return None
    return str(value).strip() or None


def _parse_yyyymmdd(value) -> date | None:
    if value in (None, "", 0, "0"):
        return None
    text = str(value)
    if len(text) != 8:
        return None
    return date(int(text[0:4]), int(text[4:6]), int(text[6:8]))


def _parse_iso_date(value) -> date | None:
    if not value:
        return None
    text = str(value)[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _quote_date(epoch_seconds) -> date:
    if epoch_seconds in (None, "", 0, "0"):
        return datetime.now(timezone.utc).date()
    return datetime.fromtimestamp(int(epoch_seconds), tz=timezone.utc).date()
