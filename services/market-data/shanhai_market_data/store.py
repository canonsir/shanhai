"""Minimal market knowledge store for Milestone 2 MVP."""

from __future__ import annotations

from shanhai_market_data.models import (
    Company,
    CompanyIntelligence,
    Industry,
    ListedEntity,
    Listing,
    MarketFact,
    QuoteSnapshot,
    Security,
    SourceRef,
)


class InMemoryMarketKnowledgeStore:
    """Local-first, process-local market knowledge store.

    This is a minimal Knowledge Store for Data Foundation MVP. It is not Memory,
    Experience, RuntimeContext, or a trading store.
    """

    def __init__(self) -> None:
        self._companies: dict[str, Company] = {}
        self._listed_entities: dict[str, ListedEntity] = {}
        self._securities: dict[str, Security] = {}
        self._listings: dict[str, Listing] = {}
        self._industries: dict[str, Industry] = {}
        self._company_industries: dict[str, str] = {}
        self._facts_by_entity: dict[str, dict[str, MarketFact]] = {}
        self._quotes_by_security: dict[str, dict[str, QuoteSnapshot]] = {}

    def upsert_company_bundle(
        self,
        *,
        company: Company,
        listed_entity: ListedEntity,
        security: Security,
        listing: Listing,
        industry: Industry | None = None,
        facts: tuple[MarketFact, ...] = (),
    ) -> None:
        self._companies[company.company_id] = company
        self._listed_entities[listed_entity.listed_entity_id] = listed_entity
        self._securities[security.security_id] = security
        self._listings[listing.listing_id] = listing
        if industry is not None:
            self._industries[industry.industry_id] = industry
            self._company_industries[company.company_id] = industry.industry_id
        for fact in facts:
            self._facts_by_entity.setdefault(fact.entity_id, {})[fact.fact_id] = fact

    def upsert_quote(self, quote: QuoteSnapshot) -> None:
        self._quotes_by_security.setdefault(quote.security_id, {})[quote.quote_id] = quote

    def get_company_intelligence_by_ts_code(self, ts_code: str) -> CompanyIntelligence | None:
        security_id = f"security:cn-a:{ts_code.lower()}"
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
        facts = tuple(self._facts_by_entity.get(company.company_id, {}).values())
        source_refs = self._collect_source_refs(listed_entity, latest_quote, facts)
        return CompanyIntelligence(
            company=company,
            listed_entity=listed_entity,
            security=security,
            listing=listing,
            industry=industry,
            latest_quote=latest_quote,
            facts=facts,
            source_refs=source_refs,
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
    ) -> tuple[SourceRef, ...]:
        refs = [listed_entity.source_ref]
        refs.extend(fact.source_ref for fact in facts)
        if latest_quote is not None:
            refs.append(latest_quote.source_ref)
        deduped: dict[tuple[str, str | None], SourceRef] = {}
        for ref in refs:
            deduped[(ref.source_id, ref.external_id)] = ref
        return tuple(deduped.values())
