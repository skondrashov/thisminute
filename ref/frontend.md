# Frontend Reference

Read this if your task touches the frontend (HTML, CSS, JS, UI behavior).

## UI Layout

- **Left sidebar** (400px): All filter controls + Situations/Events navigation
- **Right info-panel** (340px, fixed): Unified story viewer for any context
- **Map**: Globe projection (always — no flat/mercator switch). Dots, country polygons, event labels
- **Mobile**: Bottom sheet with drag handle, reticle + preview card on map center. Hover tooltip disabled on mobile (mousemove handler returns early). Map controls stripped to labels toggle + collapsible legend

## Filter System

Filters are orthogonal AND dimensions — each narrows independently:

- **Topic**: Topic chips in filter drawer
- **Source**: Source chips in sources-popup (click source count in stats bar). Multi-select — popup stays open on chip click
- **Time**: Dropdown (1h, 3h, 6h, 12h, 24h, 48h, 7d, all)
- **Sentiment**: Opinion toggle in filter drawer
- **Situation**: Click a situation in left sidebar
- **Location**: Click a country or point on the map
- **Domain**: Space/Internet buttons (top-right, glow when they have stories)
- **Search**: Searches within active preset and refinement filters. Shows "N hidden by filters" hint when matches exist outside current filters

## Key UI Patterns

- Situations are collapsible: collapsed = title + count; click to expand + select
- Clicking any item (situation/event/map/space/internet) opens the right panel
- `closeInfoPanel()` cleans up all state (feed, location filter, button highlights)
- `openInfoPanel()` clears feed theming; feed callers reapply after
- `updateFeedButtonCounts()` adds `.has-stories` class for glow effect
- `computeFilteredState()` is the single source of truth for all filtered UI
- All renderers are pure consumers — no renderer does its own filtering
- **Popup dismiss cascade**: `state._popupDismissing` flag prevents closing one popup from opening another. All click-outside handlers call `_markPopupDismiss()`. Map click handlers check the flag

## Preset Bar

- **Icon+label buttons** for all presets. `PRESET_SHORT_LABELS` abbreviates "Entertainment" to "Ent."
- **Flex-wrap on desktop**. Preset buttons wrap to additional rows
- **Filter status line** shows active time/filter count below the preset bar
- **Default preset is All Stories** (id: `"all"`). No preset tinting on All Stories
- **Unique domain-colored active states** — CSS active backgrounds are darkened variants of the brand colors. All pass WCAG AA 4.5:1 with white text
- **Manage presets panel** — accessed from hamburger menu "Manage presets". Drag-to-reorder (HTML5 DnD), remove button per preset, "Show removed" section with add-back. Hint text "Drag to reorder" inline with header
- **Preset dropdown** — click active preset label to open dropdown menu for quick switching

## Dot Color Blending

- **Domain theme active** (theme selector hidden, tracked in BACKLOG.md). `tm_dot_theme` localStorage cleared on load to prevent stale values
- **Domain theme**: `_blendLocationColors()` finds the dominant domain at each location, calculates `ratio = dominant_count / total_stories`, then RGB-lerps from a base color to the domain color. Preset-tinted: domain theme tints dots toward active preset color (skipped for "all" preset)
- **Theme-aware bases**: Dark mode = white (`#ffffff`, dots look like city lights). Light mode = medium gray (`#6e7681`)
- `toggleTheme()` triggers re-blend so dots update with the correct base color
- The `blended_color` property name is preserved for MapLibre layer compatibility

## Stats Bar

- Format: `N stories (X sources) · N shown · velocity`
- Source count set from API response (`/api/sources`), not from filtered counts
- Stats bar has `white-space: nowrap; overflow: hidden; text-overflow: ellipsis`

## SEO Files

- `static/og-image.png` — 1200x630 social preview image
- `static/robots.txt` — served at `/robots.txt` via FastAPI route
- `static/sitemap.xml` — served at `/sitemap.xml` via FastAPI route

## Cache Busting

**Every deploy MUST bump `?v=N`** in index.html for both CSS and JS links. The browser aggressively caches these files. Forgetting this is the #1 cause of "my changes didn't work."

## Pitfalls

- **Light/dark mode parity** — every new UI element needs both dark (base) and `body.light-mode` CSS rules. Frequently missed for: active states, expanded sub-items, close buttons, badges
- **`sourceCounts` is an array of `{source, count}` objects**, not a plain object. Don't use `Object.entries()` on it
- **MapLibre 5.x**: `sky` property replaces `setFog()`. Antimeridian-crossing polygons (Russia) must be split in the GeoJSON
- **`_animateCount()`** runs 20 steps × 30ms = 600ms. Tests reading `#stat-showing` mid-animation get wrong values
- **`replace_all` on template strings**: check that referenced variables exist in ALL template contexts, not just one
- **app.js is a build artifact edited directly** — the old `src/js/` source files no longer exist. The `package.json` esbuild config references `src/js/main.js` which doesn't exist. Any accidental `npm run build` would destroy edits

## Quality Signals

- Does clicking a situation/event open the right panel with correct stories?
- Do Space/Internet buttons glow when they have stories?
- Does the right panel show themed backgrounds for Space/Internet?
- Does light mode look correct for ALL elements (especially active/expanded states)?
- Does the location filter dim other areas and brighten the selected one?
- Does cross-view highlighting work (sidebar -> map -> right panel)?
- Does dismissing a popup (click away) avoid opening another popup?
- On mobile, does the reticle preview update as you pan? Does tapping it open the info panel?

## Key Files

```
static/index.html      # HTML shell, ?v=N cache busters
static/js/app.js       # All frontend logic (single file, ~5400 lines)
static/css/style.css   # All styles (dark base + light-mode overrides, ~4400 lines)
```
