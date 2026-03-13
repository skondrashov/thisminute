"""Check age distribution of singleton events and resolve stale ones."""
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

rows = conn.execute('''
SELECT
  CASE
    WHEN last_updated >= datetime('now', '-1 day') THEN '< 1 day'
    WHEN last_updated >= datetime('now', '-3 days') THEN '1-3 days'
    WHEN last_updated >= datetime('now', '-7 days') THEN '3-7 days'
    ELSE '> 7 days'
  END as age_bucket,
  COUNT(*) as cnt
FROM events
WHERE merged_into IS NULL AND status != 'resolved' AND story_count = 1
GROUP BY age_bucket
ORDER BY MIN(last_updated)
''').fetchall()

print('Singleton event age distribution:')
for r in rows:
    print(f'  {r["age_bucket"]}: {r["cnt"]}')

# Resolve stale singletons > 3 days old
cursor = conn.execute('''
    UPDATE events SET status = 'resolved'
    WHERE merged_into IS NULL AND status != 'resolved'
    AND story_count = 1
    AND last_updated < datetime('now', '-3 days')
''')
print(f'\\nResolved {cursor.rowcount} stale singletons (>3 days, never grew)')
conn.commit()

# Show final state
row = conn.execute('''
    SELECT COUNT(*) as total,
           SUM(CASE WHEN story_count = 1 THEN 1 ELSE 0 END) as singles,
           SUM(CASE WHEN story_count > 1 THEN 1 ELSE 0 END) as multi
    FROM events WHERE merged_into IS NULL AND status != 'resolved'
''').fetchone()
print(f'\\nActive events: {row["total"]}')
print(f'  Single-story: {row["singles"]} ({100*row["singles"]/max(row["total"],1):.1f}%)')
print(f'  Multi-story:  {row["multi"]} ({100*row["multi"]/max(row["total"],1):.1f}%)')

conn.close()
"""

b64 = base64.b64encode(SCRIPT).decode()
cmd = f"echo {b64} | base64 -d | sudo -u thisminute /opt/thisminute/venv/bin/python"

r = subprocess.run(
    [GCLOUD, "compute", "ssh", "thisminute", "--zone=us-central1-a", "--command", cmd],
    capture_output=True, text=True, timeout=120,
)
print(r.stdout, flush=True)
if r.stderr:
    print(r.stderr, flush=True)
