"""Debug narrative analysis."""
import sqlite3
import json
import sys
import os
import logging

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
sys.path.insert(0, '/opt/thisminute')

from src.database import get_active_events, get_active_narratives
from src.narrative_analyzer import _build_events_summary, _build_narratives_summary, NARRATIVE_MODEL

conn = sqlite3.connect('/opt/thisminute/data/thisminute.db')
conn.row_factory = sqlite3.Row

events = get_active_events(conn, limit=50)
narratives = get_active_narratives(conn, limit=20)
print(f"Events: {len(events)}", flush=True)
print(f"Narratives: {len(narratives)}", flush=True)

events_summary = _build_events_summary(conn, events)
narratives_summary = _build_narratives_summary(narratives)

print(f"Events summary ({len(events_summary)} chars):", flush=True)
print(events_summary[:500], flush=True)
print("...", flush=True)

# Try the API call
api_key = os.environ.get("ANTHROPIC_API_KEY", "")
if not api_key:
    print("NO API KEY!", flush=True)
    sys.exit(1)

import anthropic
client = anthropic.Anthropic(api_key=api_key)

prompt = f"""You are analyzing current news events to identify overarching narratives and themes.

CURRENT EVENTS:
{events_summary}

EXISTING NARRATIVES:
{narratives_summary}

Your task:
1. Identify which events belong to existing narratives (by narrative ID)
2. Identify NEW narratives that emerge from patterns across multiple events

Return a JSON object with:
- "updates": array of updates to existing narratives
- "new_narratives": array of new narratives

Return ONLY valid JSON."""

print(f"\nCalling {NARRATIVE_MODEL}...", flush=True)
try:
    response = client.messages.create(
        model=NARRATIVE_MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    print(f"Response ({len(text)} chars):", flush=True)
    print(text[:1000], flush=True)

    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    result = json.loads(text)
    print(f"\nParsed: updates={len(result.get('updates',[]))}, new={len(result.get('new_narratives',[]))}", flush=True)
except Exception as e:
    print(f"ERROR: {e}", flush=True)

conn.close()
