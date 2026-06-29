"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Search, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { useRecentCompanies } from "@/lib/recent";
import { NAV } from "@/lib/nav";

const AVATAR_TONE = [
  "bg-chart-1",
  "bg-chart-2",
  "bg-chart-3",
  "bg-chart-4",
  "bg-chart-5",
];

function toneFor(key: string) {
  let h = 0;
  for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) | 0;
  return AVATAR_TONE[Math.abs(h) % AVATAR_TONE.length];
}

export function Sidebar({ collapsed = false }: { collapsed?: boolean }) {
  const pathname = usePathname();
  const router = useRouter();
  const recent = useRecentCompanies();
  const searchRef = React.useRef<HTMLInputElement>(null);
  const [q, setQ] = React.useState("");

  // ⌘K / Ctrl+K focuses the global search field.
  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        searchRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const term = q.trim();
    router.push(term ? `/?q=${encodeURIComponent(term)}` : "/");
  };

  return (
    <div className="flex h-full w-full flex-col bg-sidebar text-sidebar-foreground">
      {/* Brand */}
      <Link
        href="/"
        aria-label="ShanHai Console"
        className={cn(
          "flex items-center gap-2.5 pb-2 pt-4 text-sidebar-foreground",
          collapsed ? "justify-center px-2" : "px-4",
        )}
      >
        {/* Animated brand mark — plain <img> keeps the inline SMIL animation. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/logo.svg" alt="" className="size-7 shrink-0" />
        {!collapsed && (
          <span className="truncate text-sm font-semibold tracking-tight">
            ShanHai <span className="text-muted-foreground">Console</span>
          </span>
        )}
      </Link>

      {/* Global search (expanded) — collapses into an icon button on the rail */}
      {collapsed ? (
        <div className="flex justify-center px-2 pb-2 pt-1">
          <Link
            href="/"
            aria-label="搜索公司"
            title="搜索公司"
            className="grid size-9 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-background/60 hover:text-foreground"
          >
            <Search className="size-4" />
          </Link>
        </div>
      ) : (
        <div className="px-3.5 pb-2 pt-1">
          <form
            onSubmit={submit}
            className={cn(
              "flex h-9 items-center gap-2 rounded-md border border-transparent px-3",
              "bg-background/70 transition-colors focus-within:border-ring focus-within:bg-background",
            )}
          >
            <Search className="size-4 shrink-0 text-muted-foreground" />
            <input
              ref={searchRef}
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="搜索公司…"
              aria-label="全局搜索"
              className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
            <kbd className="rounded bg-muted-foreground/15 px-1.5 py-0.5 text-[0.7rem] font-semibold text-muted-foreground">
              ⌘K
            </kbd>
          </form>
        </div>
      )}

      {/* Primary navigation */}
      <nav
        aria-label="主导航"
        className={cn(
          "flex flex-col gap-0.5 py-1",
          collapsed ? "px-2" : "px-2.5",
        )}
      >
        {NAV.map((item) => {
          const active = item.match(pathname);
          const Icon = item.icon;
          const iconEl = (
            <Icon
              className={cn(
                "size-4 shrink-0",
                active ? "text-primary" : "text-foreground/70",
              )}
            />
          );

          if (collapsed) {
            const railBase =
              "grid size-9 place-items-center rounded-md transition-colors";
            if (item.soon) {
              return (
                <span
                  key={item.id}
                  aria-disabled
                  title={`${item.label}（即将上线）`}
                  className={cn(railBase, "cursor-not-allowed opacity-50")}
                >
                  {iconEl}
                </span>
              );
            }
            return (
              <Link
                key={item.id}
                href={item.href}
                aria-label={item.label}
                title={item.label}
                className={cn(
                  railBase,
                  active ? "bg-background" : "hover:bg-background/60",
                )}
              >
                {iconEl}
              </Link>
            );
          }

          const inner = (
            <>
              {iconEl}
              <span className="flex-1 truncate">{item.label}</span>
              {item.soon && (
                <span className="rounded bg-muted px-1.5 py-0.5 text-[0.65rem] text-muted-foreground">
                  soon
                </span>
              )}
            </>
          );
          const base =
            "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors";
          if (item.soon) {
            return (
              <span
                key={item.id}
                aria-disabled
                className={cn(base, "cursor-not-allowed text-muted-foreground")}
              >
                {inner}
              </span>
            );
          }
          return (
            <Link
              key={item.id}
              href={item.href}
              className={cn(
                base,
                active
                  ? "bg-background font-semibold text-foreground"
                  : "text-sidebar-foreground hover:bg-background/60",
              )}
            >
              {inner}
            </Link>
          );
        })}
      </nav>

      {/* Recently viewed companies */}
      <div
        className={cn(
          "flex min-h-0 flex-1 flex-col overflow-y-auto pb-3",
          collapsed ? "px-2" : "px-2.5",
        )}
      >
        {!collapsed && (
          <div className="flex items-center gap-1.5 px-3 pb-1.5 pt-3 text-xs text-muted-foreground">
            <Clock className="size-3.5" />
            最近查看
          </div>
        )}
        {collapsed ? (
          <div className="flex flex-col items-center gap-1 pt-3">
            {recent.map((c) => (
              <Link
                key={c.tsCode}
                href={`/company/${encodeURIComponent(c.tsCode)}`}
                aria-label={c.name}
                title={c.name}
                className={cn(
                  "grid size-7 place-items-center rounded text-[0.65rem] font-semibold text-primary-foreground transition-opacity hover:opacity-80",
                  toneFor(c.tsCode),
                )}
              >
                {c.name.slice(0, 1)}
              </Link>
            ))}
          </div>
        ) : recent.length === 0 ? (
          <p className="px-3 text-xs italic text-muted-foreground">
            暂无浏览记录
          </p>
        ) : (
          recent.map((c) => (
            <Link
              key={c.tsCode}
              href={`/company/${encodeURIComponent(c.tsCode)}`}
              className="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm text-foreground/80 transition-colors hover:bg-background/60 hover:text-foreground"
            >
              <span
                className={cn(
                  "grid size-[18px] shrink-0 place-items-center rounded text-[0.6rem] font-semibold text-primary-foreground",
                  toneFor(c.tsCode),
                )}
              >
                {c.name.slice(0, 1)}
              </span>
              <span className="flex-1 truncate">{c.name}</span>
            </Link>
          ))
        )}
      </div>

      {/* Footer status */}
      {!collapsed && (
        <div className="border-t px-4 py-3 text-xs text-muted-foreground">
          Knowledge Model Validator · M3.1 Alpha
        </div>
      )}
    </div>
  );
}
