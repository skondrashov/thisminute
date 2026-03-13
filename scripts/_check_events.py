"""Check event quality: titles, descriptions, source diversity."""
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

# Top 20 multi-story events with their titles and descriptions
rows = conn.execute('''
    SELECT e.id, e.title, e.description, e.story_count, e.status,
           e.primary_location, e.severity,
           (SELECT COUNT(DISTINCT s.source)
            FROM event_stories es JOIN stories s ON es.story_id = s.id
            WHERE es.event_id = e.id) as source_count
    FROM events e
    WHERE e.merged_into IS NULL AND e.status != 'resolved'
    AND e.story_count >= 2
    ORDER BY e.story_count DESC
    LIMIT 20
''').fetchall()

print('=== Top 20 multi-story events ===')
for r in rows:
    desc_preview = (r['description'] or '')[:80]
    print(f"  [{r['story_count']} stories, {r['source_count']} sources, sev={r['severity']}] {r['title']}")
    if desc_preview:
        print(f"    desc: {desc_preview}...")

# Check how many events have descriptions vs raw headlines
print()
row = conn.execute('''
    SELECT
        COUNT(*) as total,
        SUM(CASE WHEN description IS NOT NULL AND description != '' THEN 1 ELSE 0 END) as has_desc,
        SUM(CASE WHEN description IS NULL OR description = '' THEN 1 ELSE 0 END) as no_desc
    FROM events
    WHERE merged_into IS NULL AND status != 'resolved' AND story_count >= 2
''').fetchone()
print(f'Multi-story events with descriptions: {row["has_desc"]}/{row["total"]}')
print(f'Multi-story events without descriptions: {row["no_desc"]}/{row["total"]}')

# Check situation counts by domain
print()
rows = conn.execute('''
    SELECT domain, COUNT(*) as cnt,
           SUM(CASE WHEN event_count > 0 THEN 1 ELSE 0 END) as with_events
    FROM narratives
    WHERE status = 'active'
    GROUP BY domain
''').fetchall()
print('=== Active situations by domain ===')
for r in rows:
    print(f"  {r['domain']}: {r['cnt']} ({r['with_events']} with events)")

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
