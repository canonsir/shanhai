"""Entity Resolver v0.1 for A-share market identities.

Deterministic external-identifier mapping only. The resolver translates a
provider record (keyed by an external code such as ts_code) into the four
surrogate identities (Company / ListedEntity / Security / Listing) via the
IdentityRegistry. The same external code always resolves to the same surrogate
ids within a registry's lifetime.

Explicitly out of scope for v0.1 (frozen in the Phase 0 Closure Review):
no AI entity resolution, no fuzzy matching, no embeddings, no cross-security
merge. The model does not forbid two securities sharing a company_id, but the
resolver never does that automatically.
"""

from __future__ import annotations

from shanhai_market_data.identity import (
    company_id_from_ts_code,
    listed_entity_id_from_ts_code,
    listing_id_from_ts_code,
    security_id_from_ts_code,
)
from shanhai_market_data.models import ResolvedMarketIdentity, TushareStockBasicRecord
from shanhai_market_data.registry import IdentityRegistry

TUSHARE_SOURCE = "tushare"


class EntityResolver:
    """Deterministic resolver backed by an IdentityRegistry.

    Identities are surrogate keys that do not encode the external code; the
    external code is recorded as an attribute and a registry lookup key only.
    """

    def __init__(self, registry: IdentityRegistry | None = None) -> None:
        self._registry = registry if registry is not None else IdentityRegistry()

    @property
    def registry(self) -> IdentityRegistry:
        return self._registry

    def resolve_stock_basic(self, record: TushareStockBasicRecord) -> ResolvedMarketIdentity:
        ts_code = record.ts_code
        company_id = self._resolve_layer("company", ts_code, company_id_from_ts_code)
        listed_entity_id = self._resolve_layer(
            "listed_entity", ts_code, listed_entity_id_from_ts_code
        )
        security_id = self._resolve_layer("security", ts_code, security_id_from_ts_code)
        listing_id = self._resolve_layer("listing", ts_code, listing_id_from_ts_code)
        return ResolvedMarketIdentity(
            ts_code=ts_code,
            company_id=company_id,
            listed_entity_id=listed_entity_id,
            security_id=security_id,
            listing_id=listing_id,
            external_ids=(
                f"{TUSHARE_SOURCE}:ts_code:{ts_code}",
                f"{TUSHARE_SOURCE}:symbol:{record.symbol}",
            ),
            aliases=tuple(
                item
                for item in (record.name, record.symbol, ts_code)
                if item
            ),
        )

    def security_id_for(self, ts_code: str) -> str:
        """Resolve (reuse or allocate) the surrogate security id for a ts_code."""
        return self._resolve_layer("security", ts_code, security_id_from_ts_code)

    def company_id_for(self, ts_code: str) -> str:
        """Resolve (reuse or allocate) the surrogate company id for a ts_code."""
        return self._resolve_layer("company", ts_code, company_id_from_ts_code)

    def _resolve_layer(self, entity_type: str, ts_code: str, legacy_fn) -> str:
        internal_id = self._registry.resolve_or_allocate(entity_type, TUSHARE_SOURCE, ts_code)
        self._registry.record_legacy_migration(entity_type, internal_id, legacy_fn(ts_code))
        return internal_id
