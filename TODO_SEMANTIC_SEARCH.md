# Semantic Search

## What existed (removed in v60)

- `parseSearchQuery()` pattern-matched strings like "victim is Swedish" into structured params (`actor_role`, `actor_demographic`, `action`, `location_type`)
- `performSemanticSearch()` sent those params to `/api/search` which did SQL queries against `story_actors` and `story_extractions`
- When active, it completely overrode all other filters — replaced `geojsonData` with its own GeoJSON response
- Not actually semantic — just string pattern matching into structured SQL queries
- Removed because it broke the filter architecture (mode switch instead of composable filter) and wasn't being used

## API endpoint (still exists)

`GET /api/search` — multi-dimensional SQL search across stories, actors, extractions. Params:

- `actor_role`: perpetrator/victim/authority/witness/participant/target
- `actor_name`: partial match
- `actor_demographic`: partial match
- `action`: primary action (e.g. "airstrike", "arrested")
- `topic`: topic tag
- `severity_min`: 1-5
- `location_type`: terrestrial/space/internet/abstract
- `search`: free text

The endpoint works fine and can stay. The problem was only the frontend wiring.

## What real semantic search should do

Natural language queries that actually understand intent:

- "protests in Southeast Asia" → topic=protest + geocode region filter
- "climate disasters this week" → topic=climate/disaster + time=7d
- "who's sanctioning Russia" → actor search + action=sanction + location
- "what's happening in space" → location_type=space
- "violence against civilians" → actor_role=victim + severity_min=3

## Suggested implementation

1. User types a natural language query in the search box
2. After debounce, send query to LLM (Haiku) with a prompt like:
   "Given this search query, extract structured filter parameters: topics, actor_role, actor_demographic, action, location_type, severity_min, time_range, region/country"
3. LLM returns structured params
4. Those params become filter values in the centralized filter store — they COMPOSE with other active filters, not override
5. The existing `/api/search` endpoint can handle server-side actor/demographic queries that can't be done client-side
6. For things that CAN be done client-side (topics, time, location_type), just set the filter values directly

## Key design constraint

Semantic search must be a filter dimension, not a mode switch. Results must compose with topic, source, time, origin, and bright side filters. The centralized filter store makes this straightforward — semantic search just sets multiple filter values at once.
