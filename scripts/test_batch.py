"""Test a batch extraction to debug why batches fail."""
import json
import sys
import os
import logging

logging.basicConfig(level=logging.DEBUG)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.llm_extractor import _extract_batch_llm, _build_story_text, SYSTEM_PROMPT
from src.llm_utils import get_anthropic_client, HAIKU_MODEL
from src.database import get_connection

client = get_anthropic_client()
if not client:
    print("NO API CLIENT")
    sys.exit(1)

conn = get_connection()

# Get 8 stories needing re-extraction (same as backfill)
rows = conn.execute("""
    SELECT s.id, s.title, s.summary, s.url, s.source, s.published_at, s.scraped_at,
           s.lat, s.lon, s.location_name, s.concepts
    FROM stories s
    JOIN story_extractions se ON se.story_id = s.id
    WHERE se.bright_side_score IS NULL
    ORDER BY s.published_at DESC
    LIMIT 8
""").fetchall()

stories = []
for r in rows:
    stories.append({
        "id": r[0], "title": r[1], "summary": r[2], "url": r[3],
        "source": r[4], "published_at": r[5], "scraped_at": r[6],
        "lat": r[7], "lon": r[8], "location_name": r[9], "concepts": r[10],
    })

print(f"Got {len(stories)} stories", flush=True)
for s in stories:
    print(f"  [{s['id']}] {s['title'][:80]}", flush=True)

# Load registry events (same as backfill)
registry_events = conn.execute("""
    SELECT id, registry_label, map_label, primary_lat, primary_lon, status
    FROM event_registry WHERE status != 'retired'
""").fetchall()
registry = [{"id": r[0], "registry_label": r[1], "map_label": r[2], "lat": r[3], "lon": r[4], "status": r[5]}
            for r in registry_events]
print(f"Registry events: {len(registry)}", flush=True)

# Load wiki events
wiki_events = conn.execute("""
    SELECT we.id, we.article_title, COUNT(swe.story_id) as story_count
    FROM wiki_events we
    LEFT JOIN story_wiki_events swe ON swe.wiki_event_id = we.id
    WHERE we.status = 'active'
    GROUP BY we.id
""").fetchall()
wikis = [{"id": r[0], "article_title": r[1], "story_count": r[2]} for r in wiki_events]
print(f"Wiki events: {len(wikis)}", flush=True)

# Try the extraction
print("\n--- Calling _extract_batch_llm ---", flush=True)
try:
    result = _extract_batch_llm(client, stories, registry, wikis)
    if result:
        print(f"SUCCESS: {len(result)} extractions", flush=True)
        for i, ext in enumerate(result):
            print(f"  [{i}] keys={list(ext.keys())}, bright_side={ext.get('bright_side') is not None}", flush=True)
    else:
        print("RETURNED None", flush=True)
except Exception as e:
    print(f"EXCEPTION: {e}", flush=True)
    import traceback
    traceback.print_exc()
