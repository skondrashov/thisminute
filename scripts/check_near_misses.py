"""Find near-miss singleton pairs that might benefit from better fuzzy matching."""
import sqlite3
import os
import re
from collections import Counter, defaultdict

DB = os.environ.get("DB_PATH", "/opt/thisminute/data/thisminute.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
    "be", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "that", "this",
    "it", "its", "not", "no", "if", "up", "out", "new", "says", "said",
    "over", "after", "into", "how", "what", "when", "where", "who", "why",
    "all", "about", "than", "more", "some", "so", "just", "also", "now",
}


def sig_words(sig):
    if not sig:
        return set()
    return {w.lower() for w in re.findall(r"\w+", sig) if len(w) >= 2 and w.lower() not in STOPWORDS}


# Load all active singleton signatures
print("Loading singleton signatures...", flush=True)
rows = conn.execute(
    """SELECT e.id, e.title,
        (SELECT se.event_signature FROM story_extractions se
         JOIN event_stories es ON se.story_id = es.story_id
         WHERE es.event_id = e.id LIMIT 1) as sig
    FROM events e
    WHERE e.merged_into IS NULL AND e.status != 'resolved' AND e.story_count = 1
    ORDER BY e.first_seen DESC"""
).fetchall()
print(f"Total singletons: {len(rows)}", flush=True)

# Build word -> event_id index for fast overlap detection
word_index = defaultdict(set)
sigs = {}
for r in rows:
    eid = r["id"]
    sig = r["sig"] or ""
    words = sig_words(sig)
    sigs[eid] = (sig, words, r["title"])
    for w in words:
        word_index[w].add(eid)

# Find pairs with 2+ word overlap (potential merges)
print("\nScanning for near-miss pairs (2+ word overlap)...", flush=True)
pair_count = 0
merge_candidates = 0
checked = set()

# Only check recent singletons (last 24h = first ~4000)
recent = [r["id"] for r in rows[:4000]]

for eid in recent:
    sig, words, title = sigs[eid]
    if len(words) < 2:
        continue

    # Find candidate events sharing at least 2 words
    candidates = Counter()
    for w in words:
        for other_id in word_index[w]:
            if other_id != eid and other_id not in checked:
                candidates[other_id] += 1

    for other_id, overlap in candidates.most_common(5):
        if overlap < 2:
            break
        other_sig, other_words, other_title = sigs[other_id]
        # Compute Dice coefficient
        intersection = words & other_words
        dice = 2 * len(intersection) / (len(words) + len(other_words)) if (len(words) + len(other_words)) > 0 else 0
        if dice >= 0.35:  # Near-miss threshold
            merge_candidates += 1
            if merge_candidates <= 30:
                print(f"  Dice={dice:.2f} overlap={len(intersection)} [{eid}] {sig[:30]} <-> [{other_id}] {other_sig[:30]}")
                print(f"    -> {title[:50]}")
                print(f"    -> {other_title[:50]}")

    checked.add(eid)

print(f"\nTotal near-miss pairs (Dice>=0.35, 2+ overlap): {merge_candidates}")

# Also check: how many singletons share the EXACT same signature as another singleton?
print("\n=== Exact duplicate signatures among singletons ===")
sig_groups = defaultdict(list)
for eid, (sig, words, title) in sigs.items():
    if sig:
        sig_groups[sig].append(eid)

dupe_sigs = {s: ids for s, ids in sig_groups.items() if len(ids) > 1}
print(f"Signatures shared by 2+ singletons: {len(dupe_sigs)}")
for sig, ids in sorted(dupe_sigs.items(), key=lambda x: -len(x[1]))[:15]:
    titles = [sigs[i][2][:40] for i in ids[:3]]
    print(f"  sig={sig[:35]} count={len(ids)} titles={titles}")

conn.close()
