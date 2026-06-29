"""Map provider records into ShanHai market entities."""

from __future__ import annotations

from datetime import datetime, timezone

from shanhai_market_data.fact_mapper import (
    TUSHARE_SOURCE_REF,
    build_company_profile_facts,
)
from shanhai_market_data.identity import industry_id_from_name
from shanhai_market_data.models import (
    Board,
    Company,
    Industry,
    ListedEntity,
    Listing,
    MarketFact,
    QuoteSnapshot,
    Security,
    SourceRef,
    TushareDailyRecord,
    TushareStockBasicRecord,
)
from shanhai_market_data.resolver import EntityResolver


def map_stock_basic(
    record: TushareStockBasicRecord,
    *,
    source_ref: SourceRef = TUSHARE_SOURCE_REF,
    resolver: EntityResolver | None = None,
) -> tuple[Company, ListedEntity, Security, Listing, Industry | None, tuple[MarketFact, ...]]:
    resolver = resolver if resolver is not None else EntityResolver()
    identity = resolver.resolve_stock_basic(record)
    company_id = identity.company_id
    listed_entity_id = identity.listed_entity_id
    security_id = identity.security_id
    listing_id = identity.listing_id

    company = Company(
        company_id=company_id,
        name=record.name,
        aliases=identity.aliases,
        region=record.area,
        external_ids=identity.external_ids,
    )
    listed_entity = ListedEntity(
        listed_entity_id=listed_entity_id,
        company_id=company_id,
        disclosure_name=record.name,
        source_ref=source_ref,
    )
    security = Security(
        security_id=security_id,
        listed_entity_id=listed_entity_id,
        ts_code=record.ts_code,
        symbol=record.symbol,
        name=record.name,
        exchange=record.exchange,
    )
    listing = Listing(
        listing_id=listing_id,
        security_id=security_id,
        exchange=record.exchange,
        board=_board_from_market(record.market),
        listed_at=record.list_date,
        status=record.list_status,
    )
    industry = (
        Industry(
            industry_id=industry_id_from_name(record.industry),
            taxonomy="tushare",
            name=record.industry,
        )
        if record.industry
        else None
    )
    facts = build_company_profile_facts(record, identity, source_ref=source_ref)
    return company, listed_entity, security, listing, industry, facts


def map_daily_quote(
    record: TushareDailyRecord,
    *,
    source_ref: SourceRef = TUSHARE_SOURCE_REF,
    resolver: EntityResolver | None = None,
) -> QuoteSnapshot:
    resolver = resolver if resolver is not None else EntityResolver()
    security_id = resolver.security_id_for(record.ts_code)
    return QuoteSnapshot(
        quote_id=f"quote:tushare:{record.ts_code.lower()}:{record.trade_date.isoformat()}",
        security_id=security_id,
        trade_date=record.trade_date,
        open=record.open,
        high=record.high,
        low=record.low,
        close=record.close,
        previous_close=record.pre_close,
        volume=record.vol,
        amount=record.amount,
        source_ref=source_ref.model_copy(update={"captured_at": datetime.now(timezone.utc)}),
    )


def _board_from_market(value: str | None) -> Board:
    if value == "主板":
        return Board.MAIN
    if value == "中小板":
        return Board.SME
    if value == "创业板":
        return Board.CHINEXT
    if value == "科创板":
        return Board.STAR
    if value == "北交所":
        return Board.BSE
    return Board.UNKNOWN
