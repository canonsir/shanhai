"""Stable ShanHai market identity helpers.

Identity rule (M2.5 Phase 1): external codes such as ts_code / symbol are
**attributes and lookup keys, never identities**. Live identities are surrogate
keys allocated by `new_internal_id` and tracked in the IdentityRegistry.

The legacy ``*_from_ts_code`` helpers are retained only to record old -> new
migration traceability (``legacy_id``) inside the registry. Do NOT use them to
assign live identities.
"""

from __future__ import annotations

import uuid


def new_internal_id(entity_type: str) -> str:
    """Allocate a surrogate identity that does not encode any external code."""
    return f"{entity_type}:{uuid.uuid4().hex}"


# --- Legacy (deprecated): ts_code-derived ids, kept for migration mapping only ---


def company_id_from_ts_code(ts_code: str) -> str:
    return f"company:cn-a:{ts_code.lower()}"


def listed_entity_id_from_ts_code(ts_code: str) -> str:
    return f"listed_entity:cn-a:{ts_code.lower()}"


def security_id_from_ts_code(ts_code: str) -> str:
    return f"security:cn-a:{ts_code.lower()}"


def listing_id_from_ts_code(ts_code: str) -> str:
    return f"listing:cn-a:{ts_code.lower()}"


def industry_id_from_name(name: str) -> str:
    slug = name.strip().replace(" ", "-")
    return f"industry:tushare:{slug}"
