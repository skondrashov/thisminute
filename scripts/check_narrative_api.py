"""Check narrative API query directly on production."""
import subprocess
import base64

GCLOUD = "C:/Users/tkond/AppData/Local/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"

script = r"""#!/bin/bash
sudo -u thisminute /opt/thisminute/venv/bin/python3 -c "
import sqlite3
conn = sqlite3.connect('/opt/thisminute/data/thisminute.db')
conn.row_factory = sqlite3.Row

# Run the exact query the API uses
n_id = 1  # first narrative
rows = conn.execute('''
    SELECT DISTINCT es.story_id, se.bright_side_score
    FROM narrative_events ne
    JOIN event_stories es ON es.event_id = ne.event_id
    LEFT JOIN story_extractions se ON se.story_id = es.story_id
    WHERE ne.narrative_id = ?
''', (n_id,)).fetchall()
print(f'Narrative {n_id}: {len(rows)} story rows')
if rows:
    sids = [r['story_id'] for r in rows]
    print(f'  First 5 story_ids: {sids[:5]}')
    bright = sum(1 for r in rows if r['bright_side_score'] and int(r['bright_side_score']) >= 4)
    print(f'  Bright count: {bright}')
else:
    # Debug: check tables
    ne = conn.execute('SELECT COUNT(*) FROM narrative_events WHERE narrative_id = ?', (n_id,)).fetchone()[0]
    print(f'  narrative_events for {n_id}: {ne}')
    if ne:
        eids = [r[0] for r in conn.execute('SELECT event_id FROM narrative_events WHERE narrative_id = ?', (n_id,)).fetchall()]
        print(f'  event_ids: {eids[:5]}')
        for eid in eids[:3]:
            es = conn.execute('SELECT COUNT(*) FROM event_stories WHERE event_id = ?', (eid,)).fetchone()[0]
            print(f'  event {eid} -> {es} stories')
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
