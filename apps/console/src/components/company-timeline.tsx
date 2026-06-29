"use client";

import * as React from "react";
import { getCompanyTimeline } from "@/lib/api";
import type { CompanyTimelineEvent, TimeBasis } from "@/lib/types";
import {
  FACT_TYPE_LABEL,
  TIME_BASIS_LABEL,
  fmtDate,
} from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const BASES: TimeBasis[] = ["published_at", "occurred_at", "captured_at"];

export function CompanyTimelineView({
  tsCode,
  initialEvents,
  initialBasis = "published_at",
}: {
  tsCode: string;
  initialEvents: CompanyTimelineEvent[];
  initialBasis?: TimeBasis;
}) {
  const [basis, setBasis] = React.useState<TimeBasis>(initialBasis);
  const [latestFirst, setLatestFirst] = React.useState(true);
  const [events, setEvents] = React.useState(initialEvents);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const reload = React.useCallback(
    async (nextBasis: TimeBasis, nextLatestFirst: boolean) => {
      setLoading(true);
      setError(null);
      try {
        const data = await getCompanyTimeline(tsCode, {
          timeBasis: nextBasis,
          latestFirst: nextLatestFirst,
        });
        setEvents(data?.events ?? []);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setLoading(false);
      }
    },
    [tsCode],
  );

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="text-muted-foreground">排序基准:</span>
        {BASES.map((b) => (
          <button
            key={b}
            onClick={() => {
              setBasis(b);
              void reload(b, latestFirst);
            }}
            className={
              "rounded-md border px-2 py-1 transition-colors " +
              (b === basis
                ? "border-ring bg-accent text-accent-foreground"
                : "hover:bg-muted")
            }
          >
            {TIME_BASIS_LABEL[b]}
          </button>
        ))}
        <span className="mx-1 text-border">|</span>
        <button
          onClick={() => {
            const next = !latestFirst;
            setLatestFirst(next);
            void reload(basis, next);
          }}
          className="rounded-md border px-2 py-1 hover:bg-muted"
        >
          {latestFirst ? "最新在前 ↓" : "最早在前 ↑"}
        </button>
        {loading && <span className="text-muted-foreground">加载中…</span>}
      </div>

      {error ? (
        <p className="text-sm italic text-red-600">
          时间线加载失败：{error}
        </p>
      ) : events.length === 0 ? (
        <p className="text-sm italic text-muted-foreground">时间线为空</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-28">时间</TableHead>
              <TableHead className="w-24">基准</TableHead>
              <TableHead className="w-20">类型</TableHead>
              <TableHead>标题</TableHead>
              <TableHead>摘要</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {events.map((e) => (
              <TableRow key={e.event_id}>
                <TableCell className="font-mono text-xs">
                  {fmtDate(e.event_time)}
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {TIME_BASIS_LABEL[e.event_time_basis]}
                </TableCell>
                <TableCell>
                  <Badge>{FACT_TYPE_LABEL[e.event_type] ?? e.event_type}</Badge>
                </TableCell>
                <TableCell className="text-sm">{e.title}</TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {e.summary || "—"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
