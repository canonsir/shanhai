"""Map provider records into Market Knowledge facts (MarketFact v1 family).

Facts are the cognition layer over raw provider records. Profile / industry /
quote facts use the generic ``MarketFact``; structured financials and
disclosed announcements use their own sibling models. Nothing here resolves
identity (that stays in the resolver) and nothing here emits trading signals.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone

from shanhai_market_data.models import (
    AnnouncementFact,
    AnnouncementType,
    FactAttribute,
    FactType,
    FinancialFact,
    MarketFact,
    QuoteSnapshot,
    ResolvedMarketIdentity,
    SourceRef,
    SourceTrustLevel,
    SubjectRef,
    TushareAnnouncementRecord,
    TushareFinaIndicatorRecord,
    TushareStockBasicRecord,
)

TUSHARE_SOURCE_REF = SourceRef(
    source_id="tushare",
    source_name="Tushare",
    trust_level=SourceTrustLevel.LICENSED_AGGREGATOR,
)

_FINANCIAL_METRICS: tuple[tuple[str, str, str, str], ...] = (
    # (record attribute, metric_name, unit, yoy attribute)
    ("revenue", "revenue", "CNY", "or_yoy"),
    ("netprofit", "net_profit", "CNY", "netprofit_yoy"),
    ("roe", "roe", "percent", ""),
    ("eps", "eps", "CNY_per_share", ""),
    ("grossprofit_margin", "gross_margin", "percent", ""),
)


def build_company_profile_facts(
    record: TushareStockBasicRecord,
    identity: ResolvedMarketIdentity,
    *,
    source_ref: SourceRef = TUSHARE_SOURCE_REF,
) -> tuple[MarketFact, ...]:
    """Derive descriptive company facts (region / industry / listing date)."""
    company_id = identity.company_id
    subject = SubjectRef(entity_type="company", entity_id=company_id, label=record.name)
    facts: list[MarketFact] = []

    if record.area:
        facts.append(
            MarketFact(
                fact_id=f"fact:{company_id}:profile:region",
                fact_type=FactType.PROFILE,
                subject_ref=subject,
                predicate="located_in_region",
                object_value=record.area,
                source_ref=source_ref,
            )
        )
    if record.industry:
        facts.append(
            MarketFact(
                fact_id=f"fact:{company_id}:industry:tushare",
                fact_type=FactType.INDUSTRY,
                subject_ref=subject,
                predicate="classified_in_industry",
                object_value=record.industry,
                source_ref=source_ref,
            )
        )
    if record.list_date is not None:
        listed_at = _to_datetime(record.list_date)
        facts.append(
            MarketFact(
                fact_id=f"fact:{company_id}:profile:listing",
                fact_type=FactType.PROFILE,
                subject_ref=subject,
                predicate="listed_on_exchange",
                object_value=record.exchange.value,
                occurred_at=listed_at,
                published_at=listed_at,
                source_ref=source_ref,
            )
        )
    return tuple(facts)


def build_quote_fact(
    quote: QuoteSnapshot,
    *,
    label: str | None = None,
) -> MarketFact:
    """Project the latest QuoteSnapshot into a dated QUOTE fact."""
    subject = SubjectRef(entity_type="security", entity_id=quote.security_id, label=label)
    traded_at = _to_datetime(quote.trade_date)
    attributes = tuple(
        FactAttribute(key=key, value=_num_text(value))
        for key, value in (
            ("open", quote.open),
            ("high", quote.high),
            ("low", quote.low),
            ("close", quote.close),
            ("previous_close", quote.previous_close),
            ("volume", quote.volume),
            ("amount", quote.amount),
        )
        if value is not None
    )
    return MarketFact(
        fact_id=f"fact:{quote.security_id}:quote:{quote.trade_date.isoformat()}",
        fact_type=FactType.QUOTE,
        subject_ref=subject,
        predicate="closing_price",
        object_value=_num_text(quote.close),
        occurred_at=traded_at,
        published_at=traded_at,
        source_ref=quote.source_ref,
        attributes=attributes,
    )


def map_financial_indicator(
    record: TushareFinaIndicatorRecord,
    *,
    security_id: str,
    label: str | None = None,
    source_ref: SourceRef = TUSHARE_SOURCE_REF,
) -> tuple[FinancialFact, ...]:
    """Split a fina_indicator row into one FinancialFact per disclosed metric."""
    subject = SubjectRef(entity_type="security", entity_id=security_id, label=label)
    report_period = _report_period(record.end_date)
    occurred_at = _to_datetime(record.end_date)
    published_at = _to_datetime(record.ann_date) if record.ann_date else None
    facts: list[FinancialFact] = []
    for attr, metric_name, unit, yoy_attr in _FINANCIAL_METRICS:
        value = getattr(record, attr)
        if value is None:
            continue
        yoy = getattr(record, yoy_attr) if yoy_attr else None
        facts.append(
            FinancialFact(
                fact_id=f"financial:{security_id}:{report_period}:{metric_name}",
                subject_ref=subject,
                report_period=report_period,
                report_type="fina_indicator",
                metric_name=metric_name,
                metric_value=value,
                unit=unit,
                yoy=yoy,
                occurred_at=occurred_at,
                published_at=published_at,
                source_ref=source_ref,
                confidence=0.98,
            )
        )
    return tuple(facts)


def map_announcement(
    record: TushareAnnouncementRecord,
    *,
    company_id: str,
    label: str | None = None,
    source_ref: SourceRef = TUSHARE_SOURCE_REF,
) -> AnnouncementFact:
    """Map an anns_d row into a disclosed AnnouncementFact reference."""
    subject = SubjectRef(entity_type="company", entity_id=company_id, label=label)
    published_at = _to_datetime(record.ann_date)
    announcement_id = _announcement_id(record)
    return AnnouncementFact(
        fact_id=f"announcement:{company_id}:{announcement_id}",
        subject_ref=subject,
        announcement_id=announcement_id,
        announcement_type=_announcement_type(record.ann_type, record.title),
        title=record.title,
        published_at=published_at,
        occurred_at=published_at,
        document_url=record.url or "",
        document_hash=_document_hash(record.content),
        source_ref=source_ref,
        confidence=0.9,
    )


def _announcement_id(record: TushareAnnouncementRecord) -> str:
    digest = hashlib.sha1(
        f"{record.ts_code}|{record.ann_date.isoformat()}|{record.title}".encode("utf-8")
    ).hexdigest()[:16]
    return f"{record.ann_date.isoformat()}:{digest}"


def _document_hash(content: str | None) -> str:
    if not content:
        return ""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _announcement_type(ann_type: str | None, title: str) -> AnnouncementType:
    text = f"{ann_type or ''} {title}".lower()
    rules: tuple[tuple[tuple[str, ...], AnnouncementType], ...] = (
        (("年度报告", "半年度报告", "季度报告", "定期报告", "年报", "中报"),
         AnnouncementType.PERIODIC_REPORT),
        (("业绩预告", "业绩快报"), AnnouncementType.EARNINGS_PREVIEW),
        (("分红", "派息", "利润分配"), AnnouncementType.DIVIDEND),
        (("重大合同", "中标"), AnnouncementType.MAJOR_CONTRACT),
        (("并购", "收购", "重组"), AnnouncementType.MERGER_ACQUISITION),
        (("问询函", "监管", "立案"), AnnouncementType.REGULATORY_INQUIRY),
        (("风险", "退市", "*st", "st"), AnnouncementType.RISK_WARNING),
        (("股东", "减持", "增持", "股权"), AnnouncementType.SHAREHOLDER_CHANGE),
    )
    for keywords, kind in rules:
        if any(keyword in text for keyword in keywords):
            return kind
    return AnnouncementType.OTHER


def _to_datetime(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)


def _report_period(end_date: date) -> str:
    """Render a fiscal report period label (e.g. 2025Q4) from an end date."""
    quarter = (end_date.month - 1) // 3 + 1
    return f"{end_date.year}Q{quarter}"


def _num_text(value: float | None) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
