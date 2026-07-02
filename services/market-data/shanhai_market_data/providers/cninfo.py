"""CNInfo (巨潮资讯) disclosed-announcement provider (free, no token).

CNInfo is the official A-share disclosure portal. Resolving announcements is a
two-step flow:

1. ``topSearch/query`` resolves a stock code to its ``orgId``.
2. ``hisAnnouncement/query`` lists disclosed announcements (title, date, PDF).

This provider only implements ``fetch_announcement``; quote / profile / financial
are served by other peers (e.g. EastMoney).
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from shanhai_market_data.models import (
    AnnouncementRecord,
    SourceRef,
    SourceTrustLevel,
)
from shanhai_market_data.providers._http import (
    Transport,
    content_hash,
    post_form_json,
    stdlib_transport,
)

_TOP_SEARCH_URL = "http://www.cninfo.com.cn/new/information/topSearch/query"
_HIS_ANN_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
_PDF_PREFIX = "http://static.cninfo.com.cn/"
_HEADERS = {"Referer": "http://www.cninfo.com.cn/"}

_PROVIDER = "cninfo"


class CninfoAnnouncementProvider:
    """Source-neutral CNInfo announcement adapter (a peer provider)."""

    name = _PROVIDER

    def __init__(self, *, transport: Transport | None = None, timeout: float = 15.0) -> None:
        self._transport = transport or stdlib_transport
        self._timeout = timeout

    def fetch_company_profile(self, ts_code: str):
        raise NotImplementedError("CNInfo provider only covers announcements.")

    def fetch_security(self, ts_code: str):
        raise NotImplementedError("CNInfo provider only covers announcements.")

    def fetch_quote(self, ts_code: str):
        raise NotImplementedError("CNInfo provider only covers announcements.")

    def fetch_financial(self, ts_code: str, *, limit: int = 8):
        raise NotImplementedError("CNInfo provider only covers announcements.")

    def fetch_announcement(
        self, ts_code: str, *, limit: int = 20
    ) -> tuple[tuple[AnnouncementRecord, SourceRef], ...]:
        org_id = self._resolve_org_id(ts_code)
        if org_id is None:
            return ()
        code = ts_code.split(".")[0]
        column = "sse" if ts_code.upper().endswith(".SH") else "szse"
        payload, raw = post_form_json(
            _HIS_ANN_URL,
            {
                "stock": f"{code},{org_id}",
                "tabName": "fulltext",
                "pageSize": str(limit),
                "pageNum": "1",
                "column": column,
                "category": "",
                "isHLtitle": "true",
            },
            transport=self._transport,
            headers=_HEADERS,
            timeout=self._timeout,
        )
        announcements = (payload or {}).get("announcements") or []
        out: list[tuple[AnnouncementRecord, SourceRef]] = []
        for item in announcements[:limit]:
            ann_date = _epoch_ms_to_date(item.get("announcementTime"))
            if ann_date is None:
                continue
            record = AnnouncementRecord(
                ts_code=ts_code,
                ann_date=ann_date,
                title=str(item.get("announcementTitle") or "").strip(),
                ann_type=None,
                url=_pdf_url(item.get("adjunctUrl")),
                content=str(item.get("announcementId") or "") or None,
            )
            out.append((record, self._source_ref(ts_code, raw)))
        return tuple(out)

    def _resolve_org_id(self, ts_code: str) -> str | None:
        code = ts_code.split(".")[0]
        payload, _ = post_form_json(
            _TOP_SEARCH_URL,
            {"keyWord": code, "maxNum": "10"},
            transport=self._transport,
            headers=_HEADERS,
            timeout=self._timeout,
        )
        if isinstance(payload, list):
            for hit in payload:
                if str(hit.get("code")) == code:
                    return hit.get("orgId")
            if payload:
                return payload[0].get("orgId")
        return None

    @staticmethod
    def _source_ref(ts_code: str, raw: str) -> SourceRef:
        captured_at = datetime.now(timezone.utc)
        ymd = captured_at.strftime("%Y%m%d")
        return SourceRef(
            source_id=_PROVIDER,
            source_name="巨潮资讯 CNInfo",
            trust_level=SourceTrustLevel.OFFICIAL,
            external_id=ts_code,
            captured_at=captured_at,
            provider=_PROVIDER,
            dataset=f"{_PROVIDER}.announcement",
            raw_snapshot_ref=f"raw://{_PROVIDER}/announcement/{ymd}/{ts_code}.json",
            version="v1",
            hash=content_hash(raw),
        )


def _pdf_url(adjunct_url) -> str | None:
    if not adjunct_url:
        return None
    return _PDF_PREFIX + str(adjunct_url).lstrip("/")


def _epoch_ms_to_date(value) -> date | None:
    if value in (None, "", 0, "0"):
        return None
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).date()
    except (TypeError, ValueError, OverflowError):
        return None
