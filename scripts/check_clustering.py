"""Check clustering quality: find singletons that might match existing events."""
import sqlite3
import re
import os

DB = os.environ.get("DB_PATH", "/opt/thisminute/data/thisminute.db")

_STOPWORDS = frozenset({
    "the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or", "is",
    "are", "was", "were", "be", "has", "have", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "over", "after",
    "before", "by", "with", "from", "up", "about", "into", "through", "new",
    "says", "said", "amid", "as", "its", "their", "his", "her", "but", "not",
})

def sig_words(sig):
    if not sig:
        return set()
    words = set(re.findall(r"[a-z]+", sig.lower()))
    return {w for w in words if w not in _STOPWORDS and len(w) > 1}

def dice(a, b):
    wa, wb = sig_words(a), sig_words(b)
    if not wa or not wb:
        return 0.0
    inter = wa & wb
    if len(inter) < 2:
        return 0.0
    return 2 * len(inter) / (len(wa) + len(wb))


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    # Get recent singletons with signatures
    singletons = conn.execute(
        """SELECT e.id, e.title, e.story_count, se.event_signature
           FROM events e
           JOIN event_stories es ON e.id = es.event_id
           JOIN story_extractions se ON es.story_id = se.story_id
           WHERE e.merged_into IS NULL AND e.status != 'resolved'
           AND e.story_count = 1
           AND e.last_updated > datetime('now', '-2 days')
           AND se.event_signature IS NOT NULL AND se.event_signature != ''
           ORDER BY e.last_updated DESC
           LIMIT 100"""
    ).fetchall()
    print(f"Recent singletons with signatures: {len(singletons)}")

    # Get multi-story events with all their signatures
    multi_ids = conn.execute(
        """SELECT id FROM events
           WHERE merged_into IS NULL AND e.status != 'resolved'
           AND story_count >= 3
           ORDER BY story_count DESC LIMIT 200"""
    ).fetchall() if False else []

    # Simpler: get multi-story event sigs directly
    multi_rows = conn.execute(
        """SELECT e.id, e.title, e.story_count, se.event_signature
           FROM events e
           JOIN event_stories es ON e.id = es.event_id
           JOIN story_extractions se ON es.story_id = se.story_id
           WHERE e.merged_into IS NULL AND e.status != 'resolved'
           AND e.story_count >= 3
           AND se.event_signature IS NOT NULL AND se.event_signature != ''
           ORDER BY e.story_count DESC"""
    ).fetchall()

    multi_sigs = {}
    for r in multi_rows:
        eid = r["id"]
        if eid not in multi_sigs:
            multi_sigs[eid] = {"title": r["title"], "count": r["story_count"], "sigs": set()}
        multi_sigs[eid]["sigs"].add(r["event_signature"])

    print(f"Multi-story events with sigs: {len(multi_sigs)}")

    # Check each singleton against multi-story events
    print("\n=== POTENTIAL MERGES (singleton -> multi-story, score 0.30-0.40) ===")
    missed = 0
    for s in singletons:
        sig = s["event_signature"]
        best_score = 0
        best_target = None
        for eid, info in multi_sigs.items():
            for esig in info["sigs"]:
                score = dice(sig, esig)
                if score > best_score:
                    best_score = score
                    best_target = (eid, info)

        if 0.30 <= best_score < 0.40:
            missed += 1
            if missed <= 15:
                t = best_target[1]
                print(f"  Score {best_score:.2f}: [{s['id']}] \"{s['event_signature']}\"")
                print(f"    -> [{best_target[0]}] ({t['count']} stories) \"{t['title'][:60]}\"")

    print(f"\n  Total near-misses (0.30-0.40): {missed} / {len(singletons)}")

    # Also check matches AT or above threshold that somehow didn't merge
    print("\n=== SHOULD-HAVE-MERGED (score >= 0.40 but still singleton) ===")
    should_have = 0
    for s in singletons:
        sig = s["event_signature"]
        best_score = 0
        best_target = None
        for eid, info in multi_sigs.items():
            for esig in info["sigs"]:
                score = dice(sig, esig)
                if score > best_score:
                    best_score = score
                    best_target = (eid, info)

        if best_score >= 0.40:
            should_have += 1
            if should_have <= 15:
                t = best_target[1]
                print(f"  Score {best_score:.2f}: [{s['id']}] \"{s['event_signature']}\"")
                print(f"    -> [{best_target[0]}] ({t['count']} stories) \"{t['title'][:60]}\"")

    print(f"\n  Total should-have-merged: {should_have} / {len(singletons)}")

    # Singleton-to-singleton matches
    print("\n=== SINGLETON-TO-SINGLETON MATCHES (could group) ===")
    grouped = 0
    seen = set()
    for i, s1 in enumerate(singletons):
        if s1["id"] in seen:
            continue
        group = [s1]
        for s2 in singletons[i+1:]:
            if s2["id"] in seen:
                continue
            score = dice(s1["event_signature"], s2["event_signature"])
            if score >= 0.35:
                group.append(s2)
                seen.add(s2["id"])
        if len(group) >= 2:
            grouped += 1
            if grouped <= 10:
                print(f"  Group ({len(group)} singletons):")
                for g in group[:5]:
                    print(f"    [{g['id']}] sig=\"{g['event_signature']}\"")

    print(f"\n  Total singleton groups: {grouped}")

    # Extraction coverage
    no_extract = conn.execute(
        """SELECT COUNT(*) as c FROM stories s
           LEFT JOIN story_extractions se ON s.id = se.story_id
           WHERE se.story_id IS NULL
           AND s.scraped_at > datetime('now', '-2 days')"""
    ).fetchone()["c"]
    total_recent = conn.execute(
        """SELECT COUNT(*) as c FROM stories
           WHERE scraped_at > datetime('now', '-2 days')"""
    ).fetchone()["c"]
    print(f"\n=== EXTRACTION COVERAGE (last 2 days) ===")
    print(f"  Total stories: {total_recent}")
    print(f"  Without extraction: {no_extract} ({100*no_extract/max(total_recent,1):.1f}%)")

    conn.close()

if __name__ == "__main__":
    main()
