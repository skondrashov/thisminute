"""Reset events: clear old garbage events and let semantic clusterer rebuild.

Only unassigns stories that have LLM extractions (so they get proper clustering).
Stories without extractions stay in their current events.
"""
import sqlite3
import sys

sys.path.insert(0, '/opt/thisminute')

conn = sqlite3.connect('/opt/thisminute/data/thisminute.db')
conn.row_factory = sqlite3.Row

# Stats before
before = {
    'events': conn.execute("SELECT COUNT(*) FROM events").fetchone()[0],
    'event_stories': conn.execute("SELECT COUNT(*) FROM event_stories").fetchone()[0],
    'narrative_events': conn.execute("SELECT COUNT(*) FROM narrative_events").fetchone()[0],
    'extracted': conn.execute("SELECT COUNT(*) FROM story_extractions").fetchone()[0],
}
print(f"Before: {before}", flush=True)

# Step 1: Remove event_stories links for all extracted stories
# These will be re-clustered properly by the semantic clusterer
extracted_count = conn.execute("""
    DELETE FROM event_stories
    WHERE story_id IN (SELECT story_id FROM story_extractions)
""").rowcount
print(f"Unassigned {extracted_count} extracted stories from events", flush=True)

# Step 2: Delete events that now have 0 stories
# (Count stories remaining in each event)
empty_events = conn.execute("""
    SELECT e.id FROM events e
    WHERE NOT EXISTS (SELECT 1 FROM event_stories es WHERE es.event_id = e.id)
""").fetchall()
empty_ids = [r['id'] for r in empty_events]
print(f"Found {len(empty_ids)} empty events to delete", flush=True)

if empty_ids:
    placeholders = ','.join('?' * len(empty_ids))
    # Remove narrative links to empty events
    ne_deleted = conn.execute(
        f"DELETE FROM narrative_events WHERE event_id IN ({placeholders})",
        empty_ids
    ).rowcount
    print(f"Deleted {ne_deleted} narrative_events links", flush=True)

    # Delete the empty events
    ev_deleted = conn.execute(
        f"DELETE FROM events WHERE id IN ({placeholders})",
        empty_ids
    ).rowcount
    print(f"Deleted {ev_deleted} empty events", flush=True)

conn.commit()

# Stats after
after = {
    'events': conn.execute("SELECT COUNT(*) FROM events").fetchone()[0],
    'event_stories': conn.execute("SELECT COUNT(*) FROM event_stories").fetchone()[0],
    'narrative_events': conn.execute("SELECT COUNT(*) FROM narrative_events").fetchone()[0],
    'unassigned': conn.execute("""
        SELECT COUNT(*) FROM stories
        WHERE id NOT IN (SELECT story_id FROM event_stories)
    """).fetchone()[0],
}
print(f"After: {after}", flush=True)
print(f"Unassigned stories will be re-clustered on next pipeline run", flush=True)
conn.close()
