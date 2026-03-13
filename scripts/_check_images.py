"""Check if image_url is being extracted from RSS feeds."""
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

# Check recent stories for image_url
row = conn.execute('''
    SELECT
        COUNT(*) as total,
        SUM(CASE WHEN image_url IS NOT NULL AND image_url != '' THEN 1 ELSE 0 END) as has_image
    FROM stories
    WHERE scraped_at >= datetime('now', '-1 hour')
''').fetchone()

print(f'Stories in last hour: {row["total"]}')
print(f'  With images: {row["has_image"]}')
if row['total'] > 0:
    print(f'  Image rate: {100*row["has_image"]/row["total"]:.0f}%')

# Show some examples
rows = conn.execute('''
    SELECT title, source, image_url
    FROM stories
    WHERE image_url IS NOT NULL AND image_url != ''
    AND scraped_at >= datetime('now', '-2 hours')
    ORDER BY scraped_at DESC
    LIMIT 5
''').fetchall()

if rows:
    print()
    print('=== Recent stories with images ===')
    for r in rows:
        print(f'  [{r["source"]}] {r["title"][:60]}')
        print(f'    img: {r["image_url"][:80]}')
else:
    print()
    print('No images found yet (may need to wait for next scrape cycle)')

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
