# thisminute.org — Roles, Monitoring & Growth

## Agent Roles

### Deployer
**File**: `agents/deployer.md` (exists)
**Trigger**: After code changes, on request
**Does**: Tars local code, SCPs to GCP VM, fixes CRLF, restarts systemd service, runs health checks.
**Owns**: `deploy/setup.sh`, nginx config, systemd service, SSL certs.

### Monitor
**Trigger**: Periodic (daily or on-demand)
**Does**:
- SSH into VM, check `journalctl -u thisminute` for errors
- Query DB for extraction health: `SELECT COUNT(*) FROM story_extractions WHERE extracted_at > datetime('now', '-24 hours')`
- Check extraction failure rate: stories with `extraction_status = 'failed'` vs 'done'
- Check event clustering quality: ratio of events to stories (target: 1 event per 3-8 stories)
- Check narrative freshness: `SELECT last_analyzed FROM narratives ORDER BY last_analyzed DESC LIMIT 1`
- Monitor API costs via Anthropic dashboard or log token counts
- Report: extraction count, failure rate, avg severity distribution, top topics, event/story ratio, narrative count

**Key queries**:
```sql
-- Extraction health (last 24h)
SELECT extraction_status, COUNT(*) FROM stories
WHERE scraped_at > datetime('now', '-24 hours') GROUP BY extraction_status;

-- Topic distribution (are topics diverse or stuck on one thing?)
SELECT topics, COUNT(*) as cnt FROM story_extractions
WHERE extracted_at > datetime('now', '-24 hours')
GROUP BY topics ORDER BY cnt DESC LIMIT 20;

-- Location type distribution (should be ~85% terrestrial, 1-5% space, 5-10% internet, 5-10% abstract)
SELECT location_type, COUNT(*) as cnt FROM story_extractions
WHERE extracted_at > datetime('now', '-24 hours')
GROUP BY location_type;

-- Severity distribution (should be roughly normal around 2-3)
SELECT severity, COUNT(*) as cnt FROM story_extractions
WHERE extracted_at > datetime('now', '-24 hours')
GROUP BY severity ORDER BY severity;

-- Event clustering health
SELECT COUNT(*) as event_count,
       AVG(story_count) as avg_stories,
       MIN(story_count) as min_stories,
       MAX(story_count) as max_stories
FROM events WHERE merged_into IS NULL AND status != 'resolved';

-- Actor role distribution
SELECT role, COUNT(*) as cnt FROM story_actors
WHERE story_id IN (SELECT id FROM stories WHERE scraped_at > datetime('now', '-24 hours'))
GROUP BY role ORDER BY cnt DESC;

-- Narrative health
SELECT COUNT(*) as active_narratives,
       AVG(event_count) as avg_events_per_narrative
FROM narratives WHERE status = 'active';
```

### Designer
**Trigger**: When UI feedback arrives or new features are needed
**Does**:
- Modifies `static/js/app.js`, `static/css/style.css`, `static/index.html`
- Tests locally at localhost:8000
- Bumps `?v=N` cache-buster on every change
- Ensures light/dark mode parity for ALL new elements (this is frequently missed)

**Principles**:
- No build tools, no frameworks — vanilla JS/CSS
- Mobile-responsive (sidebar collapses)
- MapLibre GL JS 5.x
- localStorage for user preferences (theme)
- Left sidebar = filters + navigation (Situations | Events). Right panel = story reader.
- Orthogonal filter model: topic, source, time, sentiment, situation, location, domain are independent AND filters
- Space/Internet use the same right info-panel with themed backgrounds (not separate panels)

### Extractor (LLM Quality)
**Trigger**: When extraction quality issues are identified
**Does**:
- Reviews and improves the SYSTEM_PROMPT in `src/llm_extractor.py`
- Adds examples, edge cases, decision tables to the prompt
- Tests prompt changes against sample stories
- Monitors for common misclassifications (especially location_type)

**Current prompt features** (~2,654 tokens):
- 10 numbered field specifications with GOOD/BAD examples
- location_type decision table (terrestrial/space/internet/abstract)
- Severity scale 1-5 with descriptions
- Actor role definitions (perpetrator/victim/authority/witness/participant/target)
- event_signature rules (3-6 word real-world event identifier)
- search_keywords generation rules

### Backend Dev
**Trigger**: New API endpoints, schema changes, pipeline improvements
**Does**:
- Modifies `src/database.py` (schema, migrations, queries)
- Modifies `src/app.py` (FastAPI endpoints)
- Modifies pipeline components (`pipeline.py`, `semantic_clusterer.py`, etc.)
- Writes migrations carefully (existing data must survive)

**Rules**:
- Always add columns with DEFAULT values
- Run dedup BEFORE adding unique indexes
- Test migrations against existing DB before deploying

---

## What to Monitor

### Daily Health Check
| Metric | Target | Alert If |
|--------|--------|----------|
| Stories scraped (24h) | 150-250 | < 50 or > 500 |
| Extraction success rate | > 95% | < 80% |
| Events created (24h) | 30-80 | < 10 or > 150 |
| Event/story ratio | 1:3 to 1:8 | < 1:2 or > 1:15 |
| Narratives active | 5-20 | 0 (Sonnet not running) |
| API errors in logs | 0 | > 5 per cycle |
| Pipeline cycle time | < 60s | > 180s |
| Anthropic API cost | ~$3-5/day | > $10/day |

### Extraction Quality Signals
- **Topic diversity**: If >50% of stories get the same topic, the prompt is too coarse
- **Severity distribution**: Should be roughly normal (most stories = 2-3, few = 1 or 5). If everything is 3, the model is hedging
- **location_type accuracy**: Spot-check 20 stories/week — are space/internet/abstract stories correctly classified?
- **event_signature clustering**: Do similar stories get the same signature? Do unrelated stories get different ones?
- **search_keywords utility**: Try searching for actors/concepts that should match — do they?
- **Actor extraction**: Are actor roles correct? (victim vs perpetrator matters a lot)

### Frontend Quality Signals
- Does clicking a situation/event open the right panel with correct stories?
- Do Space/Internet buttons glow when they have stories?
- Does the right panel show themed backgrounds for Space/Internet?
- Does light mode look correct for ALL elements (especially active/expanded states)?
- Does the location filter dim other areas and brighten the selected one?
- Are registry event labels readable on the map?
- Does cross-view highlighting work (sidebar -> map -> right panel)?

---

## Growth Priorities

### Near-Term (Next 2 Weeks)
1. **Feed expansion**: Add Reuters, AP, DW, NHK, SCMP for better global coverage
2. **Extraction prompt tuning**: Collect 50 misclassified stories, add as examples to system prompt
3. **Search UX**: Natural language query parsing ("victim is black" -> structured API query)
4. **Mobile layout**: Sidebar behavior on narrow screens, touch-friendly map interactions
5. **Event deduplication**: Merge events that the LLM signature missed (periodic Sonnet pass?)

### Medium-Term (1-2 Months)
1. **User accounts**: Save searches, bookmark stories, set alerts for topics/actors
2. **Push notifications**: Breaking news (severity >= 4) via web push or email
3. **Historical view**: Timeline slider to see how events evolved over days/weeks
4. **Source diversity scoring**: Flag when a narrative only has coverage from one perspective
5. **API for third parties**: Public REST API with rate limiting for researchers

### Long-Term (3+ Months)
1. **Multilingual**: Scrape non-English feeds, translate via LLM
2. **Bias detection**: Compare framing across sources for the same event
3. **Prediction**: "This narrative is likely to escalate because..." based on historical patterns
4. **Community contributions**: Let users submit feeds, suggest corrections
5. **Self-improving extraction**: Use user search patterns to identify extraction gaps

---

## Feedback Loop

When something looks wrong on the site:

1. **Identify the layer**: Is it scraping (no stories), extraction (wrong categories), clustering (wrong groupings), analysis (bad descriptions), or frontend (display bug)?
2. **Check logs**: `sudo journalctl -u thisminute -n 100 --no-pager` on the VM
3. **Check DB**: Run the monitoring queries above
4. **Fix at the right level**:
   - Bad categories -> improve SYSTEM_PROMPT in `llm_extractor.py`
   - Bad clustering -> adjust `FUZZY_MATCH_THRESHOLD` in `semantic_clusterer.py`
   - Bad event descriptions -> improve prompt in `event_analyzer.py`
   - Bad narratives -> improve prompt in `narrative_analyzer.py`
   - Display issues -> fix in `app.js` / `style.css`
5. **Deploy and verify**: Bump version, deploy, wait 2 pipeline cycles (~30 min), check results

## Cost Management

| Component | Model | Est. Cost/Day |
|-----------|-------|---------------|
| Story extraction (8/batch) | Haiku | ~$0.75 |
| Event analysis (10/cycle) | Haiku | ~$0.50 |
| World overview (1/hour) | Haiku | ~$0.12 |
| Narrative synthesis (1/2h) | Sonnet | ~$2.00 |
| **Total** | | **~$3.37** |

To reduce costs:
- Increase batch size in `llm_extractor.py` (8 -> 12)
- Increase `WORLD_OVERVIEW_STALENESS_HOURS` (1 -> 2)
- Increase `NARRATIVE_INTERVAL_SECONDS` (7200 -> 14400)
- Skip re-analysis of events whose `analysis_hash` hasn't changed (already implemented)
