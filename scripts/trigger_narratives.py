#!/usr/bin/env python3
"""Trigger narrative analysis for all domains immediately with debugging."""
import os
import sys
sys.path.insert(0, "/opt/thisminute")

# Check API key
key = os.environ.get("ANTHROPIC_API_KEY", "")
print(f"API key set: {bool(key)} (len={len(key)})")

from src.database import get_connection
from src.narrative_analyzer import _get_domain_events, analyze_narratives
from src.llm_utils import get_anthropic_client

client = get_anthropic_client()
print(f"Anthropic client: {client is not None}")

conn = get_connection()

# Reset last_analyzed timestamps
conn.execute("UPDATE narratives SET last_analyzed = '2020-01-01T00:00:00+00:00' WHERE status = 'active'")
conn.commit()

for domain in ["sports", "entertainment", "positive"]:
    print(f"\n=== {domain} ===")
    evts = _get_domain_events(conn, domain, limit=50)
    print(f"  Events found: {len(evts)}")
    if evts:
        print(f"  Top 3: {[(e['id'], e['title'][:60]) for e in evts[:3]]}")

    try:
        stats = analyze_narratives(conn, domain=domain)
        print(f"  Result: {stats}")
    except Exception as e:
        import traceback
        traceback.print_exc()

# Check what narratives exist now
rows = conn.execute("SELECT domain, COUNT(*) as c FROM narratives WHERE status='active' GROUP BY domain").fetchall()
print(f"\nNarrative counts: {[(r['domain'], r['c']) for r in rows]}")

conn.close()
