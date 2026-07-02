"""MarketKnowledgeRepository — storage-agnostic boundary for the Market
Knowledge Store (M3.3 Phase 1).

The business layer (acquisition / sync / api) depends only on this Protocol, so
the persistence backend can move from in-memory to SQLite (local-first, M3.3
Phase 2) to PostgreSQL (scale backend, M3.3 Phase 3) without touching any
caller. This mirrors the proven RunStore boundary (ADR 0008 / 0009): one
abstraction, many adapters, no driver leaking into the domain.

The eight methods below are the exact contract already relied on by
``api.py`` / ``acquisition.py`` / ``sync.py`` — five writes (ingestion) and
three reads plus the timeline projection. Adapters must honour these signatures
unchanged.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

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
    TimeBasis,
)


@runtime_checkable
class MarketKnowledgeRepository(Protocol):
    """Read/write boundary over the Market Knowledge Store.

    Implementations persist the four-layer identity model
    (Company / ListedEntity / Security / Listing) plus the three fact families
    (MarketFact / FinancialFact / AnnouncementFact) and quote snapshots, and
    assemble the ``CompanyIntelligence`` read model. The timeline is a derived
    read model, never a stored table.
    """

    # --- write (ingestion) ----------------------------------------------------

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
        ...

    def upsert_market_facts(self, company_id: str, facts: tuple[MarketFact, ...]) -> None:
        ...

    def upsert_financial_facts(
        self, company_id: str, facts: tuple[FinancialFact, ...]
    ) -> None:
        ...

    def upsert_announcement_facts(
        self, company_id: str, facts: tuple[AnnouncementFact, ...]
    ) -> None:
        ...

    def upsert_quote(self, quote: QuoteSnapshot) -> None:
        ...

    # --- read (read model) ----------------------------------------------------

    def get_company_intelligence_by_ts_code(
        self, ts_code: str
    ) -> CompanyIntelligence | None:
        ...

    def get_company_timeline(
        self,
        ts_code: str,
        *,
        time_basis: TimeBasis = TimeBasis.PUBLISHED_AT,
        latest_first: bool = True,
    ) -> tuple[CompanyTimelineEvent, ...]:
        ...

    def list_company_intelligence(self, limit: int = 50) -> tuple[CompanyIntelligence, ...]:
        ...

    def search_company(self, text: str, limit: int = 50) -> tuple[CompanyIntelligence, ...]:
        ...
