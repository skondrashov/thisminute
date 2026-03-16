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

## World Bar

- **Icon+label buttons** for all 12 world presets. `WORLD_SHORT_LABELS` abbreviates "Entertainment" to "Ent." and "Geopolitics" to "Geo".
- **Flex-wrap on desktop** (was horizontal scroll). World buttons wrap to additional rows.
- **Filter status line** shows active time/filter count below the world bar.
- **Default world is Positive** (was News).
- **12 unique domain-colored active states** — CSS active backgrounds are darkened variants of the brand colors (e.g., positive `#a06800` not `#f5a623`). All pass WCAG AA 4.5:1 with white text. Full color overhaul: Tech=hot pink, Curious=orange, Markets=dark teal, etc. (no more color collisions).
- **Share button** (`#world-share-btn`) copies current URL to clipboard. Uses `_worldShareFallback()` for older browsers. Visual feedback: checkmark + green border for 1.5s.
- **Replay tour** menu item in hamburger menu lets users re-run the auto-cycling world tour.
- `renderWorldsBar()` inserts world buttons before `#world-share-btn` to maintain correct DOM order.

## Dot Color Blending

- **5 switchable themes**: domain (default), classic, mono, heat, neon. Persisted as `tm_dot_theme` in localStorage.
- **Domain theme**: `_blendLocationColors()` finds the dominant domain at each location, calculates `ratio = dominant_count / total_stories`, then RGB-lerps from a base color to the domain color. World-tinted: domain theme tints dots toward active world color.
- **Classic theme**: Uses world color directly for all dots.
- **Theme-aware bases**: Dark mode = white (`#ffffff`, dots look like city lights). Light mode = medium gray (`#6e7681`).
- **Palette button**: In mobile controls tray (not standalone on mobile). Popup menu near legend area on desktop.
- `toggleTheme()` triggers re-blend so dots update with the correct base color.
- The `blended_color` property name is preserved for MapLibre layer compatibility. Country polygon fills use a separate code path (already dominant-domain based).

## Welcome Questionnaire

- **Replaces world picker** in first-visit flow. 6 personality cards presented after world tour ends.
- Selection personalizes the world bar (saved to `tm_visible_worlds` in localStorage).
- Accessible later via main menu "Pick worlds" item.
- All cards selected by default -- dismissing keeps everything. Empty selection treated as all-selected.
- Bidirectional sync with eye toggles in worlds panel.

## SEO Files

- `static/og-image.png` — 1200x630 social preview image
- `static/robots.txt` — served at `/robots.txt` via FastAPI route
- `static/sitemap.xml` — served at `/sitemap.xml` via FastAPI route
- Dynamic OG in `app.py` replaces meta tags for `/?sit=N` deep links. String replacements must match exact text in `index.html`.

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
