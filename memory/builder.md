# Builder Memory

## Domain Event Filtering (2026-03-13)

- Entertainment events get heavy cross-coverage from general news sources (BBC, CNN, NYT all cover Oscars). A 50% entertainment-source threshold is too strict. Current threshold: 15% source ratio + topic-keyword secondary signal.
- Positive events: `bright_side_score >= 3` at 15% ratio works better than the original >= 4 at 30%. Also added source-based signal for positive-tagged feeds.
- Sports at 50% threshold works fine because sports sources dominate sports events (ESPN, BBC Sport, etc. are the primary reporters).
- The LLM prompt is the final quality gate -- it rejects junk/vague situations even if the event filter is permissive. Better to be too permissive on event filtering and let Sonnet decide quality.
- Topic-based matching uses LIKE against the JSON topics string. Requires >= 2 matching stories to avoid false positives.

## Deploy Script Notes

- `src/js/` is excluded from repo (filtered in `make_tarball()` and not committed). The pre-built `static/js/app.js` is what gets deployed.
- `deploy()` now conditionally runs `npm run build` only if `src/js/` exists. If missing, it skips the build and uses the pre-built bundle.
- `make_tarball()` explicitly excludes `src/js` from the tarball via the `dirs[:]` filter.

## Sports Clustering (2026-03-13)

- Sports event_signatures fragment badly when match-result-centric ("Wolves Beat Liverpool"). Fixed by adding sports-specific prompt guidance to generate tournament-centric signatures ("2026 Premier League").
- Three-part fix: (1) LLM prompt guidance, (2) post-clustering tournament merge pass, (3) fuzzy match boost for shared tournaments.
- Tournament detection uses 25+ regex patterns in `_SPORTS_TOURNAMENT_PATTERNS` covering all major sports.
- Sports events detected via feed source tags (>= 50% from `_SPORTS_SOURCES`). News events are never touched by sports merge logic.
- Key thresholds: `SPORTS_MERGE_THRESHOLD = 0.28` (lower than normal 0.35-0.45), tournament boost = +0.15 on fuzzy score.
- The prompt change is the most impactful: it changes how NEW signatures are generated. The merge pass fixes existing fragmented events.
- Tournament patterns may need expansion as new sports/competitions appear. Easy to add new patterns to the list.

## Entertainment Clustering (2026-03-13)

- Entertainment event_signatures fragment by individual news item ("Spider-Man 4 Casting" vs "Spider-Man 4 Filming"). Fixed by adding entertainment-specific prompt guidance to generate production/franchise-centric signatures ("Spider-Man 4 Production").
- Three-part fix (mirrors sports): (1) LLM prompt guidance, (2) post-clustering entertainment merge pass, (3) fuzzy match boost for shared entertainment keys.
- Entertainment detection uses 30% source ratio (lower than sports' 50%) because entertainment events get heavy cross-coverage from general news outlets (BBC, CNN, NYT all cover Oscars).
- Entertainment patterns cover: award shows (12 types), film festivals (10 types), movie franchises (12+), TV shows (6+), music tours (pattern-based), K-pop groups (4+), Broadway/West End, Bollywood.
- Key thresholds: `ENTERTAINMENT_MERGE_THRESHOLD = 0.28`, `ENTERTAINMENT_SOURCE_RATIO = 0.3`, entertainment boost = +0.15 on fuzzy score.
- The prompt change is most impactful: it changes how NEW signatures are generated. The merge pass fixes existing fragmented events.
- Cross-domain isolation verified: entertainment patterns don't match sports signatures and vice versa.

## Entertainment Pattern Disambiguation (2026-03-13)

- Patterns for common English words (succession, batman, wednesday, the bear) MUST require franchise/show-specific context words. Bare word matching causes false positives on news signatures.
- Greedy capture groups like `\w[\w\s]*?` after franchise names (star wars, harry potter) match nonsense -- use explicit word lists instead.
- Allow one optional intervening word between franchise name and context word (e.g., "Star Wars New Trilogy" needs `(?:\w+\s+)?` before `trilogy`).
- The `_best_event_match()` boost is domain-gated: sports boost only for confirmed sports events, entertainment boost only for confirmed entertainment events. Pre-compute domain sets in the caller via batch queries.

## Sports Narrative Prompt -- Cross-Sport Contamination (2026-03-13)

- The clustering layer (semantic_clusterer.py) correctly separates events by sport -- rugby events are separate from cricket events. But the Sonnet narrative prompt was too loose, grouping events from different sports into one situation.
- Root cause: the sports prompt said "a tournament, a season, a transfer saga" but never said "ONE sport per situation." Sonnet interpreted this as "group big sports events together" and created a cricket situation containing rugby, football, tennis, MMA, and motorsport events.
- Fix: added explicit "CRITICAL -- ONE SPORT PER SITUATION" guidance to `DOMAIN_PROMPTS["sports"]["guidance"]`. Also added cross-sport contamination to `examples_bad`.
- Key lesson: domain-specific prompts need EXPLICIT exclusion rules, not just good examples. Sonnet follows examples but generalizes liberally -- if you don't say "don't mix sports," it will mix them when the events seem related (e.g., both are "big international competitions").
- The fix takes effect on the next narrative analysis cycle (every 1-2 hours). Existing contaminated narratives should self-correct as Sonnet reassigns events.

## Curious/Human Interest Domain (2026-03-13)

- human_interest_score (1-10) is DIFFERENT from bright_side_score. Human interest = "this is fascinating/engaging." Bright side = "this is good news." A gripping war crime investigation is high human-interest but low bright-side. A routine charity donation is high bright-side but low human-interest.
- Curious domain uses human_interest_score >= 5 at 15% ratio (same architecture as positive domain's bright_side_score approach).
- Score 5 cutoff is appropriate: 5-6 in the rubric is "engaging -- surprising twist, dramatic confrontation, compelling human drama, odd science." Reserve 7+ for genuinely remarkable stories.
- The curious domain is source-agnostic (DOMAIN_FEED_TAGS = None). Human interest stories come from any source.
- The Sonnet prompt emphasizes "you won't believe this" factor and explicitly differentiates from positive domain. Rejects vague buckets like "human interest stories" and "viral content."
- Cap: 10 situations (same as sports/entertainment/positive).
- Phase 3 is now COMPLETE: all 5 domains generating (news, sports, entertainment, positive, curious).

## Key Thresholds (Updated)

| Domain | Source ratio | Extra signal |
|--------|-------------|--------------|
| News | 0.5 | None |
| Sports | 0.5 | None |
| Entertainment | 0.15 | Topic keywords (film, oscars, broadway, etc.) |
| Positive | N/A | bright_side_score >= 3 at 15% ratio OR 30% positive-source ratio |
| Curious | N/A | human_interest_score >= 5 at 15% ratio |

## Project Conventions

- `flush=True` on all prints (Windows subprocess buffers stdout)
- Avoid unicode in print statements (cp1252 encoding on Windows)
- SQLite with WAL mode and busy_timeout=10000
- Always add columns with DEFAULT values in migrations
- Bump `?v=N` in index.html on every deploy
