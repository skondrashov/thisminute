"""One-time cleanup: merge events that share exact event_signatures.

Run on VM:
    sudo -u thisminute /opt/thisminute/venv/bin/python /opt/thisminute/scripts/merge_events.py

Finds active events where multiple events have the same event_signature,
merges smaller events into the largest one per signature group.
Also resolves very old singleton events (>7 days, no growth).
"""
import sqlite3
import sys
import os

DB_PATH = os.environ.get("DB_PATH", "/opt/thisminute/data/thisminute.db")
MAX_EVENT_STORIES = 50


def merge_exact_duplicates(conn):
    """Merge events sharing exact signatures."""
    print("=== Finding duplicate signatures ===", flush=True)

    # Create index if missing
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_extractions_event_signature "
        "ON story_extractions(event_signature)"
    )

    dupe_rows = conn.execute(
        """SELECT se.event_signature,
                  GROUP_CONCAT(DISTINCT es.event_id) as event_ids,
                  COUNT(DISTINCT es.event_id) as event_count
           FROM story_extractions se
           JOIN event_stories es ON se.story_id = es.story_id
           JOIN events e ON es.event_id = e.id
           WHERE e.merged_into IS NULL AND e.status != 'resolved'
           AND se.event_signature IS NOT NULL AND se.event_signature != ''
           GROUP BY se.event_signature
           HAVING COUNT(DISTINCT es.event_id) > 1
           ORDER BY event_count DESC"""
    ).fetchall()

    print(f"Found {len(dupe_rows)} signatures with multiple events", flush=True)
    merged = 0
    stories_moved = 0

    for row in dupe_rows:
        sig = row["event_signature"]
        event_ids = [int(x) for x in row["event_ids"].split(",")]

        events_info = conn.execute(
            f"""SELECT id, story_count FROM events
                WHERE id IN ({','.join('?' * len(event_ids))})
                AND merged_into IS NULL
                ORDER BY story_count DESC""",
            event_ids,
        ).fetchall()

        if len(events_info) < 2:
            continue

        target = events_info[0]
        target_id = target["id"]
        target_count = target["story_count"]

        for source in events_info[1:]:
            source_id = source["id"]
            combined = target_count + source["story_count"]
            if combined > MAX_EVENT_STORIES:
                continue

            before = conn.execute(
                "SELECT COUNT(*) as c FROM event_stories WHERE event_id = ?",
                (source_id,),
            ).fetchone()["c"]

            conn.execute(
                "UPDATE OR IGNORE event_stories SET event_id = ? WHERE event_id = ?",
                (target_id, source_id),
            )
            conn.execute(
                "DELETE FROM event_stories WHERE event_id = ?",
                (source_id,),
            )
            conn.execute(
                "UPDATE events SET merged_into = ? WHERE id = ?",
                (target_id, source_id),
            )
            count = conn.execute(
                "SELECT COUNT(*) as c FROM event_stories WHERE event_id = ?",
                (target_id,),
            ).fetchone()["c"]
            conn.execute(
                "UPDATE events SET story_count = ? WHERE id = ?",
                (count, target_id),
            )
            target_count = count
            stories_moved += before
            merged += 1

        if merged % 500 == 0 and merged > 0:
            conn.commit()
            print(f"  ... merged {merged} events so far ({stories_moved} stories moved)", flush=True)

    conn.commit()
    print(f"Merged {merged} events ({stories_moved} stories moved)", flush=True)
    return merged


def resolve_stale_singletons(conn):
    """Resolve singleton events older than 7 days that never grew."""
    print("=== Resolving stale singletons ===", flush=True)

    cursor = conn.execute(
        """UPDATE events SET status = 'resolved'
           WHERE merged_into IS NULL
           AND status != 'resolved'
           AND story_count = 1
           AND last_updated < datetime('now', '-7 days')"""
    )
    resolved = cursor.rowcount
    conn.commit()
    print(f"Resolved {resolved} stale singletons (>7 days old, never grew)", flush=True)
    return resolved


def report(conn):
    """Print current state."""
    row = conn.execute(
        """SELECT COUNT(*) as total,
                  SUM(CASE WHEN story_count = 1 THEN 1 ELSE 0 END) as singles,
                  SUM(CASE WHEN story_count > 1 THEN 1 ELSE 0 END) as multi
           FROM events
           WHERE merged_into IS NULL AND status != 'resolved'"""
    ).fetchone()
    print(f"\nActive events: {row['total']}", flush=True)
    print(f"  Single-story: {row['singles']} ({100*row['singles']/max(row['total'],1):.1f}%)", flush=True)
    print(f"  Multi-story:  {row['multi']} ({100*row['multi']/max(row['total'],1):.1f}%)", flush=True)


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    print("=== Before ===", flush=True)
    report(conn)

    merge_exact_duplicates(conn)
    resolve_stale_singletons(conn)

    print("\n=== After ===", flush=True)
    report(conn)

    conn.close()
    print("\nDone!", flush=True)
