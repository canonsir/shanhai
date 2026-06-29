"""M2.5 Phase 1 Identity Registry (entity_identity_mapping) tests.

Run:
PYTHONPATH=services/market-data:. .venv/bin/python -m tests.market_data.test_identity_registry
"""

from __future__ import annotations

from shanhai_market_data import IdentityRegistry
from shanhai_market_data.registry import LEGACY_SOURCE


def test_external_mapping_is_deterministic() -> None:
    registry = IdentityRegistry()

    first = registry.resolve_or_allocate("security", "tushare", "600519.SH")
    second = registry.resolve_or_allocate("security", "tushare", "600519.SH")

    assert first == second
    assert first.startswith("security:")
    assert "600519" not in first
    print("[OK] 同一外部码确定性复用同一代理键")


def test_distinct_external_codes_get_distinct_surrogates() -> None:
    registry = IdentityRegistry()

    a = registry.resolve_or_allocate("company", "tushare", "600519.SH")
    b = registry.resolve_or_allocate("company", "tushare", "300750.SZ")

    assert a != b
    print("[OK] 不同外部码分配不同代理键")


def test_external_source_mapping_links_multiple_sources() -> None:
    registry = IdentityRegistry()

    internal = registry.resolve_or_allocate("company", "tushare", "600519.SH")
    # A second source (e.g. 东方财富) points at the same surrogate id.
    registry.link("company", internal, "eastmoney", "600519")

    assert registry.internal_for("company", "tushare", "600519.SH") == internal
    assert registry.internal_for("company", "eastmoney", "600519") == internal
    print("[OK] 多源外部标识映射到同一代理键")


def test_old_to_new_migration_and_rollback() -> None:
    registry = IdentityRegistry()

    internal = registry.resolve_or_allocate("company", "tushare", "600519.SH")
    registry.record_legacy_migration("company", internal, "company:cn-a:600519.sh")

    # Forward: legacy id -> new surrogate id.
    assert registry.internal_for("company", LEGACY_SOURCE, "company:cn-a:600519.sh") == internal
    # Rollback: new surrogate id -> the legacy id it replaced.
    assert registry.legacy_id_for(internal) == "company:cn-a:600519.sh"
    print("[OK] old_id -> new_id 迁移可正查与回滚")


def test_conflicting_link_raises() -> None:
    registry = IdentityRegistry()

    internal = registry.resolve_or_allocate("company", "tushare", "600519.SH")
    try:
        registry.link("company", "company:other", "tushare", "600519.SH")
        assert False, "冲突映射应抛错"
    except ValueError as exc:
        assert "identity conflict" in str(exc)
    # Idempotent for an identical mapping.
    registry.link("company", internal, "tushare", "600519.SH")
    print("[OK] 冲突映射报错，幂等映射放行")


def main() -> None:
    test_external_mapping_is_deterministic()
    test_distinct_external_codes_get_distinct_surrogates()
    test_external_source_mapping_links_multiple_sources()
    test_old_to_new_migration_and_rollback()
    test_conflicting_link_raises()
    print("\nIdentity Registry (entity_identity_mapping) 测试全部通过 ✅")


if __name__ == "__main__":
    main()
