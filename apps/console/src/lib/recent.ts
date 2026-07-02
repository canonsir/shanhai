"use client";

import * as React from "react";

/**
 * Recently viewed companies, persisted to localStorage.
 *
 * The console has no backend "history" concept yet; the sidebar's "最近查看"
 * list is a pure client-side convenience that mirrors the reference shell's
 * history rail without inventing a server-side feature.
 */
export type RecentCompany = {
  tsCode: string;
  name: string;
  /** epoch ms of the last visit, newest first */
  at: number;
};

const KEY = "shanhai.console.recent-companies";
const LIMIT = 8;
const EVENT = "shanhai:recent-companies";

function read(): RecentCompany[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as RecentCompany[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function write(items: RecentCompany[]) {
  window.localStorage.setItem(KEY, JSON.stringify(items));
  window.dispatchEvent(new Event(EVENT));
}

export function recordRecentCompany(entry: Omit<RecentCompany, "at">) {
  if (typeof window === "undefined") return;
  const next = [
    { ...entry, at: Date.now() },
    ...read().filter((c) => c.tsCode !== entry.tsCode),
  ].slice(0, LIMIT);
  write(next);
}

export function useRecentCompanies(): RecentCompany[] {
  const [items, setItems] = React.useState<RecentCompany[]>([]);

  React.useEffect(() => {
    const sync = () => setItems(read());
    sync();
    window.addEventListener(EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  return items;
}
