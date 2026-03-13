#!/usr/bin/env python3
"""Quick test: verify domain event queries work."""
import sys
sys.path.insert(0, "/opt/thisminute")

from src.database import get_connection
from src.narrative_analyzer import _get_domain_events

conn = get_connection()
for d in ["news", "sports", "entertainment", "positive"]:
    evts = _get_domain_events(conn, d, limit=50)
    print(f"{d}: {len(evts)} events")
    for e in evts[:3]:
        print(f"  #{e['id']}: {e['title']} ({e['story_count']} stories)")
conn.close()
