"""Check image rates by source."""
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
    SELECT source,
           COUNT(*) as total,
           SUM(CASE WHEN image_url IS NOT NULL AND image_url != '' THEN 1 ELSE 0 END) as has_image
    FROM stories
    WHERE scraped_at >= datetime('now', '-2 hours')
    GROUP BY source
    HAVING total >= 3
    ORDER BY has_image DESC, total DESC
''').fetchall()

print(f'{"Source":<35} {"Total":>6} {"Images":>6} {"Rate":>6}')
print('-' * 60)
for r in rows:
    rate = f'{100*r["has_image"]/r["total"]:.0f}%' if r['total'] > 0 else '0%'
    print(f'{r["source"]:<35} {r["total"]:>6} {r["has_image"]:>6} {rate:>6}')

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
