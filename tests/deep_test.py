"""Deep integration & data quality tests for thisminute.org.

Goes beyond smoke tests to verify data integrity, filter combinations,
frontend contract conformance, extraction quality, and regression checks
for previously fixed bugs.

Usage:
    python tests/deep_test.py [--base-url URL] [--verbose]
"""
import argparse
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode, quote

PASS = 0
FAIL = 0
WARN = 0
VERBOSE = False
RESULTS = []


def log(msg):
    if VERBOSE:
        print(f"    {msg}")


def passed(name, detail=""):
    global PASS
    PASS += 1
    RESULTS.append(("PASS", name, detail))
    print(f"  PASS  {name}" + (f" [{detail}]" if detail else ""))


def failed(name, detail=""):
    global FAIL
    FAIL += 1
    RESULTS.append(("FAIL", name, detail))
    print(f"  FAIL  {name}: {detail}")


def warned(name, detail=""):
    global WARN
    WARN += 1
    RESULTS.append(("WARN", name, detail))
    print(f"  WARN  {name}: {detail}")


def fetch_json(base, path, params=None, timeout=30):
    url = f"{base}{path}"
    if params:
        url += "?" + urlencode(params)
    req = Request(url, headers={"User-Agent": "thisminute-deep-test/1.0"})
    resp = urlopen(req, timeout=timeout)
    return json.loads(resp.read().decode())


def safe_run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except (URLError, HTTPError) as e:
        failed(fn.__name__, f"HTTP error: {e}")
    except Exception as e:
        failed(fn.__name__, f"{type(e).__name__}: {e}")
    return None


# ===========================================================================
# 1. DATA QUALITY — things that should never happen
# ===========================================================================

def test_null_island(stories):
    """Stories at (0, 0) indicate geocoding failures."""
    print("\n--- Data Quality ---")
    null_island = []
    for f in stories:
        coords = f["geometry"]["coordinates"]
        if abs(coords[0]) < 0.01 and abs(coords[1]) < 0.01:
            null_island.append(f["properties"]["title"][:60])

    if not null_island:
        passed("no_null_island")
    else:
        failed("no_null_island", f"{len(null_island)} stories at (0,0): {null_island[0]}")


def test_empty_titles(stories):
    """Every story should have a non-empty title."""
    empty = [f["properties"]["id"] for f in stories
             if not f["properties"].get("title", "").strip()]
    if not empty:
        passed("no_empty_titles")
    else:
        failed("no_empty_titles", f"{len(empty)} stories with empty titles")


def test_empty_summaries(stories):
    """RSS stories should have summaries; GDELT stories typically don't."""
    rss_total = rss_missing = gdelt_total = gdelt_missing = 0
    for f in stories:
        p = f["properties"]
        has_summary = bool(p.get("summary", "").strip())
        if p.get("origin") == "rss":
            rss_total += 1
            if not has_summary:
                rss_missing += 1
        else:
            gdelt_total += 1
            if not has_summary:
                gdelt_missing += 1

    # RSS should mostly have summaries
    rss_pct = rss_missing / max(rss_total, 1) * 100
    if rss_pct < 10:
        passed("rss_summaries", f"{rss_total - rss_missing}/{rss_total} RSS have summaries")
    elif rss_pct < 30:
        warned("rss_summaries", f"{rss_missing}/{rss_total} RSS missing ({rss_pct:.0f}%)")
    else:
        failed("rss_summaries", f"{rss_missing}/{rss_total} RSS missing ({rss_pct:.0f}%)")

    # GDELT missing summaries is expected — just report
    gdelt_pct = gdelt_missing / max(gdelt_total, 1) * 100
    passed("gdelt_summaries_noted",
           f"{gdelt_missing}/{gdelt_total} GDELT missing ({gdelt_pct:.0f}%) — expected")


def test_duplicate_stories(stories):
    """Check for duplicate titles (same title within same hour = likely dupe)."""
    title_times = Counter()
    for f in stories:
        p = f["properties"]
        # Normalize: lowercase title + first 13 chars of timestamp (hour precision)
        key = (p.get("title", "").lower().strip(),
               (p.get("published_at") or "")[:13])
        title_times[key] += 1

    dupes = {k: v for k, v in title_times.items() if v > 1 and k[0]}
    dupe_count = sum(v - 1 for v in dupes.values())  # extra copies

    if dupe_count == 0:
        passed("no_duplicate_stories")
    elif dupe_count < 20:
        warned("no_duplicate_stories", f"{dupe_count} potential dupes across {len(dupes)} titles")
    else:
        top = sorted(dupes.items(), key=lambda x: -x[1])[:3]
        examples = "; ".join(f"'{t[:40]}' x{c}" for (t, _), c in top)
        failed("no_duplicate_stories", f"{dupe_count} dupes: {examples}")


def test_coordinate_clustering(stories):
    """Check for extreme coordinate clustering (ignoring country centroids)."""
    coord_counts = Counter()
    for f in stories:
        coords = tuple(round(c, 2) for c in f["geometry"]["coordinates"])
        coord_counts[coords] += 1

    total = len(stories)
    # A single coordinate having >25% of stories would be suspicious
    top_coord, top_count = coord_counts.most_common(1)[0] if coord_counts else ((0, 0), 0)
    top_pct = top_count / max(total, 1) * 100

    if top_pct < 15:
        passed("coordinate_diversity",
               f"top cluster ({top_coord[0]:.1f},{top_coord[1]:.1f}): {top_count} ({top_pct:.0f}%)")
    elif top_pct < 25:
        passed("coordinate_diversity",
               f"top cluster ({top_coord[0]:.1f},{top_coord[1]:.1f}): {top_count} ({top_pct:.0f}%) — country centroid expected")
    else:
        warned("coordinate_diversity",
               f"top cluster has {top_pct:.0f}% of stories — possible geocoding issue")


def test_source_freshness(base, stories):
    """Each active source should have recent stories (last 48h)."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=48)
    source_latest = {}

    for f in stories:
        p = f["properties"]
        source = p.get("source", "unknown")
        scraped = p.get("scraped_at", "")
        try:
            dt = datetime.fromisoformat(scraped.replace("Z", "+00:00"))
            if source not in source_latest or dt > source_latest[source]:
                source_latest[source] = dt
        except (ValueError, TypeError):
            pass

    stale = [s for s, dt in source_latest.items() if dt < cutoff]
    if not stale:
        passed("source_freshness", f"all {len(source_latest)} sources active")
    else:
        warned("source_freshness", f"{len(stale)}/{len(source_latest)} stale (>48h): {', '.join(stale[:5])}")


def test_concepts_populated(stories):
    """Most stories should have at least one concept/topic."""
    no_concepts = sum(1 for f in stories
                      if not f["properties"].get("concepts"))
    total = len(stories)
    pct = no_concepts / max(total, 1) * 100
    if pct < 10:
        passed("concepts_populated", f"{total - no_concepts}/{total} have concepts")
    elif pct < 50:
        warned("concepts_populated", f"{no_concepts}/{total} ({pct:.0f}%) missing concepts")
    else:
        failed("concepts_populated", f"{no_concepts}/{total} ({pct:.0f}%) missing concepts (LLM backfill needed?)")


# ===========================================================================
# 2. EXTRACTION QUALITY — LLM extraction coverage
# ===========================================================================

def test_extraction_coverage(stories):
    """Check what % of stories have LLM extraction fields populated."""
    print("\n--- Extraction Quality ---")
    total = len(stories)
    fields = {
        "severity": 0,
        "primary_action": 0,
        "bright_side_score": 0,
        "is_opinion": 0,
    }

    opinion_count = 0
    for f in stories:
        p = f["properties"]
        if p.get("severity") is not None:
            fields["severity"] += 1
        if p.get("primary_action"):
            fields["primary_action"] += 1
        if p.get("bright_side_score") is not None:
            fields["bright_side_score"] += 1
        if p.get("is_opinion"):
            opinion_count += 1

    for field, count in fields.items():
        pct = count / max(total, 1) * 100
        if field == "is_opinion":
            # Opinion is rare, just check it's not impossible
            passed(f"extraction_{field}", f"{opinion_count}/{total} are opinion")
        elif pct > 50:
            passed(f"extraction_{field}", f"{count}/{total} ({pct:.0f}%)")
        elif pct > 10:
            warned(f"extraction_{field}", f"{count}/{total} ({pct:.0f}%) — backfill in progress?")
        else:
            warned(f"extraction_{field}", f"{count}/{total} ({pct:.0f}%) — needs LLM backfill")


def test_bright_side_distribution(stories):
    """Bright side scores should have a reasonable distribution."""
    raw = [f["properties"]["bright_side_score"]
           for f in stories if f["properties"].get("bright_side_score") is not None]
    scores = [int(s) if isinstance(s, str) else s for s in raw]

    if len(scores) < 10:
        warned("bright_side_distribution", f"only {len(scores)} stories have scores")
        return

    avg = sum(scores) / len(scores)
    high = sum(1 for s in scores if s >= 7)
    medium = sum(1 for s in scores if 4 <= s < 7)
    low = sum(1 for s in scores if s < 4)

    # Distribution should not be all one value
    if high > 0 and low > 0:
        passed("bright_side_distribution",
               f"avg={avg:.1f}, high={high}, med={medium}, low={low} (n={len(scores)})")
    else:
        warned("bright_side_distribution",
               f"skewed: avg={avg:.1f}, high={high}, med={medium}, low={low}")


def test_severity_distribution(stories):
    """Severity values should be 1-5 with reasonable spread."""
    severities = [f["properties"]["severity"]
                  for f in stories if f["properties"].get("severity") is not None]

    if len(severities) < 10:
        warned("severity_distribution", f"only {len(severities)} have severity")
        return

    counts = Counter(severities)
    valid = all(1 <= s <= 5 for s in severities if isinstance(s, (int, float)))
    if not valid:
        failed("severity_distribution", f"values outside 1-5 range: {counts}")
    elif len(counts) >= 3:
        passed("severity_distribution", f"spread across {len(counts)} levels: {dict(counts)}")
    else:
        warned("severity_distribution", f"only {len(counts)} levels used: {dict(counts)}")


# ===========================================================================
# 3. FILTER COMBINATION MATRIX
# ===========================================================================

def test_time_plus_concept(base):
    """Time filter + concept filter should intersect correctly."""
    print("\n--- Filter Combinations ---")
    now = datetime.now(timezone.utc)
    since = (now - timedelta(hours=24)).isoformat()

    # Get all stories in last 24h
    all_recent = fetch_json(base, "/api/stories", {"since": since, "limit": 2000})
    all_count = len(all_recent.get("features", []))

    # Get concept-filtered stories in last 24h
    # Find a concept first
    concepts = fetch_json(base, "/api/topics")
    topics = concepts.get("topics", [])
    if not topics:
        warned("time_plus_concept", "no topics available")
        return

    test_topic = topics[0]["name"]
    filtered = fetch_json(base, "/api/stories",
                          {"since": since, "concepts": test_topic, "limit": 2000})
    filtered_count = len(filtered.get("features", []))

    if filtered_count <= all_count:
        passed("time_plus_concept",
               f"'{test_topic}': {filtered_count}/{all_count} (subset confirmed)")
    else:
        failed("time_plus_concept",
               f"filtered ({filtered_count}) > unfiltered ({all_count})")


def test_search_plus_source(base):
    """Search + source filter should both apply."""
    sources = fetch_json(base, "/api/sources")
    counts = sources.get("counts", [])
    if not counts:
        warned("search_plus_source", "no sources")
        return

    # Pick the biggest source
    top_source = max(counts, key=lambda s: s.get("count", 0))["source"]

    # Search within that source
    data = fetch_json(base, "/api/stories",
                      {"search": "the", "source": top_source, "limit": 100})
    features = data.get("features", [])

    wrong_source = sum(1 for f in features
                       if f["properties"]["source"] != top_source)

    if wrong_source == 0 and len(features) > 0:
        passed("search_plus_source", f"{len(features)} results, all from '{top_source}'")
    elif len(features) == 0:
        warned("search_plus_source", f"no results for 'the' in '{top_source}'")
    else:
        failed("search_plus_source", f"{wrong_source} from wrong source")


def test_concept_exclusion(base):
    """Excluding a concept should reduce results."""
    topics = fetch_json(base, "/api/topics")
    topic_list = topics.get("topics", [])
    if not topic_list:
        warned("concept_exclusion", "no topics")
        return

    # Pick the most common topic
    big_topic = max(topic_list, key=lambda t: t.get("count", 0))

    # Get stories WITH the concept
    with_data = fetch_json(base, "/api/stories",
                           {"concepts": big_topic["name"], "limit": 500})
    with_count = len(with_data.get("features", []))

    # Get stories EXCLUDING the concept
    without_data = fetch_json(base, "/api/stories",
                              {"exclude": big_topic["name"], "limit": 500})
    without_count = len(without_data.get("features", []))

    if with_count > 0 and without_count > 0:
        passed("concept_exclusion",
               f"'{big_topic['name']}': {with_count} with, {without_count} without")
    elif with_count == 0:
        warned("concept_exclusion",
               f"'{big_topic['name']}' matched 0 stories despite count={big_topic.get('count')}")
    else:
        warned("concept_exclusion",
               f"excluding '{big_topic['name']}' left 0 stories")


def test_advanced_search_filters(base):
    """Advanced search with severity filter should work."""
    data = fetch_json(base, "/api/search",
                      {"severity_min": 4, "limit": 50})
    features = data.get("features", [])

    if len(features) > 0:
        low_sev = sum(1 for f in features
                      if (f["properties"].get("severity") or 0) < 4)
        if low_sev == 0:
            passed("search_severity_filter", f"{len(features)} results, all severity >= 4")
        else:
            warned("search_severity_filter",
                   f"{low_sev}/{len(features)} below severity 4")
    else:
        warned("search_severity_filter", "no high-severity stories found")


# ===========================================================================
# 4. FRONTEND CONTRACT — API returns what the frontend expects
# ===========================================================================

FRONTEND_DOMAIN_RULES = [
    {"domain": "violence", "color": "#e74c3c", "keywords": ["war", "conflict", "strike", "attack", "military", "weapon", "bomb", "kill", "death", "shooting", "violence", "terror", "security", "missile", "drone", "naval"]},
    {"domain": "human", "color": "#e67e22", "keywords": ["rights", "refugee", "humanitarian", "abuse", "discrimination", "gender", "immigration", "protest", "justice", "corruption", "crime", "prison", "child"]},
    {"domain": "power", "color": "#3498db", "keywords": ["politic", "election", "government", "trump", "cabinet", "legislation", "congress", "parliament", "democrat", "republican", "diplomatic", "sanction", "tariff", "trade"]},
    {"domain": "economy", "color": "#2ecc71", "keywords": ["econom", "market", "stock", "finance", "business", "oil", "energy", "industry", "labor", "employ", "inflation", "banking", "currency"]},
    {"domain": "planet", "color": "#16a085", "keywords": ["climate", "environment", "weather", "earthquake", "flood", "wildfire", "ocean", "species", "conservation", "pollution", "disaster", "agriculture"]},
    {"domain": "health", "color": "#9b59b6", "keywords": ["health", "medical", "disease", "vaccine", "hospital", "mental", "drug", "cancer", "pandemic", "surgery", "pharma"]},
    {"domain": "tech", "color": "#1abc9c", "keywords": ["ai", "tech", "cyber", "software", "data", "robot", "space", "nasa", "satellite", "internet", "crypto", "blockchain", "quantum"]},
    {"domain": "culture", "color": "#f39c12", "keywords": ["film", "music", "art", "book", "sport", "cricket", "football", "rugby", "olympic", "award", "festival", "entertainment", "media", "celebrity", "cup"]},
    {"domain": "uplifting", "color": "#f1c40f", "keywords": ["rescue", "hero", "discovery", "breakthrough", "donation", "volunteer", "recovery", "milestone", "achievement", "innovation"]},
]


def classify_topic_py(topic):
    """Python port of frontend classifyTopic()."""
    lower = topic.lower()
    for rule in FRONTEND_DOMAIN_RULES:
        for kw in rule["keywords"]:
            if kw in lower:
                return rule["domain"], rule["color"]
    return "general", "#484f58"


def test_topic_domain_classification(base):
    """Every topic from API should classify into a domain matching frontend rules."""
    print("\n--- Frontend Contract ---")
    data = fetch_json(base, "/api/topics")
    topics = data.get("topics", [])

    if not topics:
        warned("topic_domain_classification", "no topics")
        return

    general_count = 0
    classified = 0
    for t in topics:
        domain, _ = classify_topic_py(t["name"])
        if domain == "general":
            general_count += 1
        else:
            classified += 1

    total = len(topics)
    general_pct = general_count / max(total, 1) * 100
    if general_pct < 30:
        passed("topic_domain_classification",
               f"{classified}/{total} classified, {general_count} general ({general_pct:.0f}%)")
    else:
        warned("topic_domain_classification",
               f"{general_count}/{total} ({general_pct:.0f}%) fall to 'general' — consider expanding domain keywords")


def test_preset_coverage(base):
    """Each filter preset should produce at least some results."""
    PRESET_KEYWORDS = {
        "conflict": ["war", "conflict", "strike", "attack", "military", "weapon", "bomb", "kill", "terror", "missile", "drone", "naval", "ceasefire", "shooting"],
        "politics": ["politic", "election", "government", "trump", "cabinet", "legislation", "congress", "parliament", "democrat", "republican", "diplomatic", "sanction", "corruption", "justice"],
        "planet": ["climate", "weather", "disaster", "wildfire", "pollution", "wildlife", "earthquake", "flood", "environment", "ocean", "species", "conservation", "agriculture"],
        "future": ["ai", "tech", "cyber", "space", "nasa", "robot", "science", "quantum", "satellite", "software", "data", "blockchain"],
        "money": ["econom", "market", "stock", "finance", "business", "oil", "energy", "trade", "tariff", "inflation", "banking", "currency", "industry", "labor"],
        "culture": ["sport", "cricket", "football", "rugby", "film", "music", "art", "book", "olympic", "award", "festival", "entertainment", "media", "education", "cup"],
    }

    # Get all topics
    data = fetch_json(base, "/api/topics")
    topics = [t["name"] for t in data.get("topics", [])]

    for preset, keywords in PRESET_KEYWORDS.items():
        # Simulate _matchingConcepts
        matched = set()
        for topic in topics:
            lower = topic.lower()
            for kw in keywords:
                if kw in lower:
                    matched.add(topic)
                    break

        if len(matched) > 0:
            passed(f"preset_{preset}_coverage", f"{len(matched)} matching topics")
        else:
            warned(f"preset_{preset}_coverage", "0 matching topics — preset will show nothing")


def test_feed_panel_stories(stories):
    """Space/Internet feed stories should exist based on location_type or concepts."""
    space_count = 0
    internet_count = 0

    for f in stories:
        p = f["properties"]
        loc_type = p.get("location_type", "terrestrial")
        concepts = p.get("concepts", [])
        concept_names = [c if isinstance(c, str) else c.get("name", "") for c in concepts]
        lower_concepts = [c.lower() for c in concept_names]

        if loc_type == "space" or "space" in lower_concepts:
            space_count += 1
        if loc_type == "internet" or any(c in lower_concepts for c in ["cyber", "internet", "ai"]):
            internet_count += 1

    if space_count > 0:
        passed("feed_space_stories", f"{space_count} space stories")
    else:
        warned("feed_space_stories", "0 space stories (button won't glow)")

    if internet_count > 0:
        passed("feed_internet_stories", f"{internet_count} internet stories")
    else:
        warned("feed_internet_stories", "0 internet stories (button won't glow)")


def test_story_property_types(stories):
    """Verify property types match what the frontend expects."""
    type_errors = []
    for f in stories[:100]:  # Sample
        p = f["properties"]

        # is_opinion should be bool
        if "is_opinion" in p and not isinstance(p["is_opinion"], bool):
            type_errors.append(f"is_opinion={p['is_opinion']!r} (type={type(p['is_opinion']).__name__})")

        # concepts should be a list
        if "concepts" in p and not isinstance(p["concepts"], list):
            type_errors.append(f"concepts is {type(p['concepts']).__name__}")

        # narrative_ids should be a list
        if "narrative_ids" in p and not isinstance(p["narrative_ids"], list):
            type_errors.append(f"narrative_ids is {type(p['narrative_ids']).__name__}")

        # bright_side_score should be int/float or null
        bs = p.get("bright_side_score")
        if bs is not None and not isinstance(bs, (int, float)):
            type_errors.append(f"bright_side_score={bs!r}")

    if not type_errors:
        passed("story_property_types")
    else:
        unique = list(set(type_errors))[:5]
        failed("story_property_types", "; ".join(unique))


# ===========================================================================
# 5. REGRESSION TESTS — previously fixed bugs
# ===========================================================================

def test_regression_narratives_not_empty(base):
    """v58 bug: narratives showed 0 because of race condition."""
    print("\n--- Regression Tests ---")
    data = fetch_json(base, "/api/narratives")
    narratives = data.get("narratives", [])

    # Must have active narratives with stories
    with_stories = [n for n in narratives if n.get("story_count", 0) > 0]
    if len(with_stories) >= 5:
        passed("regression_narratives_populated",
               f"{len(with_stories)} narratives with stories")
    elif len(with_stories) > 0:
        warned("regression_narratives_populated",
               f"only {len(with_stories)} narratives with stories")
    else:
        failed("regression_narratives_populated",
               "0 narratives with stories (race condition regression?)")


def test_regression_bright_side_not_default(base):
    """v58 bug: Bright Side was default, filtering everything for new visitors."""
    # The default API call should not filter by bright_side
    data = fetch_json(base, "/api/stories", {"limit": 100})
    features = data.get("features", [])

    # Should have stories WITHOUT bright_side (not everything filtered)
    has_bs = sum(1 for f in features if f["properties"].get("bright_side_score"))
    no_bs = len(features) - has_bs

    if no_bs > 0:
        passed("regression_no_bright_side_default",
               f"{has_bs} with bright_side, {no_bs} without")
    else:
        if len(features) == 0:
            failed("regression_no_bright_side_default", "0 stories returned")
        else:
            warned("regression_no_bright_side_default",
                   "all stories have bright_side (might be fine post-backfill)")


def test_regression_rss_gdelt_balance(stories):
    """v63 fix: API should return balanced RSS/GDELT, not 99% GDELT."""
    rss = sum(1 for f in stories if f["properties"]["origin"] == "rss")
    gdelt = sum(1 for f in stories if f["properties"]["origin"] == "gdelt")
    total = len(stories)

    if total == 0:
        failed("regression_rss_gdelt_balance", "no stories")
        return

    rss_pct = rss / total * 100
    if 30 <= rss_pct <= 70:
        passed("regression_rss_gdelt_balance",
               f"RSS={rss} ({rss_pct:.0f}%), GDELT={gdelt}")
    else:
        failed("regression_rss_gdelt_balance",
               f"RSS={rss} ({rss_pct:.0f}%), GDELT={gdelt} — imbalanced!")


def test_regression_actors_null(base):
    """Backfill fix: store_extraction crashed on actors: null from LLM."""
    # Verify the API can return event details without crashing
    events = fetch_json(base, "/api/events")
    event_list = events.get("events", [])
    if event_list:
        # Fetch detail — this would crash if actors bug exists
        detail = fetch_json(base, f"/api/events/{event_list[0]['id']}")
        if detail.get("title"):
            passed("regression_actors_null_safe")
        else:
            failed("regression_actors_null_safe", "event detail empty")
    else:
        warned("regression_actors_null_safe", "no events to test")


# ===========================================================================
# 6. CROSS-ENDPOINT DEEP CONSISTENCY
# ===========================================================================

def test_narrative_event_chain(base):
    """Narrative → events → stories chain should be consistent."""
    print("\n--- Deep Consistency ---")
    narratives = fetch_json(base, "/api/narratives")
    narr_list = narratives.get("narratives", [])

    if not narr_list:
        warned("narrative_event_chain", "no narratives")
        return

    # Check first narrative
    n = narr_list[0]
    detail = fetch_json(base, f"/api/narratives/{n['id']}")
    events = detail.get("events", [])
    stories = detail.get("stories", [])

    if events and stories:
        # Story IDs from detail should overlap with narrative's story_ids
        detail_sids = {s["id"] for s in stories}
        list_sids = set(n.get("story_ids", []))

        # Detail stories should be subset of listed IDs (detail may be truncated)
        if detail_sids <= list_sids:
            passed("narrative_event_chain",
                   f"narrative {n['id']}: {len(events)} events, {len(stories)} stories, chain valid")
        else:
            extra = detail_sids - list_sids
            warned("narrative_event_chain",
                   f"{len(extra)} stories in detail not in list story_ids")
    else:
        warned("narrative_event_chain",
               f"narrative {n['id']}: {len(events)} events, {len(stories)} stories")


def test_registry_story_links(base, stories):
    """Registry events referenced in stories should exist in /api/registry."""
    registry_data = fetch_json(base, "/api/registry")
    registry_ids = {r["id"] for r in registry_data.get("registry", [])}

    story_reg_ids = {f["properties"]["registry_event_id"]
                     for f in stories
                     if f["properties"].get("registry_event_id")}

    if not story_reg_ids:
        warned("registry_story_links", "no stories linked to registry events")
        return

    orphans = story_reg_ids - registry_ids
    if not orphans:
        passed("registry_story_links",
               f"all {len(story_reg_ids)} registry refs valid")
    else:
        warned("registry_story_links",
               f"{len(orphans)}/{len(story_reg_ids)} reference non-active registry events")


def test_wiki_event_links(base, stories):
    """Wiki events referenced in stories should be real."""
    wiki_data = fetch_json(base, "/api/wiki-events")
    wiki_titles = {w.get("article_title") for w in wiki_data.get("wiki_events", [])}

    story_wikis = set()
    for f in stories:
        for w in f["properties"].get("wiki_events", []):
            story_wikis.add(w)

    if not story_wikis:
        warned("wiki_event_links", "no stories linked to wiki events")
        return

    orphans = story_wikis - wiki_titles
    if not orphans:
        passed("wiki_event_links",
               f"all {len(story_wikis)} wiki refs valid")
    else:
        warned("wiki_event_links",
               f"{len(orphans)}/{len(story_wikis)} wiki refs not in active list")


def test_world_overview_freshness(base):
    """World overview should be generated recently."""
    data = fetch_json(base, "/api/world-overview")
    gen_at = data.get("generated_at")

    if not gen_at:
        warned("world_overview_freshness", "no generated_at timestamp")
        return

    try:
        dt = datetime.fromisoformat(gen_at.replace("Z", "+00:00"))
        age = datetime.now(timezone.utc) - dt
        hours = age.total_seconds() / 3600

        if hours < 2:
            passed("world_overview_freshness", f"generated {hours:.1f}h ago")
        elif hours < 24:
            warned("world_overview_freshness", f"generated {hours:.0f}h ago")
        else:
            failed("world_overview_freshness", f"generated {hours:.0f}h ago (stale)")
    except (ValueError, TypeError):
        warned("world_overview_freshness", f"can't parse: {gen_at}")


# ===========================================================================
# 7. API ROBUSTNESS — error handling, edge cases, idempotency
# ===========================================================================

def test_invalid_limit(base):
    """Invalid limit values should be handled gracefully."""
    print("\n--- API Robustness ---")
    # Verify the main page loads
    try:
        url = f"{base}/"
        req = Request(url, headers={"User-Agent": "thisminute-deep-test/1.0"})
        resp = urlopen(req, timeout=15)
        html = resp.read().decode()
        checks = ["thisminute", "map-container", "sidebar", "app.js"]
        missing = [c for c in checks if c not in html]
        if not missing:
            passed("homepage_loads", f"{len(html)} bytes, all elements present")
        else:
            failed("homepage_loads", f"missing: {missing}")
    except Exception as e:
        failed("homepage_loads", str(e))

    # Limit=0 should work (FastAPI validation: ge=1 may reject)
    try:
        url = f"{base}/api/stories?limit=0"
        req = Request(url, headers={"User-Agent": "thisminute-deep-test/1.0"})
        resp = urlopen(req, timeout=10)
        code = resp.getcode()
        if code == 422:
            passed("invalid_limit_zero", "422 validation error (correct)")
        else:
            data = json.loads(resp.read().decode())
            passed("invalid_limit_zero", f"returned {len(data.get('features', []))} stories")
    except HTTPError as e:
        if e.code == 422:
            passed("invalid_limit_zero", "422 validation error (correct)")
        else:
            failed("invalid_limit_zero", f"HTTP {e.code}")

    # Negative limit
    try:
        url = f"{base}/api/stories?limit=-1"
        req = Request(url, headers={"User-Agent": "thisminute-deep-test/1.0"})
        resp = urlopen(req, timeout=10)
        passed("invalid_limit_negative", "handled gracefully")
    except HTTPError as e:
        if e.code == 422:
            passed("invalid_limit_negative", "422 validation (correct)")
        else:
            failed("invalid_limit_negative", f"HTTP {e.code}")


def test_empty_search(base):
    """Empty search string should return all stories."""
    data = fetch_json(base, "/api/stories", {"search": "", "limit": 50})
    count = len(data.get("features", []))
    if count > 0:
        passed("empty_search", f"{count} stories (no filtering)")
    else:
        failed("empty_search", "returned 0 stories")


def test_special_chars_search(base):
    """Search with special characters should not crash."""
    special = ["<script>", "'; DROP TABLE", "%%", "null", "undefined"]
    for term in special:
        try:
            data = fetch_json(base, "/api/stories",
                              {"search": term, "limit": 10})
            # Just verify it doesn't crash
        except HTTPError as e:
            if e.code >= 500:
                failed("special_chars_search", f"'{term}' caused HTTP {e.code}")
                return
    passed("special_chars_search", f"all {len(special)} special inputs handled safely")


def test_nonexistent_endpoints(base):
    """Non-existent endpoints should return 404, not 500."""
    try:
        url = f"{base}/api/nonexistent"
        req = Request(url, headers={"User-Agent": "thisminute-deep-test/1.0"})
        resp = urlopen(req, timeout=10)
        warned("nonexistent_endpoint", f"returned {resp.getcode()} instead of 404")
    except HTTPError as e:
        if e.code == 404:
            passed("nonexistent_endpoint", "404 as expected")
        elif e.code >= 500:
            failed("nonexistent_endpoint", f"HTTP {e.code} (server error)")
        else:
            passed("nonexistent_endpoint", f"HTTP {e.code}")


def test_nonexistent_event_detail(base):
    """Requesting a non-existent event ID should not crash."""
    try:
        url = f"{base}/api/events/999999"
        req = Request(url, headers={"User-Agent": "thisminute-deep-test/1.0"})
        resp = urlopen(req, timeout=10)
        data = json.loads(resp.read().decode())
        # Should return empty or error, but not crash
        passed("nonexistent_event", "handled gracefully")
    except HTTPError as e:
        if e.code == 404:
            passed("nonexistent_event", "404 as expected")
        elif e.code >= 500:
            failed("nonexistent_event", f"HTTP {e.code} (server error)")
        else:
            passed("nonexistent_event", f"HTTP {e.code}")


def test_nonexistent_narrative_detail(base):
    """Requesting a non-existent narrative ID should not crash."""
    try:
        url = f"{base}/api/narratives/999999"
        req = Request(url, headers={"User-Agent": "thisminute-deep-test/1.0"})
        resp = urlopen(req, timeout=10)
        passed("nonexistent_narrative", "handled gracefully")
    except HTTPError as e:
        if e.code == 404:
            passed("nonexistent_narrative", "404 as expected")
        elif e.code >= 500:
            failed("nonexistent_narrative", f"HTTP {e.code} (server error)")
        else:
            passed("nonexistent_narrative", f"HTTP {e.code}")


def test_idempotency(base):
    """Same request twice should return same results."""
    data1 = fetch_json(base, "/api/stories", {"limit": 50})
    data2 = fetch_json(base, "/api/stories", {"limit": 50})

    ids1 = [f["properties"]["id"] for f in data1.get("features", [])]
    ids2 = [f["properties"]["id"] for f in data2.get("features", [])]

    if ids1 == ids2:
        passed("idempotency", f"{len(ids1)} stories match exactly")
    else:
        overlap = set(ids1) & set(ids2)
        pct = len(overlap) / max(len(ids1), 1) * 100
        if pct > 90:
            passed("idempotency", f"{pct:.0f}% overlap (minor variance ok)")
        else:
            warned("idempotency", f"only {pct:.0f}% overlap between identical requests")


def test_max_limit(base):
    """Maximum limit (5000) should work without timeout."""
    start = time.time()
    data = fetch_json(base, "/api/stories", {"limit": 5000}, timeout=60)
    elapsed = time.time() - start
    count = len(data.get("features", []))

    if count > 0 and elapsed < 30:
        passed("max_limit", f"{count} stories in {elapsed:.1f}s")
    elif elapsed >= 30:
        warned("max_limit", f"{count} stories in {elapsed:.1f}s (slow)")
    else:
        failed("max_limit", f"0 stories returned")


def test_concurrent_endpoints(base):
    """Multiple endpoint types should all be accessible."""
    endpoints = [
        "/api/health",
        "/api/stories?limit=10",
        "/api/narratives",
        "/api/events",
        "/api/topics",
        "/api/sources",
        "/api/registry",
    ]

    errors = []
    for ep in endpoints:
        try:
            url = f"{base}{ep}"
            req = Request(url, headers={"User-Agent": "thisminute-deep-test/1.0"})
            resp = urlopen(req, timeout=15)
            if resp.getcode() != 200:
                errors.append(f"{ep}: HTTP {resp.getcode()}")
        except Exception as e:
            errors.append(f"{ep}: {e}")

    if not errors:
        passed("all_endpoints_accessible", f"{len(endpoints)} endpoints OK")
    else:
        failed("all_endpoints_accessible", "; ".join(errors))


# ===========================================================================
# 8. UNTESTED ENDPOINTS — categories, stats, actors, wiki-events
# ===========================================================================

def test_categories_endpoint(base):
    """Categories endpoint should return valid color-coded categories."""
    print("\n--- Untested Endpoints ---")
    data = fetch_json(base, "/api/categories")

    if not data:
        warned("categories_endpoint", "empty response")
        return data

    # Should be a dict/list with category info
    if isinstance(data, (dict, list)):
        count = len(data)
        if count > 0:
            passed("categories_endpoint", f"{count} categories")
        else:
            warned("categories_endpoint", "0 categories returned")
    else:
        failed("categories_endpoint", f"unexpected type: {type(data).__name__}")

    return data


def test_stats_endpoint(base):
    """Stats endpoint should return database metrics."""
    data = fetch_json(base, "/api/stats")

    if not data:
        failed("stats_endpoint", "empty response")
        return

    # Should have total stories count
    story_count = data.get("total_stories") or data.get("stories") or data.get("story_count")
    if story_count and story_count > 0:
        passed("stats_total_stories", f"{story_count} total")
    else:
        warned("stats_total_stories", f"keys={list(data.keys())}")

    return data


def test_actors_endpoint(base):
    """Actors endpoint should return browseable actor data."""
    data = fetch_json(base, "/api/actors")

    actors = data if isinstance(data, list) else data.get("actors", [])
    if len(actors) > 0:
        passed("actors_endpoint", f"{len(actors)} actors")
    else:
        warned("actors_endpoint", "0 actors (needs LLM extraction)")

    # Test role filter
    for role in ["perpetrator", "victim", "authority"]:
        try:
            role_data = fetch_json(base, "/api/actors", {"role": role, "limit": 10})
            role_actors = role_data if isinstance(role_data, list) else role_data.get("actors", [])
            if len(role_actors) > 0:
                passed(f"actors_role_{role}", f"{len(role_actors)} actors")
                break  # Just need one role to work
        except Exception:
            pass
    else:
        warned("actors_role_filter", "no role filter returned results")

    return data


def test_wiki_events_endpoint(base):
    """Wiki events endpoint should return article data."""
    data = fetch_json(base, "/api/wiki-events")
    events = data.get("wiki_events", [])

    if len(events) > 0:
        passed("wiki_events_endpoint", f"{len(events)} wiki events")
        # Check required fields
        e = events[0]
        if e.get("article_title"):
            passed("wiki_events_have_titles")
        else:
            failed("wiki_events_have_titles", f"keys: {list(e.keys())}")
    else:
        warned("wiki_events_endpoint", "0 wiki events")

    return data


def test_search_actor_filter(base):
    """Search endpoint actor filters should work."""
    # Try searching by actor role
    data = fetch_json(base, "/api/search", {"actor_role": "authority", "limit": 20})
    features = data.get("features", [])

    if len(features) > 0:
        passed("search_actor_role", f"{len(features)} results for actor_role=authority")
    else:
        warned("search_actor_role", "0 results (may need LLM extraction)")


def test_search_location_type(base):
    """Search endpoint location_type filter should work."""
    for loc_type in ["space", "internet"]:
        data = fetch_json(base, "/api/search",
                          {"location_type": loc_type, "limit": 20})
        features = data.get("features", [])
        if len(features) > 0:
            passed(f"search_location_{loc_type}", f"{len(features)} results")
        else:
            warned(f"search_location_{loc_type}", "0 results")


# ===========================================================================
# 9. ORDERING & PAGINATION — data ordering guarantees
# ===========================================================================

def test_bright_side_globe_viable(stories):
    """Bright side mode needs enough stories with score >= 4 to render on globe."""
    print("\n--- Bright Side Viability ---")
    MIN_SCORE = 4
    qualifying = sum(1 for f in stories
                     if f["properties"].get("bright_side_score") is not None
                     and (int(f["properties"]["bright_side_score"])
                          if isinstance(f["properties"]["bright_side_score"], str)
                          else f["properties"]["bright_side_score"]) >= MIN_SCORE)

    total = len(stories)
    if qualifying >= 20:
        passed("bright_side_globe_viable",
               f"{qualifying}/{total} stories with score >= {MIN_SCORE}")
    elif qualifying > 0:
        warned("bright_side_globe_viable",
               f"only {qualifying}/{total} stories qualify — globe will look sparse")
    else:
        warned("bright_side_globe_viable",
               f"0/{total} stories with score >= {MIN_SCORE} — bright side globe will be EMPTY")


def test_events_have_story_ids(base):
    """Events must include story_ids for frontend filter to work."""
    data = fetch_json(base, "/api/events", {"limit": 5, "min_stories": 2})
    events = data.get("events", [])
    if not events:
        warned("events_have_story_ids", "no events to check")
        return

    missing = sum(1 for e in events if not e.get("story_ids"))
    if missing == 0:
        passed("events_have_story_ids",
               f"all {len(events)} events have story_ids")
    else:
        failed("events_have_story_ids",
               f"{missing}/{len(events)} events missing story_ids — events panel will be empty with filters")


def test_stories_ordering(stories):
    """Stories should be ordered by scraped_at descending."""
    print("\n--- Ordering & Pagination ---")
    timestamps = []
    for f in stories[:100]:  # Check first 100
        scraped = f["properties"].get("scraped_at", "")
        if scraped:
            timestamps.append(scraped)

    if len(timestamps) < 2:
        warned("stories_ordering", "not enough timestamps to verify")
        return

    out_of_order = 0
    for i in range(len(timestamps) - 1):
        if timestamps[i] < timestamps[i + 1]:
            out_of_order += 1

    if out_of_order == 0:
        passed("stories_ordering", f"all {len(timestamps)} in desc order")
    elif out_of_order < len(timestamps) * 0.05:
        passed("stories_ordering", f"{out_of_order} minor ordering gaps (dedup shuffle)")
    else:
        failed("stories_ordering",
               f"{out_of_order}/{len(timestamps)} out of order")


def test_url_validity(stories):
    """Story URLs should look like valid URLs."""
    invalid = 0
    for f in stories[:200]:
        url = f["properties"].get("url", "")
        if not url or not url.startswith("http"):
            invalid += 1

    total = min(len(stories), 200)
    if invalid == 0:
        passed("url_validity", f"all {total} have valid URLs")
    elif invalid < total * 0.05:
        warned("url_validity", f"{invalid}/{total} invalid URLs")
    else:
        failed("url_validity", f"{invalid}/{total} invalid URLs")


def test_story_narrative_bidirectional(base, stories):
    """Stories claiming narrative_ids should actually appear in those narratives."""
    # Find stories that claim to be in narratives
    story_narr_map = {}  # narrative_id -> set of story_ids
    for f in stories[:500]:
        p = f["properties"]
        narr_ids = p.get("narrative_ids", [])
        if narr_ids:
            for nid in narr_ids[:2]:  # Don't check too many
                story_narr_map.setdefault(nid, set()).add(p["id"])

    if not story_narr_map:
        # narrative_ids populated via event_stories→narrative_events join
        # May be empty if stories aren't linked to events yet
        passed("story_narrative_bidir", "no stories in window have narrative links (normal for new stories)")
        return

    # Check up to 3 narratives
    issues = 0
    checked = 0
    for nid, story_ids in list(story_narr_map.items())[:3]:
        try:
            detail = fetch_json(base, f"/api/narratives/{nid}")
            narr_story_ids = set(detail.get("story_ids", []))
            missing = story_ids - narr_story_ids
            if missing:
                issues += 1
                log(f"narrative {nid}: {len(missing)} stories claim membership but not in narrative")
            checked += 1
        except Exception:
            pass

    if checked == 0:
        warned("story_narrative_bidir", "couldn't verify any narratives")
    elif issues == 0:
        passed("story_narrative_bidir", f"checked {checked} narratives, all consistent")
    else:
        warned("story_narrative_bidir", f"{issues}/{checked} have mismatches")


def test_event_title_uniqueness(base):
    """Active events should have unique titles (no duplicates)."""
    data = fetch_json(base, "/api/events", {"limit": 100})
    events = data.get("events", [])

    titles = [e.get("title", "").lower().strip() for e in events]
    title_counts = Counter(titles)
    dupes = {t: c for t, c in title_counts.items() if c > 1 and t}

    if not dupes:
        passed("event_title_uniqueness", f"all {len(events)} events unique")
    else:
        examples = "; ".join(f"'{t[:40]}' x{c}" for t, c in list(dupes.items())[:3])
        warned("event_title_uniqueness", f"{len(dupes)} duplicate titles: {examples}")


def test_stats_consistency(base):
    """Stats should be roughly consistent with actual API data."""
    stats = fetch_json(base, "/api/stats")
    stories = fetch_json(base, "/api/stories", {"limit": 5000})
    api_count = len(stories.get("features", []))

    # Stats total should be >= API stories count (DB has more than window shows)
    total = None
    for key in ["total_stories", "stories", "story_count", "total"]:
        if key in stats:
            total = stats[key]
            break

    if total is not None:
        if total >= api_count:
            passed("stats_consistency", f"stats={total} >= api={api_count}")
        else:
            warned("stats_consistency", f"stats={total} < api={api_count}")
    else:
        warned("stats_consistency", f"couldn't find story count in stats keys: {list(stats.keys())}")


# ===========================================================================
# Main
# ===========================================================================

def run_all(base):
    global PASS, FAIL, WARN, RESULTS
    PASS = FAIL = WARN = 0
    RESULTS = []

    print(f"\n{'='*60}")
    print(f"DEEP TESTS — {base}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    # Fetch the main dataset once
    full_stories = fetch_json(base, "/api/stories", {"limit": 2000})
    features = full_stories.get("features", [])
    print(f"Loaded {len(features)} stories for testing")

    # 1. Data quality
    safe_run(test_null_island, features)
    safe_run(test_empty_titles, features)
    safe_run(test_empty_summaries, features)
    safe_run(test_duplicate_stories, features)
    safe_run(test_coordinate_clustering, features)
    safe_run(test_source_freshness, base, features)
    safe_run(test_concepts_populated, features)

    # 2. Extraction quality
    safe_run(test_extraction_coverage, features)
    safe_run(test_bright_side_distribution, features)
    safe_run(test_severity_distribution, features)

    # 3. Filter combinations
    safe_run(test_time_plus_concept, base)
    safe_run(test_search_plus_source, base)
    safe_run(test_concept_exclusion, base)
    safe_run(test_advanced_search_filters, base)

    # 4. Frontend contract
    safe_run(test_topic_domain_classification, base)
    safe_run(test_preset_coverage, base)
    safe_run(test_feed_panel_stories, features)
    safe_run(test_story_property_types, features)

    # 5. Regression tests
    safe_run(test_regression_narratives_not_empty, base)
    safe_run(test_regression_bright_side_not_default, base)
    safe_run(test_regression_rss_gdelt_balance, features)
    safe_run(test_regression_actors_null, base)

    # 6. Deep consistency
    safe_run(test_narrative_event_chain, base)
    safe_run(test_registry_story_links, base, features)
    safe_run(test_wiki_event_links, base, features)
    safe_run(test_world_overview_freshness, base)

    # 7. API robustness
    safe_run(test_invalid_limit, base)
    safe_run(test_empty_search, base)
    safe_run(test_special_chars_search, base)
    safe_run(test_nonexistent_endpoints, base)
    safe_run(test_nonexistent_event_detail, base)
    safe_run(test_nonexistent_narrative_detail, base)
    safe_run(test_idempotency, base)
    safe_run(test_max_limit, base)
    safe_run(test_concurrent_endpoints, base)

    # 8. Untested endpoints
    safe_run(test_categories_endpoint, base)
    safe_run(test_stats_endpoint, base)
    safe_run(test_actors_endpoint, base)
    safe_run(test_wiki_events_endpoint, base)
    safe_run(test_search_actor_filter, base)
    safe_run(test_search_location_type, base)

    # 9. Bright side & event viability
    safe_run(test_bright_side_globe_viable, features)
    safe_run(test_events_have_story_ids, base)

    # 10. Ordering & pagination
    safe_run(test_stories_ordering, features)
    safe_run(test_url_validity, features)
    safe_run(test_story_narrative_bidirectional, base, features)
    safe_run(test_event_title_uniqueness, base)
    safe_run(test_stats_consistency, base)

    # Summary
    total = PASS + FAIL + WARN
    print(f"\n{'='*60}")
    print(f"RESULTS: {PASS} passed, {FAIL} failed, {WARN} warnings ({total} total)")
    print(f"{'='*60}")

    if FAIL > 0:
        print("\nFAILURES:")
        for status, name, detail in RESULTS:
            if status == "FAIL":
                print(f"  {name}: {detail}")

    if WARN > 0:
        print("\nWARNINGS:")
        for status, name, detail in RESULTS:
            if status == "WARN":
                print(f"  {name}: {detail}")

    return FAIL == 0


def main():
    parser = argparse.ArgumentParser(description="thisminute deep integration tests")
    parser.add_argument("--base-url", default="https://thisminute.org")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    global VERBOSE
    VERBOSE = args.verbose

    success = run_all(args.base_url)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
