# thisminute.org — Review Log

## Review #1 — 2026-03-04 07:45 UTC

### DB Health

| Metric            | Value                 | Assessment                                                     |
| ----------------- | --------------------- | -------------------------------------------------------------- |
| Stories           | 1,277                 | Good — growing                                                 |
| Extractions       | 9/1,277 (0.7%)        | CRITICAL — LLM not running                                     |
| Actors            | 0                     | Expected (no LLM)                                              |
| Events            | 523                   | WAY too many — legacy Jaccard creates 1 event per ~2.4 stories |
| Narratives        | 0                     | Expected (no Sonnet)                                           |
| Extraction status | 1,268 pending, 9 done | 9 legacy fallback extractions only                             |

### Root Cause: No ANTHROPIC_API_KEY on VM

The systemd service had no `ANTHROPIC_API_KEY` environment variable. All 1,268 stories are stuck at `extraction_status = 'pending'`. The legacy fallback only runs for new stories (not pending backfill).

**Fix applied**: Added `EnvironmentFile=-/opt/thisminute/.env` to systemd service. User needs to:

```bash
gcloud compute ssh thisminute --zone=us-central1-a
echo "ANTHROPIC_API_KEY=sk-ant-..." | sudo tee /opt/thisminute/.env
sudo chmod 600 /opt/thisminute/.env
sudo chown thisminute:thisminute /opt/thisminute/.env
sudo systemctl restart thisminute
```

### Issues Found

1. **523 events from 1,277 stories** — ratio of 1:2.4 is terrible. Target is 1:3-8. Without LLM event_signatures, the legacy Jaccard clustering creates far too many small events. Will improve dramatically once API key is set and semantic clustering kicks in.

2. **No backfill for pending extractions** — `enrich_stories()` only processes stories passed as `story_ids` (new ones from pipeline). The 1,268 already-stored pending stories will never get extracted unless we add a backfill mechanism.

3. **Event analysis never runs** — `analyzed: 0` in every pipeline run. Without API key, `_get_anthropic_client()` returns None, and the template fallback creates events but never enriches them with good titles/descriptions.

4. **World overview never generated** — shows "False" in every log. Same API key issue.

### Suggestions to Implement

- [ ] **Backfill pending extractions**: Add a startup task or periodic check that processes stories with `extraction_status = 'pending'` (not just new ones)
- [ ] **Merge bloated events**: Once LLM clustering works, run a one-time cleanup to re-cluster the 523 events
- [ ] **Add event count to stats bar**: Show how many events are active so users see clustering is working
- [ ] **Preview pane**: Currently empty until a story is clicked — could show a "tip" or the most recent/severe story by default

### UX Observations (from site visit)

- The multiview layout is visually appealing with the space/internet backgrounds
- Preview pane works well as a concept — good that it's one click to preview, one more to read
- The opinion filter checkbox blends in nicely with the toolbar
- Concept chips work but are currently keyword-based; will improve with LLM topics
- World overview bar is empty (no LLM) — could show template fallback text
- 523 events in the Events tab is overwhelming — needs LLM clustering badly

---

## Review #2 — 2026-03-04 15:20 UTC

### Status

| Metric      | Value                       | Change               | Assessment                          |
| ----------- | --------------------------- | -------------------- | ----------------------------------- |
| Stories     | 1,480                       | +203                 | Healthy growth                      |
| Extractions | 433/1,480 (29%)             | +424                 | LLM working, backfill in progress   |
| Actors      | 697                         | +697                 | Populated from LLM                  |
| Events      | 530 (413 single, 117 multi) | 604->530 after merge | Improved but still too many singles |
| Narratives  | 0                           | 0                    | FIXED: model ID was wrong           |

### Issues Found & Fixed

1. **Narrative model ID 404**: `claude-sonnet-4-6-20250610` doesn't exist. Changed to `claude-sonnet-4-6`. Narratives should start populating within 10 minutes.

2. **Event clustering too aggressive on uniqueness**: LLM event signatures were too specific (e.g., "Wolves beats Liverpool 2-1 late goal 2026" vs "Wolves defeat Liverpool Premier League"). Three fixes:
    - **Improved prompt**: Signatures now canonical entity+event-type only, no scores/dates/verbs
    - **Better similarity**: Dice coefficient instead of Jaccard, stopword filtering, number removal
    - **Lower threshold**: 0.35 instead of 0.5

3. **Severity type comparison crash**: `'>' not supported between instances of 'int' and 'str'` in `semantic_clusterer.py`. Fixed with explicit int() casts.

4. **Legacy extraction poisoning signatures**: When API returns 529 (overloaded), fallback stored `title[:60]` as event_signature, creating garbage signatures. Fixed to store empty string, routing to Jaccard fallback instead.

5. **API 529 overloaded**: Claude Haiku returning 529 intermittently. Not fixable in code — the anthropic SDK already retries 3x. Legacy fallback handles it gracefully now.

### Re-merge Results

Ran one-time re-merge of existing events:

- Pass 1: 68 merged, Pass 2: 6 merged
- 604 events -> 530 events (74 merged)
- Top event: "Iran-Israel-US Military Escalation" with 53 stories
- Clustering will continue to improve as more stories get LLM signatures

### Pending

- Backfill: ~1,044 stories still pending extraction (16/cycle = ~17 more hours)
- Narratives: Should appear after next analysis cycle (~5 min from deploy)
- Event clustering: Will improve as new stories get canonical signatures
