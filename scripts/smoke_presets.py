#!/usr/bin/env python3
"""Production smoke test: verify every preset has both events and situations.

Hits the live API, applies the same filtering logic the frontend uses,
and reports which presets have gaps. Exit code 0 = all healthy, 1 = gaps found.

Usage:
    python scripts/smoke_presets.py                          # default: https://thisminute.org
    python scripts/smoke_presets.py http://localhost:8000     # local dev
    python scripts/smoke_presets.py --db                      # query DB directly (on VM)
"""

import argparse
import json
import sys
from urllib.request import urlopen, Request

# ---------------------------------------------------------------------------
# Frontend preset definitions (mirrors src/js/state.js)
# ---------------------------------------------------------------------------
PRESET_DOMAIN_MAP = {
    "bright_side": "positive",
    "sports": "sports",
    "entertainment": "entertainment",
    "curious": "curious",
    "conflict": "news",
    "power": "news",
    "health": "health",
    "science": "science",
    "tech": "science",
    "markets": "business",
}

# Presets that intentionally hide situations
DOMAINLESS_HIDE = {"planet", "travel"}

# All domain presets that should have both events and situations
DOMAIN_PRESETS = [
    "sports", "entertainment", "curious", "science", "tech",
    "markets", "health", "conflict", "power", "bright_side",
]


def fetch_json(url):
    req = Request(url, headers={"User-Agent": "smoke-presets/1.0"})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def filter_events_for_preset(events, preset):
    """Apply the frontend's event filtering logic for a domain preset."""
    domain = PRESET_DOMAIN_MAP.get(preset)
    if not domain:
        return events  # "all" preset — no filtering

    return [
        e for e in events
        if domain in (e.get("domains") or [])
        or _has_story_overlap_placeholder(e)  # storyIds check would go here
    ]


def _has_story_overlap_placeholder(event):
    """In production smoke, we can't replicate the full storyIds check
    (that requires geojson + source matching). We rely on domain tags.
    Events without domain tags are treated as unmatched."""
    return False


def filter_narratives_for_preset(narratives, preset):
    """Apply the frontend's narrative filtering logic for a domain preset."""
    if preset in DOMAINLESS_HIDE:
        return []

    domain = PRESET_DOMAIN_MAP.get(preset)
    if not domain:
        return narratives

    return [n for n in narratives if (n.get("domain") or "news") == domain]


def run_api_smoke(base_url):
    """Hit the live API and check each preset."""
    print(f"Fetching from {base_url}...")

    events = fetch_json(f"{base_url}/api/events?limit=50&min_stories=2").get("events", [])
    narratives = fetch_json(f"{base_url}/api/narratives").get("narratives", [])

    print(f"  Total events: {len(events)}")
    print(f"  Total narratives: {len(narratives)}")

    # Count events with domain tags
    with_domains = sum(1 for e in events if e.get("domains"))
    print(f"  Events with domain tags: {with_domains}")
    print()

    gaps = []
    print(f"{'Preset':<16} {'Events':>7} {'Situations':>11}  Status")
    print("-" * 52)

    for preset in DOMAIN_PRESETS:
        domain = PRESET_DOMAIN_MAP.get(preset, "?")
        ev = filter_events_for_preset(events, preset)
        na = filter_narratives_for_preset(narratives, preset)

        ev_count = len(ev)
        na_count = len(na)

        if preset in DOMAINLESS_HIDE:
            status = "OK (situations hidden)"
        elif ev_count == 0 and na_count == 0:
            status = "⚠ EMPTY (both)"
            gaps.append((preset, "both"))
        elif ev_count == 0:
            status = "⚠ NO EVENTS"
            gaps.append((preset, "events"))
        elif na_count == 0:
            status = "⚠ NO SITUATIONS"
            gaps.append((preset, "situations"))
        else:
            status = "✓"

        print(f"  {preset:<14} {ev_count:>7} {na_count:>11}  {status}")

    print()

    # Domain breakdown
    print("Domain tag distribution on events:")
    domain_counts = {}
    for e in events:
        for d in e.get("domains") or []:
            domain_counts[d] = domain_counts.get(d, 0) + 1
    for d in sorted(domain_counts, key=domain_counts.get, reverse=True):
        print(f"  {d}: {domain_counts[d]}")
    if not domain_counts:
        print("  (none — domain tags may not be deployed yet)")
    print()

    if gaps:
        print(f"FAIL: {len(gaps)} preset(s) with gaps:")
        for preset, what in gaps:
            print(f"  {preset}: missing {what}")
        return 1
    else:
        print("PASS: all domain presets have both events and situations")
        return 0


def run_db_smoke():
    """Query the DB directly (for use on the VM)."""
    import sqlite3
    import os

    db_path = os.environ.get("DB_PATH", "/opt/thisminute/data/thisminute.db")
    if not os.path.exists(db_path):
        # Try local dev path
        db_path = "data/thisminute.db"
    print(f"Querying DB at {db_path}...")

    conn = sqlite3.connect(f"file:///{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    # Count events per domain via narrative links
    rows = conn.execute("""
        SELECT n.domain, COUNT(DISTINCT ne.event_id) as event_count
        FROM narratives n
        JOIN narrative_events ne ON n.id = ne.narrative_id
        WHERE n.status = 'active'
        GROUP BY n.domain
    """).fetchall()
    events_by_domain = {r["domain"]: r["event_count"] for r in rows}

    # Count active narratives per domain
    rows = conn.execute("""
        SELECT domain, COUNT(*) as cnt
        FROM narratives WHERE status = 'active'
        GROUP BY domain
    """).fetchall()
    narrs_by_domain = {r["domain"]: r["cnt"] for r in rows}

    gaps = []
    print(f"\n{'Domain':<16} {'Events':>7} {'Situations':>11}  Status")
    print("-" * 52)

    for domain in sorted(set(PRESET_DOMAIN_MAP.values())):
        ev = events_by_domain.get(domain, 0)
        na = narrs_by_domain.get(domain, 0)

        presets = [p for p, d in PRESET_DOMAIN_MAP.items() if d == domain]

        if ev == 0 and na == 0:
            status = "⚠ EMPTY"
            gaps.append((domain, "both"))
        elif ev == 0:
            status = "⚠ NO EVENTS"
            gaps.append((domain, "events"))
        elif na == 0:
            status = "⚠ NO SITUATIONS"
            gaps.append((domain, "situations"))
        else:
            status = "✓"

        presets_str = ", ".join(presets)
        print(f"  {domain:<14} {ev:>7} {na:>11}  {status}  ({presets_str})")

    # Also check: total events, how many have narrative links
    total_events = conn.execute(
        "SELECT COUNT(*) FROM events WHERE merged_into IS NULL AND status != 'resolved'"
    ).fetchone()[0]
    linked_events = conn.execute(
        """SELECT COUNT(DISTINCT ne.event_id) FROM narrative_events ne
           JOIN events e ON e.id = ne.event_id
           WHERE e.merged_into IS NULL AND e.status != 'resolved'"""
    ).fetchone()[0]
    print(f"\n  Total active events: {total_events}")
    print(f"  Events linked to narratives: {linked_events}")
    print(f"  Unlinked events: {total_events - linked_events}")

    conn.close()
    print()

    if gaps:
        print(f"FAIL: {len(gaps)} domain(s) with gaps:")
        for domain, what in gaps:
            print(f"  {domain}: missing {what}")
        return 1
    else:
        print("PASS: all domains have both events and situations")
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smoke test preset completeness")
    parser.add_argument("base_url", nargs="?", default="https://thisminute.org",
                        help="Base URL to test (default: https://thisminute.org)")
    parser.add_argument("--db", action="store_true",
                        help="Query DB directly instead of API (for VM use)")
    args = parser.parse_args()

    if args.db:
        sys.exit(run_db_smoke())
    else:
        sys.exit(run_api_smoke(args.base_url))
