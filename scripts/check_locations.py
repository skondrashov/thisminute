"""Check event location quality — find obvious mismatches."""
import sqlite3
import os
import re

DB = os.environ.get("DB_PATH", "/opt/thisminute/data/thisminute.db")

# Known location mismatches: events where the title clearly mentions a place
# but the location is wrong
LOCATION_CHECKS = [
    # (title_pattern, expected_country_or_city, what's wrong)
    ("Beverly Hills", "United States", "Often geocoded to Australia"),
    ("Wall Street", "United States", "Financial district"),
    ("White House", "United States", "US political"),
    ("Pentagon", "United States", "US military"),
    ("Capitol Hill", "United States", "US politics"),
]

def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    # Events with no location at all
    no_loc = conn.execute(
        """SELECT COUNT(*) as c FROM events
           WHERE merged_into IS NULL AND status != 'resolved'
           AND story_count >= 3
           AND (primary_location IS NULL OR primary_location = '')"""
    ).fetchone()['c']
    total_multi = conn.execute(
        """SELECT COUNT(*) as c FROM events
           WHERE merged_into IS NULL AND status != 'resolved'
           AND story_count >= 3"""
    ).fetchone()['c']
    print(f"Multi-story events (3+): {total_multi}")
    print(f"  Without location: {no_loc} ({100*no_loc/max(total_multi,1):.0f}%)")

    # Events with location but no coordinates
    no_coords = conn.execute(
        """SELECT COUNT(*) as c FROM events
           WHERE merged_into IS NULL AND status != 'resolved'
           AND story_count >= 3
           AND primary_location IS NOT NULL AND primary_location != ''
           AND (primary_lat IS NULL OR primary_lon IS NULL)"""
    ).fetchone()['c']
    print(f"  With location name but no coords: {no_coords}")

    # Non-terrestrial events (space, internet, abstract)
    for etype in ['space', 'internet', 'abstract']:
        cnt = conn.execute(
            """SELECT COUNT(*) as c FROM events
               WHERE merged_into IS NULL AND status != 'resolved'
               AND story_count >= 2 AND event_type = ?""",
            (etype,),
        ).fetchone()['c']
        if cnt > 0:
            print(f"  {etype} events: {cnt}")

    # Sample of events with potentially wrong locations
    print("\n=== SAMPLE: Events with locations that might be wrong ===")
    rows = conn.execute(
        """SELECT id, title, primary_location, primary_lat, primary_lon, story_count
           FROM events
           WHERE merged_into IS NULL AND status != 'resolved'
           AND story_count >= 5 AND primary_location IS NOT NULL
           ORDER BY story_count DESC
           LIMIT 30"""
    ).fetchall()
    for r in rows:
        title_lower = r['title'].lower()
        loc = r['primary_location'] or ''
        suspicious = False
        # Check for obvious mismatches
        if 'iran' in title_lower and 'australia' in loc.lower():
            suspicious = True
        if 'us ' in title_lower or 'trump' in title_lower or 'white house' in title_lower:
            if 'united states' not in loc.lower() and 'washington' not in loc.lower():
                if loc and 'iran' not in title_lower:
                    suspicious = True
        if 'beverly hills' in title_lower and 'australia' in loc.lower():
            suspicious = True

        if suspicious:
            print(f"  [{r['id']}] ({r['story_count']} stories) {r['title'][:55]}")
            print(f"    Location: {loc}")

    conn.close()

if __name__ == "__main__":
    main()
