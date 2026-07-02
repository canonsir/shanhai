import {
  Search,
  Network,
  Newspaper,
  Bot,
  type LucideIcon,
} from "lucide-react";

/**
 * Single source of truth for primary navigation and topbar headings.
 *
 * Add a future route by appending one entry here — the sidebar (expanded +
 * collapsed rail) and the topbar title both derive from this manifest.
 */
export type NavItem = {
  id: string;
  label: string;
  icon: LucideIcon;
  href: string;
  /** Not yet shipped — rendered as a disabled rail entry. */
  soon?: boolean;
  /** True when this section owns the current pathname. */
  match: (pathname: string) => boolean;
  /** Topbar heading shown when this section is active. */
  title: string;
  sub: string;
};

export const NAV: NavItem[] = [
  {
    id: "company",
    label: "公司检索",
    icon: Search,
    href: "/",
    match: (p) => p === "/" || p.startsWith("/company"),
    title: "公司检索",
    sub: "Company Intelligence",
  },
  {
    id: "chain",
    label: "产业链",
    icon: Network,
    href: "/chain",
    soon: true,
    match: (p) => p.startsWith("/chain"),
    title: "产业链",
    sub: "Supply Chain",
  },
  {
    id: "events",
    label: "市场事件",
    icon: Newspaper,
    href: "/events",
    soon: true,
    match: (p) => p.startsWith("/events"),
    title: "市场事件",
    sub: "Market Events",
  },
  {
    id: "research",
    label: "Agent 研究",
    icon: Bot,
    href: "/research",
    soon: true,
    match: (p) => p.startsWith("/research"),
    title: "Agent 研究",
    sub: "Multi-Agent Research",
  },
];

export function activeNav(pathname: string): NavItem | undefined {
  return NAV.find((item) => item.match(pathname));
}
