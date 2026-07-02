# ShanHai Design Library Skill

Use this design library for English-language AI dashboard experiences that should feel minimal, cool-toned, technical, and calm. The library is complete, but its component model was inferred from the token system rather than extracted from authored component specs, so prefer consistency with the shared tokens and preview pages when extending it.

## Snapshot

- Library: `shanhai`
- Brand: `ShanHai`
- Product type: `AI dashboard`
- Kit type: `dashboard`
- Language: `en`
- Generation mode: `inferred-from-tokens`
- Generated artifacts: `README.md`, `SKILL.md`, `colors_and_type.css`, `css.json`, `components/index.json`, `components/button.json`, `components/search-input.json`, `components/app-card.json`, `components/sidebar-nav.json`, `components/data-table.json`, `components/chat-composer.json`, `components/badge.json`, `components/tabs.json`, `components/text-input.json`, `components/select.json`, `components/switch.json`, `components/tooltip.json`, `components/modal.json`, `components/toast.json`, `components/empty-state.json`, `components/skeleton.json`, `components/alert.json`, `components/metric-card.json`, `components/timeline.json`, `components/source-chip.json`, `components/breadcrumb.json`, `components/pagination.json`, `components/avatar.json`, `preview/component-button.html`, `preview/component-search-input.html`, `preview/component-app-card.html`, `preview/component-sidebar-nav.html`, `preview/component-data-table.html`, `preview/component-chat-composer.html`, `preview/component-badge.html`, `preview/component-tabs.html`, `preview/component-text-input.html`, `preview/component-select.html`, `preview/component-switch.html`, `preview/component-tooltip.html`, `preview/component-modal.html`, `preview/component-toast.html`, `preview/component-empty-state.html`, `preview/component-skeleton.html`, `preview/component-alert.html`, `preview/component-metric-card.html`, `preview/component-timeline.html`, `preview/component-source-chip.html`, `preview/component-breadcrumb.html`, `preview/component-pagination.html`, `preview/component-avatar.html`, `ui_kits/dashboard/index.html`
- Skipped artifacts: `none`

## Token System Summary

- CSS variable coverage: 55 variables, no icon set bundled
- Primary action color: `--primary` = `#0065fd`
- App background: `--background` = `#ffffff`
- Main text: `--foreground` = `#0e1115`
- Muted surface: `--muted` = `#eff1f4`
- Border color: `--border` = `#e7eaef`
- Focus ring: `--ring` = `#557fff`
- Sidebar surface: `--sidebar` = `#eff1f4`
- Shared radius: `--radius` = `19.2px`
- Shared spacing unit: `--spacing` = `3.84px`
- Sans font: `Stack Sans Text, ui-sans-serif, sans-serif, system-ui`
- Serif font: `Source Serif 4, serif`
- Mono font: `JetBrains Mono, monospace`
- Shadow direction: minimal elevation with border-led separation

## Implementation Guidance

1. Keep layouts compact and dashboard-dense by scaling spacing from the single global spacing token.
2. Prefer crisp borders and tonal contrast over visible drop shadows.
3. Use the shared radius token consistently so controls feel rounded but still technical.
4. Use brand blue for primary actions, muted surfaces for secondary actions, and destructive tokens only for destructive intent.
5. Follow preview pages first when deciding spacing, hierarchy, and component composition.

## Semantic Roles

- `background` -> `background`
- `foreground` -> `foreground`
- `primary` -> `primary`
- `destructive` -> `destructive`
- `warning` -> `warning`

## Quick Map

### Components

- `components/button.json` -> Button (`action`) -> preview: `preview/component-button.html`
- `components/search-input.json` -> Search Input (`form`) -> preview: `preview/component-search-input.html`
- `components/app-card.json` -> App Card (`content`) -> preview: `preview/component-app-card.html`
- `components/sidebar-nav.json` -> Sidebar Navigation (`navigation`) -> preview: `preview/component-sidebar-nav.html`
- `components/data-table.json` -> Data Table (`data-display`) -> preview: `preview/component-data-table.html`
- `components/chat-composer.json` -> Chat Composer (`ai-interaction`) -> preview: `preview/component-chat-composer.html`
- `components/badge.json` -> Badge (`data-display`) -> preview: `preview/component-badge.html`
- `components/tabs.json` -> Tabs (`navigation`) -> preview: `preview/component-tabs.html`
- `components/text-input.json` -> Text Input (`form`) -> preview: `preview/component-text-input.html`
- `components/select.json` -> Select (`form`) -> preview: `preview/component-select.html`
- `components/switch.json` -> Switch (`form`) -> preview: `preview/component-switch.html`
- `components/tooltip.json` -> Tooltip (`overlay`) -> preview: `preview/component-tooltip.html`
- `components/modal.json` -> Modal (`overlay`) -> preview: `preview/component-modal.html`
- `components/toast.json` -> Toast (`feedback`) -> preview: `preview/component-toast.html`
- `components/empty-state.json` -> Empty State (`feedback`) -> preview: `preview/component-empty-state.html`
- `components/skeleton.json` -> Skeleton (`feedback`) -> preview: `preview/component-skeleton.html`
- `components/alert.json` -> Alert (`feedback`) -> preview: `preview/component-alert.html`
- `components/metric-card.json` -> Metric Card (`data-display`) -> preview: `preview/component-metric-card.html`
- `components/timeline.json` -> Timeline (`data-display`) -> preview: `preview/component-timeline.html`
- `components/source-chip.json` -> Source Chip (`data-display`) -> preview: `preview/component-source-chip.html`
- `components/breadcrumb.json` -> Breadcrumb (`navigation`) -> preview: `preview/component-breadcrumb.html`
- `components/pagination.json` -> Pagination (`navigation`) -> preview: `preview/component-pagination.html`
- `components/avatar.json` -> Avatar (`data-display`) -> preview: `preview/component-avatar.html`

### Preview

- `preview/component-button.html` -> primary and secondary action reference
- `preview/component-search-input.html` -> compact search field reference
- `preview/component-app-card.html` -> application/content card reference
- `preview/component-sidebar-nav.html` -> dashboard sidebar navigation reference
- `preview/component-data-table.html` -> dense tabular data reference
- `preview/component-chat-composer.html` -> AI input/composer reference
- `preview/component-badge.html` -> status / category / count label reference
- `preview/component-tabs.html` -> underline and segmented tab reference
- `preview/component-text-input.html` -> labeled form field reference
- `preview/component-select.html` -> dropdown trigger and grouped menu reference
- `preview/component-switch.html` -> toggle and setting row reference
- `preview/component-tooltip.html` -> hover explanation and provenance hint reference
- `preview/component-modal.html` -> confirm and form overlay reference
- `preview/component-toast.html` -> transient feedback stack reference
- `preview/component-empty-state.html` -> zero-data / no-results / error reference
- `preview/component-skeleton.html` -> loading placeholder reference
- `preview/component-alert.html` -> persistent inline banner reference
- `preview/component-metric-card.html` -> KPI tile and trend reference
- `preview/component-timeline.html` -> knowledge timeline reference
- `preview/component-source-chip.html` -> provenance marker reference
- `preview/component-breadcrumb.html` -> entity drill-down trail reference
- `preview/component-pagination.html` -> table page navigation reference
- `preview/component-avatar.html` -> identity marker reference

### UI Kit

- `ui_kits/dashboard/index.html` -> assembled ShanHai dashboard kit reference

## Core Files

- `colors_and_type.css` -> production-ready token CSS
- `css.json` -> structured token export
- `components/index.json` -> library manifest and cross-component rules
- `README.md` -> general library overview
- `SKILL.md` -> implementation-oriented usage guidance

## Warnings

- Components were inferred from the token system and product type because the source material did not include authored component specs.
- Treat preview files and shared tokens as the source of truth when expanding the library.
