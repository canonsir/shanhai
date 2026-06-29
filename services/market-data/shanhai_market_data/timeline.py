"""Company Knowledge Timeline — a read model over Market Knowledge facts.

The timeline projects the three fact families (generic MarketFact, FinancialFact,
AnnouncementFact) onto one ordered list of CompanyTimelineEvent. It is a derived
read model, never a fact source, so it never invents facts and keeps a reference
back to the fact ids it was built from.

Ordering uses one of the three preserved timestamps (default published_at);
the three timestamps are never collapsed into one.
"""

from __future__ import annotations

from datetime import datetime, timezone

from shanhai_market_data.models import (
    AnnouncementFact,
    CompanyTimelineEvent,
    FinancialFact,
    MarketFact,
    SourceRef,
    TimeBasis,
)

_MIN_TIME = datetime.min.replace(tzinfo=timezone.utc)


def build_company_timeline(
    company_id: str,
    *,
    market_facts: tuple[MarketFact, ...] = (),
    financial_facts: tuple[FinancialFact, ...] = (),
    announcement_facts: tuple[AnnouncementFact, ...] = (),
    time_basis: TimeBasis = TimeBasis.PUBLISHED_AT,
    latest_first: bool = True,
) -> tuple[CompanyTimelineEvent, ...]:
    """Project facts into one ordered company timeline.

    Facts without the chosen ordering timestamp fall back through
    published_at -> occurred_at -> captured_at so they never silently vanish.
    """
    events: list[CompanyTimelineEvent] = []

    for fact in market_facts:
        event_time, used_basis = _pick_time(
            fact.occurred_at, fact.published_at, fact.captured_at, time_basis
        )
        events.append(
            CompanyTimelineEvent(
                event_id=f"event:{fact.fact_id}",
                company_id=company_id,
                event_time=event_time,
                event_time_basis=used_basis,
                event_type=fact.fact_type,
                title=f"{fact.predicate}: {fact.object_value}".strip(": "),
                summary=fact.object_value,
                fact_refs=(fact.fact_id,),
                source_refs=(fact.source_ref,),
                confidence=fact.confidence,
            )
        )

    for fact in financial_facts:
        event_time, used_basis = _pick_time(
            fact.occurred_at, fact.published_at, fact.captured_at, time_basis
        )
        events.append(
            CompanyTimelineEvent(
                event_id=f"event:{fact.fact_id}",
                company_id=company_id,
                event_time=event_time,
                event_time_basis=used_basis,
                event_type=fact.fact_type,
                title=f"{fact.report_period} {fact.metric_name}",
                summary=_financial_summary(fact),
                fact_refs=(fact.fact_id,),
                source_refs=(fact.source_ref,),
                confidence=fact.confidence,
            )
        )

    for fact in announcement_facts:
        event_time, used_basis = _pick_time(
            fact.occurred_at, fact.published_at, fact.captured_at, time_basis
        )
        events.append(
            CompanyTimelineEvent(
                event_id=f"event:{fact.fact_id}",
                company_id=company_id,
                event_time=event_time,
                event_time_basis=used_basis,
                event_type=fact.fact_type,
                title=fact.title or fact.announcement_type.value,
                summary=fact.extracted_summary,
                fact_refs=(fact.fact_id,),
                source_refs=(fact.source_ref,),
                confidence=fact.confidence,
            )
        )

    events.sort(key=lambda event: (event.event_time, event.event_id), reverse=latest_first)
    return tuple(events)


def _pick_time(
    occurred_at: datetime | None,
    published_at: datetime | None,
    captured_at: datetime | None,
    preferred: TimeBasis,
) -> tuple[datetime, TimeBasis]:
    by_basis: dict[TimeBasis, datetime | None] = {
        TimeBasis.OCCURRED_AT: occurred_at,
        TimeBasis.PUBLISHED_AT: published_at,
        TimeBasis.CAPTURED_AT: captured_at,
    }
    order = (preferred, TimeBasis.PUBLISHED_AT, TimeBasis.OCCURRED_AT, TimeBasis.CAPTURED_AT)
    for basis in order:
        value = by_basis.get(basis)
        if value is not None:
            return _as_aware(value), basis
    return _MIN_TIME, preferred


def _as_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _financial_summary(fact: FinancialFact) -> str:
    parts = [fact.metric_name]
    if fact.metric_value is not None:
        unit = f" {fact.unit}".rstrip()
        parts.append(f"= {_num_text(fact.metric_value)}{unit}")
    if fact.yoy is not None:
        parts.append(f"(yoy {_num_text(fact.yoy)})")
    return " ".join(parts)


def _num_text(value: float) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def collect_timeline_source_refs(
    events: tuple[CompanyTimelineEvent, ...],
) -> tuple[SourceRef, ...]:
    deduped: dict[tuple[str, str | None], SourceRef] = {}
    for event in events:
        for ref in event.source_refs:
            deduped[(ref.source_id, ref.external_id)] = ref
    return tuple(deduped.values())
