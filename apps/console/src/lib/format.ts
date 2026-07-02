import type { AnnouncementType, FactType, TimeBasis } from "@/lib/types";

export function fmtDate(value: string | null | undefined): string {
  if (!value) return "—";
  return value.slice(0, 10);
}

export function fmtNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  // Large financial magnitudes get compacted; ratios/prices stay precise.
  if (Math.abs(value) >= 1e8)
    return (value / 1e8).toFixed(2) + " 亿";
  if (Math.abs(value) >= 1e4) return (value / 1e4).toFixed(2) + " 万";
  return String(value);
}

export const FACT_TYPE_LABEL: Record<FactType, string> = {
  quote: "行情",
  financial: "财务",
  announcement: "公告",
  news: "新闻",
  industry: "行业",
  profile: "资料",
  policy: "政策",
  anomaly: "异动",
  capital_flow: "资金流",
  shareholder: "股东",
};

export const ANNOUNCEMENT_TYPE_LABEL: Record<AnnouncementType, string> = {
  periodic_report: "定期报告",
  earnings_preview: "业绩预告",
  dividend: "分红",
  major_contract: "重大合同",
  merger_acquisition: "并购重组",
  regulatory_inquiry: "监管问询",
  risk_warning: "风险提示",
  shareholder_change: "股东变动",
  other: "其他",
};

export const TIME_BASIS_LABEL: Record<TimeBasis, string> = {
  occurred_at: "发生时间",
  published_at: "披露时间",
  captured_at: "采集时间",
};
