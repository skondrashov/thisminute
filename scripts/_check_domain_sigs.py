"""Check event signatures for sports and entertainment events."""
import subprocess
import sys
import os
import base64

GCLOUD = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "Google", "Cloud SDK", "google-cloud-sdk", "bin", "gcloud.cmd",
)

SCRIPT = b"""#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/opt/thisminute/data/thisminute.db')
conn.row_factory = sqlite3.Row

# Sports event signatures (from sports-tagged sources)
sports_sources = ['ESPN', 'ESPN Soccer', 'ESPNcricinfo', 'Sky Sports', 'Sportstar', 'Autosport', 'Rugby World',
                  'ESPN NFL', 'ESPN NBA', 'ESPN MLB', 'ESPN Top', 'ESPN NHL', 'ESPN College Football',
                  'ESPN College Basketball', 'ESPN MMA', 'ESPN Racing', 'ESPN Golf', 'ESPN Tennis',
                  'Cricbuzz', 'Indian Express Sports']
ph = ','.join('?' * len(sports_sources))

# Most common sports event signatures
rows = conn.execute(f'''
    SELECT se.event_signature, COUNT(*) as cnt
    FROM story_extractions se
    JOIN stories s ON se.story_id = s.id
    WHERE s.source IN ({ph})
    AND se.event_signature IS NOT NULL AND se.event_signature != ''
    GROUP BY se.event_signature
    ORDER BY cnt DESC
    LIMIT 20
''', sports_sources).fetchall()

print('=== Top 20 Sports Event Signatures ===')
for r in rows:
    print(f'  [{r["cnt"]}x] {r["event_signature"]}')

# Entertainment event signatures
ent_sources = ['Variety', 'Hollywood Reporter', 'Deadline', 'Rolling Stone', 'Billboard',
               'Pitchfork', 'NME', 'Soompi', 'Bollywood Hungama',
               'Indian Express Entertainment', 'BBC Entertainment',
               'Times of India Entertainment', 'Hindustan Times Entertainment']
ph2 = ','.join('?' * len(ent_sources))

rows = conn.execute(f'''
    SELECT se.event_signature, COUNT(*) as cnt
    FROM story_extractions se
    JOIN stories s ON se.story_id = s.id
    WHERE s.source IN ({ph2})
    AND se.event_signature IS NOT NULL AND se.event_signature != ''
    GROUP BY se.event_signature
    ORDER BY cnt DESC
    LIMIT 20
''', ent_sources).fetchall()

print()
print('=== Top 20 Entertainment Event Signatures ===')
for r in rows:
    print(f'  [{r["cnt"]}x] {r["event_signature"]}')

# Single-story sports events (signatures used only once)
rows = conn.execute(f'''
    SELECT se.event_signature, s.title
    FROM story_extractions se
    JOIN stories s ON se.story_id = s.id
    WHERE s.source IN ({ph})
    AND se.event_signature IS NOT NULL AND se.event_signature != ''
    GROUP BY se.event_signature
    HAVING COUNT(*) = 1
    ORDER BY s.scraped_at DESC
    LIMIT 10
''', sports_sources).fetchall()

print()
print('=== Recent Singleton Sports Signatures ===')
for r in rows:
    print(f'  sig: {r["event_signature"]}')
    print(f'    title: {r["title"][:80]}')

conn.close()
"""

b64 = base64.b64encode(SCRIPT).decode()
cmd = f"echo {b64} | base64 -d | sudo -u thisminute /opt/thisminute/venv/bin/python"

r = subprocess.run(
    [GCLOUD, "compute", "ssh", "thisminute", "--zone=us-central1-a", "--command", cmd],
    capture_output=True, text=True, timeout=60,
)
print(r.stdout, flush=True)
if r.stderr:
    print(r.stderr, flush=True)
