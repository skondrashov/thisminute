"""Check narrative → event → story chain on production."""
import subprocess
import base64

GCLOUD = "C:/Users/tkond/AppData/Local/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"

script = r"""#!/bin/bash
sudo -u thisminute /opt/thisminute/venv/bin/python3 -c "
import sqlite3
conn = sqlite3.connect('/opt/thisminute/data/thisminute.db')
conn.row_factory = sqlite3.Row

# Check narrative_events links
r = conn.execute('SELECT COUNT(*) FROM narrative_events').fetchone()
print(f'narrative_events rows: {r[0]}')

# Check event_stories links
r = conn.execute('SELECT COUNT(*) FROM event_stories').fetchone()
print(f'event_stories rows: {r[0]}')

# Get first narrative
n = conn.execute('SELECT id, title FROM narratives WHERE status=\"active\" LIMIT 1').fetchone()
if n:
    print(f'First narrative: {n[\"id\"]} - {n[\"title\"]}')
    events = conn.execute('SELECT event_id FROM narrative_events WHERE narrative_id = ?', (n['id'],)).fetchall()
    print(f'  Events linked: {len(events)}')
    if events:
        eid = events[0]['event_id']
        stories = conn.execute('SELECT COUNT(*) FROM event_stories WHERE event_id = ?', (eid,)).fetchone()
        print(f'  First event {eid} has {stories[0]} stories in event_stories')

# Check the full chain
r = conn.execute('''
    SELECT COUNT(DISTINCT es.story_id)
    FROM narrative_events ne
    JOIN event_stories es ON es.event_id = ne.event_id
    WHERE ne.narrative_id = (SELECT id FROM narratives WHERE status=\"active\" LIMIT 1)
''').fetchone()
print(f'Stories via chain: {r[0]}')
"
"""

b64 = base64.b64encode(script.encode()).decode()
r = subprocess.run(
    [GCLOUD, "compute", "ssh", "thisminute", "--zone=us-central1-a",
     "--command", f"echo {b64} | base64 -d | bash"],
    capture_output=True, timeout=60, encoding="utf-8", errors="replace",
)
print(r.stdout)
if r.stderr:
    print("ERR:", r.stderr[:500])
