# ShanHai Design Library

This directory contains the completed ShanHai design library for an AI dashboard product. The visual system is minimal, cool-toned, technical, and calm, with a token-first implementation that supports both light and dark themes.

## Overview

- Brand: ShanHai
- Product type: AI dashboard
- Kit type: dashboard
- Generation mode: inferred-from-tokens
- Language: English

## Included artifacts

The following artifacts were generated for this library:

- `README.md`
- `SKILL.md`
- `colors_and_type.css`
- `css.json`
- `components/index.json`
- `components/button.json`
- `components/search-input.json`
- `components/app-card.json`
- `components/sidebar-nav.json`
- `components/data-table.json`
- `components/chat-composer.json`
- `components/badge.json`
- `components/tabs.json`
- `components/text-input.json`
- `components/select.json`
- `components/switch.json`
- `components/tooltip.json`
- `components/modal.json`
- `components/toast.json`
- `components/empty-state.json`
- `components/skeleton.json`
- `components/alert.json`
- `components/metric-card.json`
- `components/timeline.json`
- `components/source-chip.json`
- `components/breadcrumb.json`
- `components/pagination.json`
- `components/avatar.json`
- `preview/component-button.html`
- `preview/component-search-input.html`
- `preview/component-app-card.html`
- `preview/component-sidebar-nav.html`
- `preview/component-data-table.html`
- `preview/component-chat-composer.html`
- `preview/component-badge.html`
- `preview/component-tabs.html`
- `preview/component-text-input.html`
- `preview/component-select.html`
- `preview/component-switch.html`
- `preview/component-tooltip.html`
- `preview/component-modal.html`
- `preview/component-toast.html`
- `preview/component-empty-state.html`
- `preview/component-skeleton.html`
- `preview/component-alert.html`
- `preview/component-metric-card.html`
- `preview/component-timeline.html`
- `preview/component-source-chip.html`
- `preview/component-breadcrumb.html`
- `preview/component-pagination.html`
- `preview/component-avatar.html`
- `ui_kits/dashboard/index.html`

No artifacts were skipped for this completed bundle.

## Token foundation

The library exposes 54 available CSS variables across color, typography, radius, spacing, and shadow groups.

- Primary brand color: `#0065fd`
- Light theme: `--background: #ffffff`, `--foreground: #0e1115`
- Dark theme: `--background: #0e1115`, `--foreground: #eff1f4`
- Font families: `Stack Sans Text`, `Source Serif 4`, `JetBrains Mono`
- Base radius: `19.2px`
- Base spacing unit: `3.84px`
- Semantic roles mapped: `background`, `foreground`, `primary`, `destructive`, `warning`
- Icons included: none

The system emphasizes subtle borders over visible elevation, compact dashboard spacing, and a single shared radius token for a clean, cohesive interface.

## Component inventory

The completed component set includes:

**Foundation**

1. `Button` — primary and secondary action patterns
2. `Search Input` — compact query entry for dashboard surfaces
3. `App Card` — content and app/module summary card
4. `Sidebar Navigation` — dashboard navigation rail and section structure
5. `Data Table` — structured tabular data presentation
6. `Chat Composer` — AI interaction input surface

**Controls & inputs**

7. `Badge` — status, category, and count labels
8. `Tabs` — section switching (underline / segmented)
9. `Text Input` — labeled single-line form field
10. `Select` — single-choice dropdown with grouped menu
11. `Switch` — binary on/off toggle for settings
12. `Tooltip` — on-hover explanation for icons and predicates

**Feedback & overlays**

13. `Modal` — focused overlay for confirm / form / detail
14. `Toast` — transient action feedback
15. `Empty State` — zero-data, no-results, and error placeholders
16. `Skeleton` — loading placeholders that mirror final layout
17. `Alert` — persistent inline contextual banner

**ShanHai knowledge & market**

18. `Metric Card` — KPI tile for price, market cap, PE, fact counts
19. `Timeline` — chronological knowledge timeline of facts and events
20. `Source Chip` — provenance marker (provider / captured_at / snapshot)
21. `Breadcrumb` — entity drill-down trail (industry → company → security)
22. `Pagination` — page navigation for tables and long fact lists
23. `Avatar` — identity marker for users, agents, companies, sources

Component metadata is indexed in `components/index.json`, and each component has both a JSON definition and an HTML preview page.

## Cross-component patterns

- Radius: use the shared `--radius` token and derived rounded controls
- Spacing: maintain compact dashboard density with a quiet vertical rhythm
- Border treatment: prefer border-led separation instead of shadow-heavy layering
- State model: use the blue brand primary for emphasis, muted surfaces for secondary actions, and destructive tokens for error or removal states

## Usage

Import the token stylesheet:

```css
@import "./colors_and_type.css";
```

Apply the `.dark` class to a parent element to activate dark mode tokens.

Use the preview HTML files and `ui_kits/dashboard/index.html` as implementation references for composing dashboard screens from the generated component set.

## Caveats

- Components are inferred from tokens rather than extracted from source component specifications.
- The source workflow indicates that component structures were inferred from the token system and product type because the source material defined tokens and theme mappings, not explicit component specs.

## File map

- `colors_and_type.css` — ready-to-use CSS custom properties
- `css.json` — structured token export
- `components/index.json` — component registry and shared usage patterns
- `components/*.json` — per-component definitions
- `preview/*.html` — standalone component previews
- `ui_kits/dashboard/index.html` — assembled dashboard UI kit example
