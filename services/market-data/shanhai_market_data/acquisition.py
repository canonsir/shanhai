"""Public data acquisition flow — M3.2 Data Acquisition Foundation.

Pulls real A-share data through source-neutral public providers and lands it in
the Market Knowledge Store, reusing the proven mapper / fact_mapper layer so the
real ``SourceRef`` provenance from each provider travels all the way to the
Company Intelligence read model.

This is the "let reality hit the model first" spike path: free providers
(EastMoney + CNInfo) instead of a commercial vendor, no raw storage engine, and
graceful degradation when a provider does not cover a capability.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from shanhai_market_data.fact_mapper import (
    build_quote_fact,
    map_announcement,
    map_financial_indicator,
)
from shanhai_market_data.mapper import map_daily_quote, map_stock_basic
from shanhai_market_data.models import AnnouncementFact, FinancialFact, MarketFact
from shanhai_market_data.provider import PublicMarketDataProvider
from shanhai_market_data.resolver import EntityResolver
from shanhai_market_data.store import InMemoryMarketKnowledgeStore


@dataclass(frozen=True)
class AcquisitionReport:
    ts_code: str
    company_id: str
    name: str
    has_quote: bool = False
    financial_fact_count: int = 0
    announcement_fact_count: int = 0
    providers: tuple[str, ...] = field(default_factory=tuple)


class PublicDataAcquisitionService:
    """Acquire one company's facts from public providers into the store.

    ``profile_provider`` supplies profile / security / quote / financial;
    ``announcement_provider`` (optional) supplies disclosed announcements. Each
    provider attaches its own ``SourceRef``, so different facts on the same
    company carry different, truthful provenance.
    """

    def __init__(
        self,
        store: InMemoryMarketKnowledgeStore,
        *,
        profile_provider: PublicMarketDataProvider,
        announcement_provider: PublicMarketDataProvider | None = None,
        resolver: EntityResolver | None = None,
    ) -> None:
        self._store = store
        self._profile = profile_provider
        self._announcements = announcement_provider
        self._resolver = resolver if resolver is not None else EntityResolver()

    def acquire_company(self, ts_code: str) -> AcquisitionReport:
        profile_record, profile_ref = self._profile.fetch_company_profile(ts_code)
        company, listed_entity, security, listing, industry, profile_facts = map_stock_basic(
            profile_record, source_ref=profile_ref, resolver=self._resolver
        )
        label = company.name
        market_facts: list[MarketFact] = list(profile_facts)
        providers: list[str] = [self._profile.name]

        latest_quote = None
        try:
            quote_record, quote_ref = self._profile.fetch_quote(ts_code)
        except NotImplementedError:
            quote_record = None
        if quote_record is not None:
            latest_quote = map_daily_quote(
                quote_record, source_ref=quote_ref, resolver=self._resolver
            )
            market_facts.append(build_quote_fact(latest_quote, label=label))

        financial_facts = self._acquire_financial(ts_code, security.security_id, label)
        announcement_facts = self._acquire_announcements(ts_code, company.company_id, label)
        if announcement_facts and self._announcements is not None:
            providers.append(self._announcements.name)

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

        return AcquisitionReport(
            ts_code=ts_code,
            company_id=company.company_id,
            name=label,
            has_quote=latest_quote is not None,
            financial_fact_count=len(financial_facts),
            announcement_fact_count=len(announcement_facts),
            providers=tuple(providers),
        )

    def _acquire_financial(
        self, ts_code: str, security_id: str, label: str
    ) -> tuple[FinancialFact, ...]:
        try:
            rows = self._profile.fetch_financial(ts_code)
        except NotImplementedError:
            return ()
        facts: list[FinancialFact] = []
        for record, source_ref in rows:
            facts.extend(
                map_financial_indicator(
                    record, security_id=security_id, label=label, source_ref=source_ref
                )
            )
        return tuple(facts)

    def _acquire_announcements(
        self, ts_code: str, company_id: str, label: str
    ) -> tuple[AnnouncementFact, ...]:
        provider = self._announcements
        if provider is None:
            return ()
        try:
            rows = provider.fetch_announcement(ts_code)
        except NotImplementedError:
            return ()
        return tuple(
            map_announcement(record, company_id=company_id, label=label, source_ref=source_ref)
            for record, source_ref in rows
        )
