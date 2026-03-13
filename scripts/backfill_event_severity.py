"""One-off: backfill severity into events from story_extractions."""
import sqlite3
import json
import sys

sys.path.insert(0, '/opt/thisminute')

conn = sqlite3.connect('/opt/thisminute/data/thisminute.db')
conn.row_factory = sqlite3.Row

# Find events without severity that have extracted stories
rows = conn.execute("""
    SELECT e.id, e.title, e.story_count,
           GROUP_CONCAT(se.severity) as severities,
           GROUP_CONCAT(se.primary_action) as actions
    FROM events e
    JOIN event_stories es ON e.id = es.event_id
    JOIN story_extractions se ON es.story_id = se.story_id
    WHERE e.severity IS NULL AND se.severity IS NOT NULL
    GROUP BY e.id
""").fetchall()

print(f"Found {len(rows)} events to update", flush=True)
updated = 0
for r in rows:
    sevs = [int(s) for s in r['severities'].split(',') if s.isdigit()]
    actions = [a for a in (r['actions'] or '').split(',') if a and a != 'None']
    if sevs:
        max_sev = max(sevs)
        action = actions[0] if actions else None
        conn.execute(
            "UPDATE events SET severity = ?, primary_action = ? WHERE id = ?",
            (max_sev, action, r['id'])
        )
        updated += 1
        if updated <= 10:
            print(f"  [{r['id']}] {r['title'][:50]} -> sev={max_sev} action={action}", flush=True)

conn.commit()

# Also fix narrative story_count
narr_rows = conn.execute("""
    SELECT n.id, n.title,
           (SELECT COUNT(DISTINCT es2.story_id)
            FROM narrative_events ne2
            JOIN event_stories es2 ON ne2.event_id = es2.event_id
            WHERE ne2.narrative_id = n.id) as real_story_count,
           (SELECT COUNT(*) FROM narrative_events WHERE narrative_id = n.id) as real_event_count
    FROM narratives n
""").fetchall()
for nr in narr_rows:
    conn.execute(
        "UPDATE narratives SET story_count = ?, event_count = ? WHERE id = ?",
        (nr['real_story_count'], nr['real_event_count'], nr['id'])
    )
    print(f"  Narrative [{nr['id']}] {nr['title'][:40]} -> stories={nr['real_story_count']} events={nr['real_event_count']}", flush=True)

conn.commit()

# Report
sev_count = conn.execute("SELECT COUNT(*) FROM events WHERE severity IS NOT NULL").fetchone()[0]
total_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
print(f"\nDone: updated {updated} events. {sev_count}/{total_events} events now have severity.", flush=True)
conn.close()
