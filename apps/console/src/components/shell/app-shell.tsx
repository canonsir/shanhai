"use client";

import * as React from "react";
import { motion, useReducedMotion } from "framer-motion";
import { Sidebar } from "@/components/shell/sidebar";
import { Topbar } from "@/components/shell/topbar";

const SIDEBAR_WIDTH = 248;
const RAIL_WIDTH = 56;

/**
 * Full-viewport application shell: a sidebar that collapses to a minimum-width
 * icon rail (Manus-style — never fully hidden) + 52px topbar + a single
 * full-height scroll area for page content.
 *
 * Mirrors the structure of design-system/shanhai-console/ui_kits/dashboard,
 * mapped to ShanHai's company-research domain (no chat/agent UI).
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = React.useState(false);
  const reduce = useReducedMotion();

  return (
    <div className="flex h-dvh overflow-hidden bg-background">
      <motion.aside
        initial={false}
        animate={{ width: collapsed ? RAIL_WIDTH : SIDEBAR_WIDTH }}
        transition={reduce ? { duration: 0 } : { duration: 0.22, ease: "easeOut" }}
        className="hidden shrink-0 overflow-hidden border-r md:block"
      >
        <Sidebar collapsed={collapsed} />
      </motion.aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onToggleSidebar={() => setCollapsed((v) => !v)} />
        <main className="min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-5xl px-6 py-8">{children}</div>
        </main>
      </div>
    </div>
  );
}
