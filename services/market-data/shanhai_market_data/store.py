"""In-memory adapter for the Market Knowledge Store.

``InMemoryMarketKnowledgeRepository`` is the local-first / test adapter behind the
``MarketKnowledgeRepository`` boundary (M3.3 Phase 1). It is process-local and
volatile — durable SQLite / Postgres adapters arrive in M3.3 Phase 2 / 3. It is
not Memory, Experience, RuntimeContext, or a trading store.
"""

from __future__ import annotations

from shanhai_market_data.models import (
    AnnouncementFact,
    Company,
    CompanyIntelligence,
    CompanyTimelineEvent,
    FinancialFact,
    Industry,
    ListedEntity,
    Listing,
    MarketFact,
    QuoteSnapshot,
    Security,
    SourceRef,
    TimeBasis,
)
from shanhai_market_data.timeline import build_company_timeline


class InMemoryMarketKnowledgeRepository:
    """Local-first, process-local market knowledge repository.

    This is a minimal Knowledge Store adapter for the Data Foundation MVP. It is
    not Memory, Experience, RuntimeContext, or a trading store. Facts are kept
    per company so the read model can assemble one company knowledge timeline.
    """

    def __init__(self) -> None:
        self._companies: dict[str, Company] = {}
        self._listed_entities: dict[str, ListedEntity] = {}
        self._securities: dict[str, Security] = {}
        self._listings: dict[str, Listing] = {}
        self._industries: dict[str, Industry] = {}
        self._company_industries: dict[str, str] = {}
        self._facts_by_company: dict[str, dict[str, MarketFact]] = {}
        self._financial_facts_by_company: dict[str, dict[str, FinancialFact]] = {}
        self._announcement_facts_by_company: dict[str, dict[str, AnnouncementFact]] = {}
        self._quotes_by_security: dict[str, dict[str, QuoteSnapshot]] = {}
        self._security_id_by_ts_code: dict[str, str] = {}

    def upsert_company_bundle(
        self,
        *,
        company: Company,
        listed_entity: ListedEntity,
        security: Security,
        listing: Listing,
        industry: Industry | None = None,
        facts: tuple[MarketFact, ...] = (),
        financial_facts: tuple[FinancialFact, ...] = (),
        announcement_facts: tuple[AnnouncementFact, ...] = (),
    ) -> None:
        self._companies[company.company_id] = company
        self._listed_entities[listed_entity.listed_entity_id] = listed_entity
        self._securities[security.security_id] = security
        self._security_id_by_ts_code[security.ts_code.lower()] = security.security_id
        self._listings[listing.listing_id] = listing
        if industry is not None:
            self._industries[industry.industry_id] = industry
            self._company_industries[company.company_id] = industry.industry_id
        self.upsert_market_facts(company.company_id, facts)
        self.upsert_financial_facts(company.company_id, financial_facts)
        self.upsert_announcement_facts(company.company_id, announcement_facts)

    def upsert_market_facts(
        self, company_id: str, facts: tuple[MarketFact, ...]
    ) -> None:
        bucket = self._facts_by_company.setdefault(company_id, {})
        for fact in facts:
            bucket[fact.fact_id] = fact

    def upsert_financial_facts(
        self, company_id: str, facts: tuple[FinancialFact, ...]
    ) -> None:
        bucket = self._financial_facts_by_company.setdefault(company_id, {})
        for fact in facts:
            bucket[fact.fact_id] = fact

    def upsert_announcement_facts(
        self, company_id: str, facts: tuple[AnnouncementFact, ...]
    ) -> None:
        bucket = self._announcement_facts_by_company.setdefault(company_id, {})
        for fact in facts:
            bucket[fact.fact_id] = fact

    def upsert_quote(self, quote: QuoteSnapshot) -> None:
        self._quotes_by_security.setdefault(quote.security_id, {})[quote.quote_id] = quote

    def get_company_intelligence_by_ts_code(self, ts_code: str) -> CompanyIntelligence | None:
        security_id = self._security_id_by_ts_code.get(ts_code.lower())
        if security_id is None:
            return None
        security = self._securities.get(security_id)
        if security is None:
            return None
        listed_entity = self._listed_entities.get(security.listed_entity_id)
        if listed_entity is None:
            return None
        company = self._companies.get(listed_entity.company_id)
        if company is None:
            return None
        listing = next(
            (item for item in self._listings.values() if item.security_id == security.security_id),
            None,
        )
        if listing is None:
            return None
        industry = self._industries.get(self._company_industries.get(company.company_id, ""))
        latest_quote = self._latest_quote(security.security_id)
        facts = tuple(self._facts_by_company.get(company.company_id, {}).values())
        financial_facts = tuple(
            self._financial_facts_by_company.get(company.company_id, {}).values()
        )
        announcement_facts = tuple(
            self._announcement_facts_by_company.get(company.company_id, {}).values()
        )
        timeline = build_company_timeline(
            company.company_id,
            market_facts=facts,
            financial_facts=financial_facts,
            announcement_facts=announcement_facts,
        )
        source_refs = self._collect_source_refs(
            listed_entity, latest_quote, facts, financial_facts, announcement_facts
        )
        return CompanyIntelligence(
            company=company,
            listed_entity=listed_entity,
            security=security,
            listing=listing,
            industry=industry,
            latest_quote=latest_quote,
            facts=facts,
            financial_facts=financial_facts,
            announcement_facts=announcement_facts,
            timeline=timeline,
            source_refs=source_refs,
        )

    def get_company_timeline(
        self,
        ts_code: str,
        *,
        time_basis: TimeBasis = TimeBasis.PUBLISHED_AT,
        latest_first: bool = True,
    ) -> tuple[CompanyTimelineEvent, ...]:
        security_id = self._security_id_by_ts_code.get(ts_code.lower())
        if security_id is None:
            return ()
        security = self._securities.get(security_id)
        if security is None:
            return ()
        listed_entity = self._listed_entities.get(security.listed_entity_id)
        if listed_entity is None:
            return ()
        company_id = listed_entity.company_id
        return build_company_timeline(
            company_id,
            market_facts=tuple(self._facts_by_company.get(company_id, {}).values()),
            financial_facts=tuple(self._financial_facts_by_company.get(company_id, {}).values()),
            announcement_facts=tuple(
                self._announcement_facts_by_company.get(company_id, {}).values()
            ),
            time_basis=time_basis,
            latest_first=latest_first,
        )

    def list_company_intelligence(self, limit: int = 50) -> tuple[CompanyIntelligence, ...]:
        results = []
        for security in self._securities.values():
            item = self.get_company_intelligence_by_ts_code(security.ts_code)
            if item is not None:
                results.append(item)
        return tuple(results[:limit])

    def search_company(self, text: str, limit: int = 50) -> tuple[CompanyIntelligence, ...]:
        needle = text.lower()
        matched_ts_codes = []
        for company in self._companies.values():
            aliases = [a.lower() for a in company.aliases]
            if needle in company.name.lower() or any(needle in alias for alias in aliases):
                security = self._security_for_company(company.company_id)
                if security:
                    matched_ts_codes.append(security.ts_code)
        return tuple(
            item
            for ts_code in matched_ts_codes[:limit]
            if (item := self.get_company_intelligence_by_ts_code(ts_code)) is not None
        )

    def _security_for_company(self, company_id: str) -> Security | None:
        listed_entity = next(
            (
                item
                for item in self._listed_entities.values()
                if item.company_id == company_id
            ),
            None,
        )
        if listed_entity is None:
            return None
        return next(
            (
                item
                for item in self._securities.values()
                if item.listed_entity_id == listed_entity.listed_entity_id
            ),
            None,
        )

    def _latest_quote(self, security_id: str) -> QuoteSnapshot | None:
        quotes = list(self._quotes_by_security.get(security_id, {}).values())
        if not quotes:
            return None
        return sorted(quotes, key=lambda item: item.trade_date)[-1]

    @staticmethod
    def _collect_source_refs(
        listed_entity: ListedEntity,
        latest_quote: QuoteSnapshot | None,
        facts: tuple[MarketFact, ...],
        financial_facts: tuple[FinancialFact, ...],
        announcement_facts: tuple[AnnouncementFact, ...],
    ) -> tuple[SourceRef, ...]:
        refs = [listed_entity.source_ref]
        refs.extend(fact.source_ref for fact in facts)
        refs.extend(fact.source_ref for fact in financial_facts)
        refs.extend(fact.source_ref for fact in announcement_facts)
        if latest_quote is not None:
            refs.append(latest_quote.source_ref)
        deduped: dict[tuple[str, str | None], SourceRef] = {}
        for ref in refs:
            deduped[(ref.source_id, ref.external_id)] = ref
        return tuple(deduped.values())


# Deprecated compatibility alias.
# Only kept for legacy postgres_store.py inheritance.
# Remove together with postgres_store.py in the persistence migration phase
# (M3.3 Phase 3). No new code should import this name — depend on the
# MarketKnowledgeRepository Protocol (domain/repository.py) instead.
InMemoryMarketKnowledgeStore = InMemoryMarketKnowledgeRepository
