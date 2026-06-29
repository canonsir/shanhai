"use client";

import * as React from "react";
import Link from "next/link";
import { Search, ArrowRight } from "lucide-react";
import { listCompanies, searchCompanies } from "@/lib/api";
import type { CompanyIntelligence } from "@/lib/types";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

export function CompanySearch() {
  const [query, setQuery] = React.useState("");
  const [items, setItems] = React.useState<CompanyIntelligence[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [loaded, setLoaded] = React.useState(false);

  const run = React.useCallback(async (q: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = q.trim()
        ? await searchCompanies(q.trim())
        : await listCompanies();
      setItems(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setItems([]);
    } finally {
      setLoading(false);
      setLoaded(true);
    }
  }, []);

  React.useEffect(() => {
    void run("");
  }, [run]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">
          Company Intelligence
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          搜索一家 A 股公司，进入其认知视图，验证实体与事实模型。
        </p>
      </div>

      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void run(query);
        }}
      >
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="公司名称 / 代码，如 贵州茅台 或 600519"
            className="pl-9"
            autoFocus
          />
        </div>
      </form>

      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="py-4 text-sm text-red-700">
            无法连接 Market Data API：{error}
            <div className="mt-1 text-xs text-red-500">
              请确认 FastAPI 已启动，并已运行 Tushare ingestion。
            </div>
          </CardContent>
        </Card>
      )}

      {loading && (
        <p className="text-sm text-muted-foreground">加载中…</p>
      )}

      {!loading && loaded && items.length === 0 && !error && (
        <p className="text-sm text-muted-foreground">
          无结果。请先运行 Tushare ingestion，或更换搜索词。
        </p>
      )}

      <div className="grid gap-3">
        {items.map((item) => (
          <Link
            key={item.security.security_id}
            href={`/company/${encodeURIComponent(item.security.ts_code)}`}
            className="group"
          >
            <Card className="transition-colors group-hover:border-ring">
              <CardContent className="flex items-center justify-between py-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{item.company.name}</span>
                    <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
                      {item.security.ts_code}
                    </code>
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                    {item.industry && (
                      <Badge variant="muted">{item.industry.name}</Badge>
                    )}
                    {item.company.region && (
                      <span>{item.company.region}</span>
                    )}
                    <span className="font-mono">
                      {item.listing.exchange} / {item.listing.board}
                    </span>
                  </div>
                </div>
                <ArrowRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
