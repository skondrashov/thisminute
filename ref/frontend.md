# Frontend Reference

Read this if your task touches the frontend (HTML, CSS, JS, UI behavior).

## UI Layout

- **Left sidebar** (400px): All filter controls + Situations/Events navigation
- **Right info-panel** (340px, fixed): Unified story viewer for any context
- **Map**: Globe/flat with heatmap, dots, country polygons
- **Mobile**: Bottom sheet with drag handle, reticle + preview card on map

## Filter System

Filters are orthogonal AND dimensions — each narrows independently:

- **Topic**: Topic chips in filter drawer
- **Source**: Source chips in sources-popup (click source count in stats bar)
- **Time**: Dropdown (1h, 3h, 6h, 12h, 24h, 48h, 7d, all)
- **Sentiment**: Opinion toggle in filter drawer
- **Situation**: Click a situation in left sidebar
- **Location**: Click a country or point on the map
- **Domain**: Space/Internet buttons (top-right, glow when they have stories)

## Key UI Patterns

- Situations are collapsible: collapsed = title + count; click to expand + select
- Clicking any item (situation/event/map/space/internet) opens the right panel
- `closeInfoPanel()` cleans up all state (feed, location filter, button highlights)
- `openInfoPanel()` clears feed theming; feed callers reapply after
- `updateFeedButtonCounts()` adds `.has-stories` class for glow effect
- `computeFilteredState()` is the single source of truth for all filtered UI
- All renderers are pure consumers — no renderer does its own filtering

## Cache Busting

**Every deploy MUST bump `?v=N`** in index.html for both CSS and JS links. The browser aggressively caches these files. Forgetting this is the #1 cause of "my changes didn't work."

## Pitfalls

- **`#sidebar-header` MUST have `position: relative`** — without it, the theme toggle's `position: absolute` resolves against the viewport and overlaps the feed buttons.
- **Light/dark mode parity** — every new UI element needs both dark (base) and `body.light-mode` CSS rules. Frequently missed for: active states, expanded sub-items, close buttons, badges.
- **`sourceCounts` is an array of `{source, count}` objects**, not a plain object. Don't use `Object.entries()` on it.
- **MapLibre 5.x**: `sky` property replaces `setFog()`. Antimeridian-crossing polygons (Russia) must be split in the GeoJSON.
- **`_animateCount()`** runs 20 steps × 30ms = 600ms. Tests reading `#stat-showing` mid-animation get wrong values.
- **`replace_all` on template strings**: check that referenced variables exist in ALL template contexts, not just one.

## Quality Signals

- Does clicking a situation/event open the right panel with correct stories?
- Do Space/Internet buttons glow when they have stories?
- Does the right panel show themed backgrounds for Space/Internet?
- Does light mode look correct for ALL elements (especially active/expanded states)?
- Does the location filter dim other areas and brighten the selected one?
- Does cross-view highlighting work (sidebar -> map -> right panel)?

## Key Files

```
static/index.html      # HTML shell, ?v=N cache busters
static/js/app.js       # All frontend logic (bundled from src/js/)
static/css/style.css   # All styles (dark base + light-mode overrides)
src/js/main.js         # Main JS source (bundled by esbuild)
src/js/state.js        # Shared state, constants, domain colors
src/js/store.js        # computeFilteredState() — centralized filter logic
src/js/mobile.js       # Mobile bottom sheet, drag, refresh
src/js/map-labels.js   # Map layers, word cloud, country polygons
src/js/stats.js        # Stats bar, animated counters, freshness
src/js/animations.js   # Network/space feed animations
```
