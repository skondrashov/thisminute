"""Check search_keywords quality."""
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

# Sample search_keywords from recent stories
rows = conn.execute('''
    SELECT s.title, se.search_keywords, se.primary_action
    FROM story_extractions se
    JOIN stories s ON se.story_id = s.id
    WHERE se.search_keywords IS NOT NULL AND se.search_keywords != '[]'
    ORDER BY se.story_id DESC
    LIMIT 10
''').fetchall()

print('=== Recent search_keywords ===')
for r in rows:
    print(f'  title: {r["title"][:70]}')
    print(f'    keywords: {r["search_keywords"]}')
    print(f'    action: {r["primary_action"]}')
    print()

# Check how many stories have search_keywords
row = conn.execute('''
    SELECT COUNT(*) as total,
           SUM(CASE WHEN search_keywords IS NOT NULL AND search_keywords != '[]' AND search_keywords != '' THEN 1 ELSE 0 END) as has_kw
    FROM story_extractions
''').fetchone()
print(f'Stories with search_keywords: {row["has_kw"]}/{row["total"]}')

# Check actor names from story_actors for recent stories
rows = conn.execute('''
    SELECT sa.name, sa.role, s.title
    FROM story_actors sa
    JOIN stories s ON sa.story_id = s.id
    ORDER BY sa.story_id DESC
    LIMIT 20
''').fetchall()
print()
print('=== Recent actor names ===')
for r in rows:
    print(f'  [{r["role"]}] {r["name"]} <- {r["title"][:50]}')

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
