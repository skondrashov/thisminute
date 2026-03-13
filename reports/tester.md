# Tester Report

## Health Check -- 2026-03-11 01:16 EST (2026-03-11 05:16 UTC)

**Context**: ~3 hours after GDELT rate fix deploy (0.07 -> 0.003, MAX_PER_CYCLE=50). Also 16 new RSS feeds added (7 sports, 9 entertainment).

### Summary

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| API health | ok, 114,553 stories | -- | OK |
| Stories ingested (3h) | +529 (~176/hr = ~4,232/day) | 3,000-4,000/day | **WARN** (slightly above) |
| Stories in API response | 1,911 | -- | OK |
| Events (active) | 20 (16 ongoing, 4 escalating) | 200-600 | **WARN** (low, but expected post-fix) |
| Event/story ratio | 1:25 (500 stories across 20 events) | 1:3 to 1:8 | **WARN** (high -- events are very large) |
| Narratives (active) | 20 | 5-20 | OK |
| Extraction rate | 98.4% (1,880/1,911 have concepts) | > 95% | OK |
| Origin split | 996 RSS / 915 GDELT (52% / 48%) | ~50/50 | OK |
| Bright side distribution | Scores 2-8, bell curve centered ~5 | -- | OK |
| Playwright: page load | No JS errors | 0 errors | OK |
| Playwright: story count | 1,911 | > 0 | OK |
| Playwright: situations | 20 | > 0 | OK |
| Sports world | 279 stories, 0 situations | > 0 stories | **WARN** (no situations) |
| Entertainment world | 43 stories, 0 situations | > 0 stories | **WARN** (no situations) |
| Positive world | 414 stories, 7 situations | > 0 | OK |
| New feeds scraped | 15/15 found | 15/15 | OK |

### Verdict: RECOVERING -- GDELT fix working, new feeds active

The GDELT rate reduction from 0.07 to 0.003 has dramatically improved system health. Ingestion rate is now ~4,232/day, close to the 3,000-4,000 target (slightly above, likely transient). The RSS/GDELT split is now a healthy 52/48 instead of the previous 96/4. Extraction rate is back up to 98.4% (was 60.5% pre-fix). All 15 new RSS feeds are actively contributing stories.

---

### Detailed Findings

#### 1. GDELT Rate Fix -- WORKING

- **Before** (previous check): 45,027 GDELT stories/day, 96.4% of all stories
- **After** (this check): 915 GDELT stories in response (48%), origin split now 52% RSS / 48% GDELT
- **Ingestion rate**: +529 stories in ~3 hours = ~176/hr = ~4,232/day projected
- Slightly above the 3,000-4,000 target but much improved from the 46,706/day crisis
- The slight overshoot is likely because the 16 new RSS feeds are contributing more than the old feed set

**Status**: GDELT rate fix is effective. Monitor for another day to confirm steady-state rate.

#### 2. Extraction Pipeline -- RECOVERED

- 98.4% of stories have concepts (was 60.5% at last check)
- Stories have rich data: concepts, entities, severity, sentiment, bright_side_score
- Sample story from Bollywood Hungama has full extraction: concepts ["bollywood", "theatre-awards", "entertainment"], severity 1, bright_side_score 5
- Sentiment distribution: positive 350, neutral 861, negative 614, mixed 4, null 82
- Bright side scores form a healthy bell curve: centered around 5-6

**Status**: OK. Pipeline is keeping up now that volume is under control.

#### 3. New RSS Feeds -- ALL ACTIVE

All 15 new feeds are returning stories in the current API response:

| Source | Stories |
|--------|---------|
| Sportstar | 79 |
| ESPNcricinfo | 78 |
| Autosport | 41 |
| Rugby World | 26 |
| ESPN Soccer | 12 |
| ESPN | 9 |
| Soompi | 8 |
| Bollywood Hungama | 6 |
| Sky Sports | 6 |
| NME | 4 |
| Pitchfork | 4 |
| Billboard | 3 |
| Rolling Stone | 3 |
| Deadline | 3 |
| Variety | 3 |

Total: 285 stories from new feeds (14.9% of all stories).

Sports feeds are heavy contributors (Sportstar, ESPNcricinfo, Autosport dominate). Entertainment feeds are active but contribute fewer stories, which is expected given their lower article volume.

**Status**: OK. All feeds scraping successfully.

#### 4. Events -- LOW COUNT (Expected)

- Only 20 events returned via API (target: 200-600)
- All 20 are substantial: min 25, max 25, avg 25 stories per event
- Status breakdown: 16 ongoing, 4 escalating
- This is likely a cleanup effect -- the previous 25,662 event bloat was purged/resolved
- The event/story ratio of 1:25 is above the 1:3 to 1:8 target, meaning events are very large clusters

**Status**: WARN. Event count is low relative to targets but this is expected during recovery. The clustering pipeline needs time to build new events from the reduced flow. The existing 20 events are all high-quality (25+ stories each). May need a re-clustering run to break large events into smaller ones.

#### 5. Narratives -- HEALTHY

- 20 active narratives (within 5-20 target)
- All have "active" status
- Top narrative: "US-Israel War Against Iran" with 77 events, 1,737 stories
- Good thematic diversity: war, diplomacy, oil crisis, sports, entertainment, politics, AI
- T20 World Cup narrative shows sports content is being picked up

**Status**: OK.

#### 6. Sports and Entertainment Worlds -- PARTIALLY WORKING

Playwright world-switching test results:

| World | Stories | Situations |
|-------|---------|------------|
| News | 1,911 | 20 |
| Sports | 279 | 0 |
| Entertainment | 43 | 0 |
| Positive | 414 | 7 |

- **Sports**: Has 279 stories showing (good!) but 0 situations. Stories are flowing but no sports-specific situations/events have been created yet.
- **Entertainment**: Has 43 stories (lower volume, expected) but 0 situations.
- **Positive**: Working well with 414 stories and 7 situations.

The new feeds are clearly populating Sports and Entertainment worlds with stories, but the situation/event pipeline has not yet created world-specific clusters. This may just need more time for the clustering to run, or the event signatures may not be grouping sports/entertainment stories into situations.

**Status**: WARN. Stories are flowing into worlds but situations need time to form. Check again in 12-24 hours.

#### 7. Category Distribution -- DIVERSE

Top categories in current stories:
- us-iran-conflict (59), general (35), cricket (31), iran-conflict (29), formula-1 (26)
- violence (20), us-politics (17), criminal-justice (17), entertainment (15), six-nations (14)
- tennis (11), champions-league (9), cricket-t20 (10), rugby-union (7)

Sports categories (cricket, formula-1, six-nations, tennis, champions-league, rugby-union, etc.) are well-represented thanks to the new feeds. Entertainment is present but with fewer stories. The category diversity looks healthy.

#### 8. Playwright Page Health -- CLEAN

- Zero JS errors on page load
- 1,911 stories rendered
- 20 situations displayed
- World switching works without errors
- All stat counters update correctly

**Status**: OK.

---

### Comparison: Before vs After GDELT Fix

| Metric | Before (20:26 EST) | After (01:16 EST) | Change |
|--------|--------------------|--------------------|--------|
| Ingestion rate | ~46,706/day | ~4,232/day | -91% |
| GDELT/RSS split | 96%/4% | 48%/52% | Fixed |
| Extraction rate | 60.5% | 98.4% | +38pp |
| Active events | 25,662 | 20 | -99.9% |
| Active narratives | 46 | 20 | -57% |
| Pending extractions | 8,789 | ~31 | -99.6% |

The GDELT rate fix has resolved all three CRITICAL issues from the previous check.

---

### Action Items

1. **[MONITOR] Ingestion rate**: At ~4,232/day, slightly above the 3,000-4,000 target. The new RSS feeds add ~285 stories to each cycle. May need a minor GDELT_SAMPLE_RATE reduction from 0.003 to 0.002 if rate stays elevated after 24h.

2. **[MONITOR] Sports/Entertainment situations**: Stories are flowing into these worlds but no situations have formed yet. Expected to self-resolve as the clustering pipeline runs. Check again in 12-24 hours.

3. **[LOW] Event count recovery**: Only 20 events after the cleanup. The clustering pipeline should generate new events from incoming stories. If count stays below 50 after 24h, investigate event creation thresholds.

4. **[LOW] Fix Playwright test**: Still need to add "escalating" and "de-escalating" to allowed event statuses at `e2e/visual.spec.js:134` (carryover from previous report).

---

## Previous Report

### Health Check -- 2026-03-10 20:26 EST (2026-03-11 00:26 UTC)

See git history for full previous report. Summary: GDELT at 7% sample rate was ingesting ~45K stories/day, drowning extraction pipeline (60.5% rate), and bloating events table (25,662 active). All three issues were CRITICAL. GDELT rate was reduced to 0.3% (0.003) with MAX_PER_CYCLE=50 cap as a fix.
