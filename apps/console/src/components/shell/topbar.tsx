"use client";

import * as React from "react";
import { usePathname } from "next/navigation";
import { PanelLeft, Moon, Sun } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTheme } from "@/lib/theme";
import { activeNav } from "@/lib/nav";

function titleFor(pathname: string): { title: string; sub: string } {
  if (pathname.startsWith("/company/")) {
    const ts = decodeURIComponent(pathname.split("/")[2] ?? "");
    return { title: "公司认知视图", sub: ts || "Company Intelligence" };
  }
  const nav = activeNav(pathname);
  if (nav) return { title: nav.title, sub: nav.sub };
  return { title: "公司检索", sub: "Company Intelligence" };
}

export function Topbar({ onToggleSidebar }: { onToggleSidebar: () => void }) {
  const pathname = usePathname();
  const [theme, toggleTheme] = useTheme();
  const { title, sub } = titleFor(pathname);

  return (
    <header className="flex h-[52px] shrink-0 items-center gap-3 border-b px-4">
      <button
        type="button"
        onClick={onToggleSidebar}
        aria-label="切换侧栏"
        className={iconBtn}
      >
        <PanelLeft className="size-[18px]" />
      </button>

      <div className="min-w-0">
        <div className="truncate text-sm font-semibold leading-tight">
          {title}
        </div>
        <div className="truncate text-xs text-muted-foreground">{sub}</div>
      </div>

      <div className="flex-1" />

      <button
        type="button"
        onClick={toggleTheme}
        aria-label={theme === "dark" ? "切换到浅色" : "切换到深色"}
        className={iconBtn}
      >
        {theme === "dark" ? (
          <Sun className="size-[18px]" />
        ) : (
          <Moon className="size-[18px]" />
        )}
      </button>
    </header>
  );
}

const iconBtn = cn(
  "grid size-[34px] place-items-center rounded-md text-muted-foreground",
  "transition-colors hover:bg-muted hover:text-foreground",
);
