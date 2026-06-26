"""Company Intelligence API surface.

This is a service-level API object, not a FastAPI route and not an Agent tool.
It provides a read-only boundary over the Market Knowledge Store.
"""

from __future__ import annotations

from typing import Any

from shanhai_market_data.models import CompanyIntelligence
from shanhai_market_data.store import InMemoryMarketKnowledgeStore


class CompanyIntelligenceAPI:
    def __init__(self, store: InMemoryMarketKnowledgeStore) -> None:
        self._store = store

    def get_company(self, ts_code: str) -> dict[str, Any] | None:
        intelligence = self._store.get_company_intelligence_by_ts_code(ts_code)
        if intelligence is None:
            return None
        return self._to_payload(intelligence)

    def search_companies(self, text: str, limit: int = 50) -> tuple[dict[str, Any], ...]:
        return tuple(
            self._to_payload(item)
            for item in self._store.search_company(text=text, limit=limit)
        )

    def list_companies(self, limit: int = 50) -> tuple[dict[str, Any], ...]:
        return tuple(
            self._to_payload(item)
            for item in self._store.list_company_intelligence(limit=limit)
        )

    @staticmethod
    def _to_payload(item: CompanyIntelligence) -> dict[str, Any]:
        return {
            "company": item.company.model_dump(mode="json"),
            "listed_entity": item.listed_entity.model_dump(mode="json"),
            "security": item.security.model_dump(mode="json"),
            "listing": item.listing.model_dump(mode="json"),
            "industry": item.industry.model_dump(mode="json") if item.industry else None,
            "latest_quote": (
                item.latest_quote.model_dump(mode="json") if item.latest_quote else None
            ),
            "facts": [fact.model_dump(mode="json") for fact in item.facts],
            "source_refs": [ref.model_dump(mode="json") for ref in item.source_refs],
        }
