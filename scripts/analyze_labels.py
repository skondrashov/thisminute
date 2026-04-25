"""Analyze story categorization quality across presets.

Finds mislabeled stories and exemplary fits.
"""
import sqlite3
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import FEED_TAG_MAP


def main():
    conn = sqlite3.connect("data/thisminute.db")
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT s.id, s.title, s.source,
               se.topics, se.severity, se.bright_side_score, se.human_interest_score,
               se.sentiment, se.event_signature
        FROM stories s
        JOIN story_extractions se ON se.story_id = s.id
        ORDER BY s.id DESC LIMIT 1000
    """).fetchall()

    buckets = {k: [] for k in ["sports", "entertainment", "science", "tech", "business", "health", "bright_side", "curious"]}

    for r in rows:
        title = (r["title"] or "")[:90]
        source = r["source"] or ""
        tags = FEED_TAG_MAP.get(source, [])
        topics = json.loads(r["topics"]) if r["topics"] else []
        bs = int(r["bright_side_score"]) if r["bright_side_score"] else 0
        hi = int(r["human_interest_score"]) if r["human_interest_score"] else 0
        sev = r["severity"] or 2
        sent = r["sentiment"] or "neutral"

        story = {"title": title, "source": source, "topics": topics[:4], "bs": bs, "hi": hi, "sev": sev, "sent": sent}

        if "sports" in tags: buckets["sports"].append(story)
        if "entertainment" in tags: buckets["entertainment"].append(story)
        if any(t in tags for t in ["science", "tech"]): buckets["science"].append(story)
        if "tech" in tags: buckets["tech"].append(story)
        if "business" in tags: buckets["business"].append(story)
        if "health" in tags: buckets["health"].append(story)
        if bs >= 4: buckets["bright_side"].append(story)
        if hi >= 7: buckets["curious"].append(story)

    sep = "=" * 90

    # --- MISLABELED ---
    print(sep)
    print("MISLABELED / QUESTIONABLE STORIES BY PRESET")
    print(sep)

    # Entertainment: news/politics
    print("\n--- ENTERTAINMENT: News/politics stories from entertainment feeds ---")
    news_slugs = ["politics", "election", "government", "war", "conflict", "military", "sanctions", "legislation"]
    for s in buckets["entertainment"][:150]:
        tstr = " ".join(s["topics"])
        if any(slug in tstr for slug in news_slugs):
            print(f'  [{s["source"]:>20}] {s["title"]}')
            print(f'    topics: {s["topics"]}')

    # Business: pure war
    print("\n--- BUSINESS: War stories without market angle ---")
    biz_slugs = ["oil", "trade", "stock", "market", "economy", "tariff", "crypto", "bitcoin", "fed", "inflation", "earnings", "ipo"]
    war_slugs = ["war", "military", "conflict", "airstrike", "bombing", "invasion", "troops"]
    for s in buckets["business"][:150]:
        tstr = " ".join(s["topics"])
        has_war = any(slug in tstr for slug in war_slugs)
        has_biz = any(slug in tstr for slug in biz_slugs)
        if has_war and not has_biz:
            print(f'  [{s["source"]:>20}] {s["title"]}')
            print(f'    topics: {s["topics"]}')

    # Science/Tech: crypto/gaming
    print("\n--- SCIENCE/TECH: Non-science stories from science/tech feeds ---")
    nonsci_slugs = ["crypto", "bitcoin", "blockchain", "nft", "gaming", "video-game", "entertainment", "celebrity", "oscars"]
    for s in buckets["science"][:150]:
        tstr = " ".join(s["topics"])
        if any(slug in tstr for slug in nonsci_slugs):
            print(f'  [{s["source"]:>20}] {s["title"]}')
            print(f'    topics: {s["topics"]}')

    # Sports: non-sports
    print("\n--- SPORTS: Non-sports stories from sports feeds ---")
    sport_slugs = ["sports", "football", "cricket", "rugby", "tennis", "golf", "basketball", "baseball",
                   "hockey", "f1", "motorsport", "boxing", "mma", "athletics", "swimming", "cycling",
                   "nfl", "nba", "mlb", "nhl", "ipl", "premier-league", "la-liga", "champions-league",
                   "world-cup", "olympics", "racing", "grand-prix"]
    for s in buckets["sports"][:150]:
        tstr = " ".join(s["topics"])
        if not any(slug in tstr for slug in sport_slugs):
            print(f'  [{s["source"]:>20}] {s["title"]}')
            print(f'    topics: {s["topics"]}')

    # Bright Side: grim
    print("\n--- BRIGHT SIDE: Negative/high-severity stories that scored >= 4 ---")
    for s in buckets["bright_side"][:150]:
        if s["sent"] == "negative" or s["sev"] >= 4:
            print(f'  [bs={s["bs"]}, sev={s["sev"]}, {s["sent"]}] {s["title"]}')
            print(f'    topics: {s["topics"]}')

    # Curious: dark
    print("\n--- CURIOUS: Dark/violent stories that scored >= 7 ---")
    dark = ["kill", "dead", "death", "die", "dies", "died", "fatal", "murder", "attack",
            "bomb", "war", "troops", "massacre", "shot", "stabbed", "crash"]
    for s in buckets["curious"][:150]:
        words = s["title"].lower().split()
        if any(w in words for w in dark):
            print(f'  [hi={s["hi"]}, {s["sent"]}] {s["title"]}')
            print(f'    topics: {s["topics"]}')

    # --- EXEMPLARY ---
    print(f"\n{sep}")
    print("EXEMPLARY STORIES (great fit for their preset)")
    print(sep)

    print("\n--- BRIGHT SIDE: Best (positive, low severity, high score) ---")
    best = sorted([s for s in buckets["bright_side"] if s["sent"] == "positive" and s["sev"] <= 2], key=lambda x: -x["bs"])[:10]
    for s in best:
        print(f'  [bs={s["bs"]}] [{s["source"]}] {s["title"]}')

    print("\n--- CURIOUS: Best (quirky, not negative, high score) ---")
    best = sorted([s for s in buckets["curious"] if s["sent"] != "negative"], key=lambda x: -x["hi"])[:10]
    for s in best:
        print(f'  [hi={s["hi"]}] [{s["source"]}] {s["title"]}')

    print("\n--- SPORTS: Best (clearly sports, high engagement) ---")
    best = sorted([s for s in buckets["sports"] if s["sev"] >= 2], key=lambda x: -x["sev"])[:10]
    for s in best:
        print(f'  [sev={s["sev"]}] [{s["source"]}] {s["title"]}')

    print("\n--- ENTERTAINMENT: Best (clearly entertainment, not news) ---")
    ent_slugs = ["film", "movie", "music", "album", "concert", "oscar", "grammy", "emmy", "celebrity",
                 "tv", "streaming", "bollywood", "k-pop", "k-drama", "broadway", "theater"]
    best = [s for s in buckets["entertainment"][:150] if any(slug in " ".join(s["topics"]) for slug in ent_slugs)][:10]
    for s in best:
        print(f'  [{s["source"]}] {s["title"]}')
        print(f'    topics: {s["topics"]}')

    print("\n--- SCIENCE: Best (clearly science, not crypto/gaming) ---")
    sci_slugs = ["research", "discovery", "space", "climate", "quantum", "gene", "brain", "physics",
                 "biology", "chemistry", "astronomy", "ai-research", "robotics", "neuroscience"]
    best = [s for s in buckets["science"][:150] if any(slug in " ".join(s["topics"]) for slug in sci_slugs)][:10]
    for s in best:
        print(f'  [{s["source"]}] {s["title"]}')
        print(f'    topics: {s["topics"]}')

    conn.close()


if __name__ == "__main__":
    main()
