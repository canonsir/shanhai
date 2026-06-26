"""Stable ShanHai market identity helpers."""

from __future__ import annotations


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
