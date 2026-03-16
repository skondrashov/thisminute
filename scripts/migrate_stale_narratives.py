#!/usr/bin/env python3
"""One-time migration: fix stale news narratives that belong in other domains.

Since the news domain no longer claims tech/science/business feed tags,
these narratives won't regenerate in news. But existing ones need to be
re-tagged or deactivated.

Run once: python -m scripts.migrate_stale_narratives
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "thisminute.db"


def migrate(db_path: str = str(DB_PATH), dry_run: bool = True):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Patterns for narratives that should move domains
    DOMAIN_REASSIGNMENTS = [
        # (pattern in title, new domain)
        ("ai research", "science"),
        ("ai advance", "science"),
        ("artificial intelligence", "science"),
        ("machine learning", "science"),
        ("quantum", "science"),
        ("space ", "science"),
        ("nasa", "science"),
        ("climate", "science"),
        ("crypto", "business"),
        ("bitcoin", "business"),
        ("blockchain", "business"),
        ("stock market", "business"),
        ("market surge", "business"),
        ("tariff", "business"),
        ("trade war", "business"),
        ("fed interest", "business"),
        ("oil price", "business"),
    ]

    # Patterns for junk catch-all narratives to deactivate
    JUNK_PATTERNS = [
        "global entertainment, sports",
        "miscellaneous",
        "mixed updates",
        "various ",
        "roundup",
        "highlights 20",
    ]

    rows = conn.execute(
        "SELECT id, title, domain FROM narratives WHERE status = 'active' AND domain = 'news'"
    ).fetchall()

    reassigned = 0
    deactivated = 0

    for row in rows:
        title_lower = (row["title"] or "").lower()

        # Check for domain reassignment
        new_domain = None
        for pattern, domain in DOMAIN_REASSIGNMENTS:
            if pattern in title_lower:
                new_domain = domain
                break

        if new_domain:
            action = f"REASSIGN [{row['id']}] '{row['title']}' -> {new_domain}"
            if dry_run:
                print(f"  [DRY RUN] {action}")
            else:
                conn.execute(
                    "UPDATE narratives SET domain = ? WHERE id = ?",
                    (new_domain, row["id"]),
                )
                print(f"  {action}")
            reassigned += 1
            continue

        # Check for junk patterns
        is_junk = any(p in title_lower for p in JUNK_PATTERNS)
        if is_junk:
            action = f"DEACTIVATE [{row['id']}] '{row['title']}'"
            if dry_run:
                print(f"  [DRY RUN] {action}")
            else:
                conn.execute(
                    "UPDATE narratives SET status = 'inactive' WHERE id = ?",
                    (row["id"],),
                )
                print(f"  {action}")
            deactivated += 1

    if not dry_run:
        conn.commit()

    conn.close()
    print(f"\nTotal: {reassigned} reassigned, {deactivated} deactivated (dry_run={dry_run})")
    return reassigned, deactivated


if __name__ == "__main__":
    dry = "--apply" not in sys.argv
    if dry:
        print("DRY RUN (pass --apply to commit changes)\n")
    else:
        print("APPLYING changes\n")
    migrate(dry_run=dry)
