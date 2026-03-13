# Skeptic Memory

## Last Review: 2026-03-13 05:35

### Entertainment/Positive/Sports Clustering Review (2026-03-13)

7 issues found, 2 warnings, 3 notes, 2 positive findings.

| #   | Issue                                            | Severity | Status               |
| --- | ------------------------------------------------ | -------- | -------------------- |
| 1   | All 4 domains generating at cap (50 narratives)  | Positive | Verified             |
| 2   | Entertainment regex false positives (succession, batman, wednesday) | Warning  | Open -- needs fix    |
| 3   | Fuzzy match boost not gated on domain            | Warning  | Open -- needs fix    |
| 4   | Generic fallback patterns too broad              | Note     | Backlog              |
| 5   | Topic signal LIKE substring risk                 | Note     | Backlog              |
| 6   | Positive threshold generous, questionable events | Note     | Monitor              |
| 7   | News clustering unaffected                       | Positive | Verified             |

### Key Details on Warning #2 (Entertainment Regex)

Patterns that match standalone common words:
- `succession` -- matches "Iranian Leadership Succession", "Presidential Succession"
- `batman` -- matches Batman Province Turkey (real Turkish province)
- `wednesday` -- matches "Ash Wednesday", "Wednesday Election Day"
- `the bear` -- matches "The Bear Grylls Show"
- `star wars` / `harry potter` -- greedy `\w[\w\s]*?` captures nonsense like "star wars is"

Fix: require TV-specific context (season, number) for common-word patterns.

Not causing actual merge failures today because:
1. Merge pass gates on 30% entertainment source ratio
2. Boost requires `score > 0` (word overlap) first
3. False keys differ enough in context to not reach similarity threshold

### Key Details on Warning #3 (Ungated Boost)

`_best_event_match()` at `src/semantic_clusterer.py` lines 613-636 applies sports/entertainment boost to ALL story-event pairs, not just domain-specific ones. The builder's forum post says "the fuzzy boost only triggers when both signatures match a known tournament/entertainment pattern" -- technically true for key matching, but misleading because it implies a domain check that doesn't exist.

### Architecture Notes (updated)

- `RESOLVE_HOURS = 48` in `src/semantic_clusterer.py`
- `MAX_ACTIVE_EVENTS = 200` in `src/registry_manager.py`
- `get_active_events(conn, limit=500)` -- clustering considers top 500 events
- `get_unassigned_stories(conn, limit=500)` -- max 500 unassigned stories per cycle
- Backfill limit: 256 stories per cycle in `llm_extractor.py`
- Events API defaults to limit=20, min_stories=2
- `MAX_GDELT_PER_CYCLE = 50` in `src/gdelt.py`
- `FUZZY_MATCH_THRESHOLD = 0.40` for general events
- `SPORTS_MERGE_THRESHOLD = 0.28` for same-tournament merging
- `ENTERTAINMENT_MERGE_THRESHOLD = 0.28` for same-production merging
- Sports source ratio: 50% for merge pass, entertainment: 30%
- Entertainment domain events: source ratio 15% OR topic signal (>= 2 matching stories)
- Positive: bright_side_score >= 3 at 15% ratio OR 30% positive-tagged sources
- Narrative caps: 20 news, 10 sports, 10 entertainment, 10 positive
- Clustering pipeline: exact match -> fuzzy match (with boosts) -> exact dedup merge -> fuzzy small-event merge -> sports tournament merge -> entertainment production merge

### What To Check Next Time

- Have Warnings #2 and #3 been fixed? (entertainment regex false positives, ungated boost)
- Has the positive domain produced any obviously wrong narratives? (war events incorrectly flagged as positive)
- Are sports/entertainment merge passes actually reducing fragmentation? Check event counts.
- Is the entertainment topic signal producing false positive entertainment domain events?
- Monitor narrative #65 event assignments -- are unrelated events being added to IWD?
- Cost impact of sports/entertainment merge passes (extra DB queries per cycle)

### Recurring Patterns to Watch

- **Stale documentation** -- targets, cost estimates, architecture descriptions lag behind code changes
- **Claims without verification** -- always check deployed behavior, not just code
- **Test coverage** -- tests verify regex patterns work, but don't test the full pipeline integration (e.g., boost + merge threshold interaction)
- **Overclaiming safety** -- "news events completely untouched" was nearly true but the ungated boost is a counterexample
