"""Resolve events that are clearly radio show/podcast junk content.

Run on VM:
    sudo -u thisminute /opt/thisminute/venv/bin/python /opt/thisminute/scripts/resolve_junk_events.py
"""
import re
import sqlite3
import os

DB = os.environ.get("DB_PATH", "/opt/thisminute/data/thisminute.db")

# Same patterns as the GDELT filter
_JUNK_PATTERNS = [
    re.compile(r"\bFULL SHOW\b", re.IGNORECASE),
    re.compile(r"\bFull\s+\w+\s+Show\b"),
    re.compile(r"\bPT\s*[12345]\b.*:"),
    re.compile(r"\|\s*\d+\.\d+\s+\w"),
    re.compile(r"\|\s*(K[A-Z0-9]{2,5}|W[A-Z0-9]{2,5})\b"),
    re.compile(r"\|\s*\w+\s+(FM|AM)\b"),
    re.compile(r"Carroll Broadcasting", re.IGNORECASE),
]

# Additional event-level junk patterns
_JUNK_EVENT_PATTERNS = [
    re.compile(r"^Big Rig ROCK Report"),
    re.compile(r"^GrAudio Flash"),
    re.compile(r"Radio Programming$", re.IGNORECASE),
]


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    # Find active events with junk titles
    events = conn.execute(
        """SELECT id, title, story_count FROM events
        WHERE merged_into IS NULL AND status != 'resolved'"""
    ).fetchall()

    resolved = 0
    for e in events:
        title = e["title"]
        is_junk = any(p.search(title) for p in _JUNK_PATTERNS + _JUNK_EVENT_PATTERNS)
        if is_junk:
            print(f"  Resolving [{e['id']}] {e['story_count']:3d} stories: {title[:55]}")
            conn.execute("UPDATE events SET status = 'resolved' WHERE id = ?", (e["id"],))
            resolved += 1

    conn.commit()
    print(f"\nResolved {resolved} junk events")
    conn.close()


if __name__ == "__main__":
    main()
