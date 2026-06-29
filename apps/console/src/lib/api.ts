import type {
  CompanyIntelligence,
  CompanyTimeline,
  TimeBasis,
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

/**
 * Read-only client over the ShanHai Company Intelligence API.
 *
 * The console only consumes the existing endpoints; it never mutates market
 * data and never reaches into a database directly.
 */
async function getJson<T>(path: string): Promise<T | null> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

export async function listCompanies(
  limit = 50,
): Promise<CompanyIntelligence[]> {
  const data = await getJson<{ companies: CompanyIntelligence[] }>(
    `/companies?limit=${limit}`,
  );
  return data?.companies ?? [];
}

export async function searchCompanies(
  q: string,
  limit = 50,
): Promise<CompanyIntelligence[]> {
  const data = await getJson<{ companies: CompanyIntelligence[] }>(
    `/companies/search?q=${encodeURIComponent(q)}&limit=${limit}`,
  );
  return data?.companies ?? [];
}

export async function getCompany(
  tsCode: string,
): Promise<CompanyIntelligence | null> {
  return getJson<CompanyIntelligence>(
    `/companies/${encodeURIComponent(tsCode)}`,
  );
}

export async function getCompanyTimeline(
  tsCode: string,
  opts: { timeBasis?: TimeBasis; latestFirst?: boolean } = {},
): Promise<CompanyTimeline | null> {
  const params = new URLSearchParams({
    time_basis: opts.timeBasis ?? "published_at",
    latest_first: String(opts.latestFirst ?? true),
  });
  return getJson<CompanyTimeline>(
    `/companies/${encodeURIComponent(tsCode)}/timeline?${params.toString()}`,
  );
}

export { API_BASE };
