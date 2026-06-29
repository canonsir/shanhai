/**
 * TypeScript mirror of the ShanHai Market Data payloads
 * (services/market-data/shanhai_market_data/models.py + api.py).
 *
 * These types are intentionally faithful to the backend Pydantic models. If the
 * console cannot render a section naturally from these shapes, that is a signal
 * the knowledge model — not the UI — needs to change.
 */

export type FactType =
  | "quote"
  | "financial"
  | "announcement"
  | "news"
  | "industry"
  | "profile"
  | "policy"
  | "anomaly"
  | "capital_flow"
  | "shareholder";

export type TimeBasis = "occurred_at" | "published_at" | "captured_at";

export type AnnouncementType =
  | "periodic_report"
  | "earnings_preview"
  | "dividend"
  | "major_contract"
  | "merger_acquisition"
  | "regulatory_inquiry"
  | "risk_warning"
  | "shareholder_change"
  | "other";

export type SourceTrustLevel =
  | "L1_official"
  | "L2_licensed_aggregator"
  | "L3_public_aggregator"
  | "L4_derived";

export interface SourceRef {
  source_id: string;
  source_name: string;
  trust_level: SourceTrustLevel;
  external_id: string | null;
  captured_at: string;
}

export interface SubjectRef {
  entity_type: string;
  entity_id: string;
  label: string | null;
}

export interface FactAttribute {
  key: string;
  value: string;
}

export interface EntityLink {
  entity_type: string;
  entity_id: string | null;
  mention: string | null;
  resolver: string;
  confidence: number;
  reason: string;
}

export interface Company {
  company_id: string;
  name: string;
  aliases: string[];
  region: string | null;
  external_ids: string[];
}

export interface ListedEntity {
  listed_entity_id: string;
  company_id: string;
  disclosure_name: string;
  source_ref: SourceRef;
}

export interface Security {
  security_id: string;
  listed_entity_id: string;
  ts_code: string;
  symbol: string;
  name: string;
  exchange: string;
  security_type: string;
  currency: string;
}

export interface Listing {
  listing_id: string;
  security_id: string;
  exchange: string;
  board: string;
  listed_at: string | null;
  delisted_at: string | null;
  status: string;
}

export interface Industry {
  industry_id: string;
  taxonomy: string;
  name: string;
  code: string | null;
  level: number | null;
}

export interface QuoteSnapshot {
  quote_id: string;
  security_id: string;
  trade_date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  previous_close: number | null;
  volume: number | null;
  amount: number | null;
  source_ref: SourceRef;
}

export interface MarketFact {
  fact_id: string;
  fact_type: FactType;
  subject_ref: SubjectRef;
  predicate: string;
  object_value: string;
  object_ref: SubjectRef | null;
  occurred_at: string | null;
  published_at: string | null;
  captured_at: string;
  source_ref: SourceRef;
  evidence_refs: string[];
  confidence: number;
  entity_links: EntityLink[];
  attributes: FactAttribute[];
  schema_version: string;
}

export interface FinancialFact {
  fact_id: string;
  subject_ref: SubjectRef;
  report_period: string;
  report_type: string;
  metric_name: string;
  metric_value: number | null;
  unit: string;
  currency: string;
  yoy: number | null;
  qoq: number | null;
  restated: boolean;
  occurred_at: string | null;
  published_at: string | null;
  captured_at: string;
  source_ref: SourceRef;
  confidence: number;
  fact_type: FactType;
  schema_version: string;
}

export interface AnnouncementFact {
  fact_id: string;
  subject_ref: SubjectRef;
  announcement_id: string;
  announcement_type: AnnouncementType;
  title: string;
  published_at: string | null;
  occurred_at: string | null;
  captured_at: string;
  document_url: string;
  document_hash: string;
  extracted_summary: string;
  mentioned_entities: EntityLink[];
  source_ref: SourceRef;
  confidence: number;
  fact_type: FactType;
  schema_version: string;
}

export interface CompanyTimelineEvent {
  event_id: string;
  company_id: string;
  event_time: string;
  event_time_basis: TimeBasis;
  event_type: FactType;
  title: string;
  summary: string;
  fact_refs: string[];
  source_refs: SourceRef[];
  confidence: number;
}

/** Payload of GET /companies/{ts_code} and items of /companies, /companies/search. */
export interface CompanyIntelligence {
  company: Company;
  listed_entity: ListedEntity;
  security: Security;
  listing: Listing;
  industry: Industry | null;
  latest_quote: QuoteSnapshot | null;
  facts: MarketFact[];
  financial_facts: FinancialFact[];
  announcement_facts: AnnouncementFact[];
  timeline: CompanyTimelineEvent[];
  source_refs: SourceRef[];
}

/** Payload of GET /companies/{ts_code}/timeline. */
export interface CompanyTimeline {
  company: Company;
  security: Security;
  time_basis: TimeBasis;
  events: CompanyTimelineEvent[];
}
