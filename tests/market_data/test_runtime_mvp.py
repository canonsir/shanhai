"""Milestone 2.2 Market Data Runtime MVP tests.

Run:
PYTHONPATH=services/market-data:apps/api:. .venv/bin/python -m tests.market_data.test_runtime_mvp
"""

from __future__ import annotations

from datetime import date

from shanhai_api.main import company_console, company_detail_console
from shanhai_market_data import (
    EntityResolver,
    Exchange,
    InMemoryMarketKnowledgeStore,
    ListingStatus,
    TushareDailyRecord,
    TushareScheduledIngestion,
    TushareStockBasicRecord,
)
from shanhai_market_data.mapper import map_daily_quote, map_stock_basic
from shanhai_market_data.postgres_store import PostgresMarketKnowledgeStore, SCHEMA_SQL
from shanhai_market_data.scheduler import ScheduledIngestionConfig
from shanhai_market_data.sync import AShareCompanySyncService, DEFAULT_A_SHARE_TARGETS


class _TinyProvider:
    def stock_basic(self, ts_codes: tuple[str, ...]) -> tuple[TushareStockBasicRecord, ...]:
        return tuple(
            TushareStockBasicRecord(
                ts_code=ts_code,
                symbol=ts_code.split(".")[0],
                name={"600519.SH": "贵州茅台"}.get(ts_code, ts_code),
                area="贵州",
                industry="白酒",
                market="主板",
                list_date=date(2001, 8, 27),
                exchange=Exchange.SSE if ts_code.endswith(".SH") else Exchange.SZSE,
                list_status=ListingStatus.LISTED,
            )
            for ts_code in ts_codes
        )

    def daily(
        self,
        ts_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[TushareDailyRecord, ...]:
        return (
            TushareDailyRecord(
                ts_code=ts_code,
                trade_date=date(2024, 6, 26),
                close=123.45,
            ),
        )


class _FakePgConnection:
    def __init__(self) -> None:
        self.statements: list[tuple[str, tuple | None]] = []

    def __enter__(self) -> "_FakePgConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, sql: str, params: tuple | None = None) -> "_FakePgConnection":
        self.statements.append((sql, params))
        return self

    def fetchone(self) -> None:
        return None

    def fetchall(self) -> list:
        return []


def test_entity_resolver_maps_external_code_to_stable_surrogates() -> None:
    record = TushareStockBasicRecord(
        ts_code="600519.SH",
        symbol="600519",
        name="贵州茅台",
        exchange=Exchange.SSE,
    )
    resolver = EntityResolver()
    identity = resolver.resolve_stock_basic(record)

    # The four layers are independent surrogate ids, none derived from ts_code.
    layers = (
        identity.company_id,
        identity.listed_entity_id,
        identity.security_id,
        identity.listing_id,
    )
    assert len(set(layers)) == 4
    for layer_id in layers:
        assert "600519" not in layer_id

    # The external code is preserved as an attribute, not as an identity.
    assert "tushare:ts_code:600519.SH" in identity.external_ids

    # Deterministic: resolving the same ts_code again reuses the same surrogates.
    again = resolver.resolve_stock_basic(record)
    assert again.company_id == identity.company_id
    assert again.security_id == identity.security_id

    # Registry keeps an old -> new migration trail for rollback.
    legacy = resolver.registry.legacy_id_for(identity.company_id)
    assert legacy == "company:cn-a:600519.sh"
    print("[OK] Entity Resolver v0.1 确定性映射外部码到代理键身份")


def test_postgres_store_schema_and_persist_boundary() -> None:
    conn = _FakePgConnection()
    store = PostgresMarketKnowledgeStore(connection_factory=lambda: conn)
    record = TushareStockBasicRecord(
        ts_code="600519.SH",
        symbol="600519",
        name="贵州茅台",
        area="贵州",
        industry="白酒",
        market="主板",
        list_date=date(2001, 8, 27),
        exchange=Exchange.SSE,
        list_status=ListingStatus.LISTED,
    )
    resolver = EntityResolver()
    company, listed_entity, security, listing, industry, facts = map_stock_basic(
        record, resolver=resolver
    )
    store.upsert_company_bundle(
        company=company,
        listed_entity=listed_entity,
        security=security,
        listing=listing,
        industry=industry,
        facts=facts,
    )
    store.upsert_quote(
        map_daily_quote(
            TushareDailyRecord(
                ts_code="600519.SH",
                trade_date=date(2024, 6, 26),
                close=123.45,
            ),
            resolver=resolver,
        )
    )

    sql_text = "\n".join(sql for sql, _ in conn.statements)
    assert "market_company_intelligence" in SCHEMA_SQL
    assert "CREATE TABLE IF NOT EXISTS market_company_intelligence" in sql_text
    assert "INSERT INTO market_company_intelligence" in sql_text
    print("[OK] PostgreSQL Knowledge Store schema / persist 边界通过")


def test_scheduled_ingestion_run_once() -> None:
    store = InMemoryMarketKnowledgeStore()
    service = AShareCompanySyncService(_TinyProvider(), store)
    scheduler = TushareScheduledIngestion(service, ScheduledIngestionConfig())

    report = scheduler.run_once()

    assert report["requested_count"] == len(DEFAULT_A_SHARE_TARGETS)
    assert report["synced_count"] == len(DEFAULT_A_SHARE_TARGETS)
    assert store.get_company_intelligence_by_ts_code("600519.SH") is not None
    print("[OK] Tushare scheduled ingestion run_once 通过")


def test_company_console_alpha_route() -> None:
    html = company_console()

    assert "Company Intelligence Alpha" in html
    assert "/companies" in html
    print("[OK] Company Console Alpha route 通过")


def test_company_detail_console_alpha_route() -> None:
    html = company_detail_console("600519.SH")

    # The data-model validation page must express every fact family naturally.
    assert "600519.SH" in html
    assert "证券关系" in html
    assert "财务事实 (FinancialFact)" in html
    assert "公告时间线 (AnnouncementFact)" in html
    assert "MarketFact Timeline" in html
    assert "/companies/600519.SH/timeline" not in html  # built client-side from tsCode
    print("[OK] Company Detail Console (/company/:id) 数据模型验证页通过")


def main() -> None:
    test_entity_resolver_maps_external_code_to_stable_surrogates()
    test_postgres_store_schema_and_persist_boundary()
    test_scheduled_ingestion_run_once()
    test_company_console_alpha_route()
    test_company_detail_console_alpha_route()
    print("\nMilestone 2.2 Market Data Runtime MVP 测试全部通过 ✅")


if __name__ == "__main__":
    main()
