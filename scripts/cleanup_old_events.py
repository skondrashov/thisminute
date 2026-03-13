"""Clean up old events that have no extracted stories.

These are pure Jaccard-clustered events with garbage groupings.
Their stories will remain unassigned until extracted, then get proper clustering.
"""
import sqlite3
import sys

sys.path.insert(0, '/opt/thisminute')

conn = sqlite3.connect('/opt/thisminute/data/thisminute.db')
conn.row_factory = sqlite3.Row

# Find events where NO stories have extractions
old_events = conn.execute("""
    SELECT e.id, e.title, e.story_count
    FROM events e
    WHERE e.merged_into IS NULL
    AND NOT EXISTS (
        SELECT 1 FROM event_stories es
        JOIN story_extractions se ON es.story_id = se.story_id
        WHERE es.event_id = e.id
    )
""").fetchall()

print(f"Found {len(old_events)} events with no extracted stories", flush=True)
for e in old_events[:10]:
    print(f"  [{e['id']}] {e['title'][:60]} stories={e['story_count']}", flush=True)
if len(old_events) > 10:
    print(f"  ... and {len(old_events)-10} more", flush=True)

# Delete event_stories links
for e in old_events:
    conn.execute("DELETE FROM event_stories WHERE event_id = ?", (e['id'],))

# Delete narrative_events links
ids = [e['id'] for e in old_events]
if ids:
    placeholders = ','.join('?' * len(ids))
    ne_del = conn.execute(
        f"DELETE FROM narrative_events WHERE event_id IN ({placeholders})", ids
    ).rowcount
    ev_del = conn.execute(
        f"DELETE FROM events WHERE id IN ({placeholders})", ids
    ).rowcount
    print(f"Deleted {ev_del} events and {ne_del} narrative_events links", flush=True)

conn.commit()

# Also clean up merged events
merged_del = conn.execute("DELETE FROM events WHERE merged_into IS NOT NULL").rowcount
print(f"Deleted {merged_del} merged events", flush=True)
conn.commit()

# Stats
remaining = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
remaining_sev = conn.execute("SELECT COUNT(*) FROM events WHERE severity IS NOT NULL").fetchone()[0]
unassigned = conn.execute("""
    SELECT COUNT(*) FROM stories
    WHERE id NOT IN (SELECT story_id FROM event_stories)
""").fetchone()[0]
print(f"\nRemaining: {remaining} events ({remaining_sev} with severity), {unassigned} unassigned stories", flush=True)
conn.close()
