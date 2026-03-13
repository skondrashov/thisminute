"""Check bright_side scoring results on production."""
import subprocess
import base64

GCLOUD = "C:/Users/tkond/AppData/Local/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"

script = r"""#!/bin/bash
sudo -u thisminute /opt/thisminute/venv/bin/python3 -c "
import sqlite3, json
conn = sqlite3.connect('/opt/thisminute/data/thisminute.db')
conn.row_factory = sqlite3.Row

# Score distribution
print('=== SCORE DISTRIBUTION ===')
for r in conn.execute('SELECT bright_side_score, COUNT(*) as n FROM story_extractions WHERE bright_side_score IS NOT NULL GROUP BY bright_side_score ORDER BY CAST(bright_side_score AS INTEGER)').fetchall():
    print(f'  Score {r[0]}: {r[1]}')

# How many pass each threshold?
print()
for thresh in [3, 4, 5, 6, 7]:
    cnt = conn.execute('SELECT COUNT(*) FROM story_extractions WHERE CAST(bright_side_score AS INTEGER) >= ?', (thresh,)).fetchone()[0]
    print(f'Score >= {thresh}: {cnt} stories')

# Sample high-scoring stories
print()
print('=== TOP BRIGHT SIDE STORIES (score 7+) ===')
for r in conn.execute('''
    SELECT se.bright_side_headline, se.bright_side_score, se.bright_side_category, s.title, s.source
    FROM story_extractions se JOIN stories s ON s.id = se.story_id
    WHERE CAST(se.bright_side_score AS INTEGER) >= 7
    ORDER BY CAST(se.bright_side_score AS INTEGER) DESC, s.scraped_at DESC
    LIMIT 15
''').fetchall():
    print(f'  [{r[\"bright_side_score\"]}] [{r[\"bright_side_category\"]}] {r[\"bright_side_headline\"]}')
    print(f'       Original: {r[\"title\"][:90]}')
    print()
"
"""

b64 = base64.b64encode(script.encode()).decode()
r = subprocess.run(
    [GCLOUD, "compute", "ssh", "thisminute", "--zone=us-central1-a",
     "--command", f"echo {b64} | base64 -d | bash"],
    capture_output=True, timeout=120, encoding="utf-8", errors="replace",
)
print(r.stdout)
if r.stderr:
    print("ERR:", r.stderr[:500])
