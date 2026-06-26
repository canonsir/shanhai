"""Entity Resolver v0.1 for A-share market identities."""

from __future__ import annotations

from shanhai_market_data.identity import (
    company_id_from_ts_code,
    listed_entity_id_from_ts_code,
    listing_id_from_ts_code,
    security_id_from_ts_code,
)
from shanhai_market_data.models import ResolvedMarketIdentity, TushareStockBasicRecord


class EntityResolver:
    """Deterministic resolver for the Data Foundation MVP.

    v0.1 intentionally does not merge legal entities across securities. It
    preserves source namespaces and prevents Company / ListedEntity / Security /
    Listing identity collapse.
    """

    def resolve_stock_basic(self, record: TushareStockBasicRecord) -> ResolvedMarketIdentity:
        return ResolvedMarketIdentity(
            ts_code=record.ts_code,
            company_id=company_id_from_ts_code(record.ts_code),
            listed_entity_id=listed_entity_id_from_ts_code(record.ts_code),
            security_id=security_id_from_ts_code(record.ts_code),
            listing_id=listing_id_from_ts_code(record.ts_code),
            external_ids=(
                f"tushare:ts_code:{record.ts_code}",
                f"tushare:symbol:{record.symbol}",
            ),
            aliases=tuple(
                item
                for item in (record.name, record.symbol, record.ts_code)
                if item
            ),
        )
