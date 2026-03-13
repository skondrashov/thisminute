"""Production smoke tests for thisminute.org.

Tests API endpoints, data consistency, filter behavior, and cross-endpoint
invariants against the live site. Designed to catch regressions and data
integrity issues.

Usage:
    python tests/smoke_test.py [--base-url URL] [--verbose]

Default base URL: https://thisminute.org
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode

PASS = 0
FAIL = 0
WARN = 0
VERBOSE = False
RESULTS = []


def log(msg):
    if VERBOSE:
        print(f"  {msg}")


def passed(name, detail=""):
    global PASS
    PASS += 1
    RESULTS.append(("PASS", name, detail))
    print(f"  PASS  {name}")


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
    """Fetch JSON from an API endpoint."""
    url = f"{base}{path}"
    if params:
        url += "?" + urlencode(params)
    req = Request(url, headers={"User-Agent": "thisminute-smoke-test/1.0"})
    resp = urlopen(req, timeout=timeout)
    return json.loads(resp.read().decode())


# ---------------------------------------------------------------------------
# 1. API Health & Structure
# ---------------------------------------------------------------------------

def test_health(base):
    print("\n--- API Health & Structure ---")
    data = fetch_json(base, "/api/health")
    if data.get("status") == "ok":
        passed("health_status")
    else:
        failed("health_status", f"got {data.get('status')}")

    count = data.get("stories", 0)
    if count > 1000:
        passed("health_story_count", f"{count} stories")
    else:
        failed("health_story_count", f"only {count} stories")

    return data


def test_stories_structure(base):
    data = fetch_json(base, "/api/stories", {"limit": 100})
    features = data.get("features", [])

    if data.get("type") == "FeatureCollection":
        passed("stories_geojson_type")
    else:
        failed("stories_geojson_type", f"got {data.get('type')}")

    if len(features) >= 90:
        passed("stories_limit_respected", f"got {len(features)}")
    else:
        failed("stories_limit_respected", f"expected ~100, got {len(features)}")

    # Check required fields on each story
    required_props = ["id", "title", "url", "source", "origin", "published_at"]
    missing = set()
    for f in features:
        props = f.get("properties", {})
        for rp in required_props:
            if props.get(rp) is None:
                missing.add(rp)
        coords = f.get("geometry", {}).get("coordinates", [])
        if len(coords) != 2:
            missing.add("coordinates")

    if not missing:
        passed("stories_required_fields")
    else:
        failed("stories_required_fields", f"missing: {missing}")

    # Valid origin values
    origins = {f["properties"]["origin"] for f in features}
    if origins <= {"rss", "gdelt"}:
        passed("stories_valid_origins", str(origins))
    else:
        failed("stories_valid_origins", f"unexpected origins: {origins}")

    # Valid location_type values
    loc_types = {f["properties"].get("location_type") for f in features}
    valid_types = {"terrestrial", "space", "internet", "abstract", None}
    if loc_types <= valid_types:
        passed("stories_valid_location_types", str(loc_types))
    else:
        failed("stories_valid_location_types", f"unexpected: {loc_types - valid_types}")

    return data


def test_clouds_structure(base):
    data = fetch_json(base, "/api/stories/clouds", {"limit": 100})
    features = data.get("features", [])
    if data.get("type") == "FeatureCollection" and len(features) > 0:
        passed("clouds_geojson_structure", f"{len(features)} cloud points")
    else:
        failed("clouds_geojson_structure", f"type={data.get('type')}, features={len(features)}")

    # Cloud points should have story_id
    has_story_id = all(f["properties"].get("story_id") is not None for f in features[:50])
    if has_story_id:
        passed("clouds_have_story_id")
    else:
        failed("clouds_have_story_id")

    return data


def test_narratives_structure(base):
    data = fetch_json(base, "/api/narratives")
    narratives = data.get("narratives", [])

    if len(narratives) > 0:
        passed("narratives_not_empty", f"{len(narratives)} narratives")
    else:
        failed("narratives_not_empty", "0 narratives returned")

    # Check required fields
    if narratives:
        n = narratives[0]
        required = ["id", "title", "status", "story_ids", "story_count"]
        missing = [r for r in required if r not in n]
        if not missing:
            passed("narratives_required_fields")
        else:
            failed("narratives_required_fields", f"missing: {missing}")

        # story_count should match len(story_ids)
        mismatches = []
        for n in narratives:
            if n.get("story_count", 0) != len(n.get("story_ids", [])):
                mismatches.append(n["id"])
        if not mismatches:
            passed("narratives_story_count_matches_ids")
        else:
            warned("narratives_story_count_matches_ids", f"{len(mismatches)} mismatches")

    return data


def test_events_structure(base):
    data = fetch_json(base, "/api/events")
    events = data.get("events", [])

    if len(events) > 0:
        passed("events_not_empty", f"{len(events)} events")
    else:
        warned("events_not_empty", "0 events returned")

    # Each event should have sample_stories, story_ids, and story_count
    if events:
        e = events[0]
        if "sample_stories" in e and "story_count" in e and "story_ids" in e:
            passed("events_have_story_data")
        else:
            missing = [k for k in ["sample_stories", "story_count", "story_ids"] if k not in e]
            failed("events_have_story_data", f"missing: {missing}")

    return data


def test_registry_structure(base):
    data = fetch_json(base, "/api/registry")
    registry = data.get("registry", [])

    if len(registry) > 0:
        passed("registry_not_empty", f"{len(registry)} registry events")
    else:
        warned("registry_not_empty", "0 registry events")

    # Each should have map_label and coordinates
    if registry:
        has_coords = all(
            r.get("primary_lat") is not None and r.get("primary_lon") is not None
            for r in registry
        )
        if has_coords:
            passed("registry_have_coordinates")
        else:
            warned("registry_have_coordinates", "some missing coords")

    return data


def test_sources_structure(base):
    data = fetch_json(base, "/api/sources")

    if "sources" in data and "counts" in data:
        passed("sources_structure", f"{len(data['sources'])} sources")
    else:
        failed("sources_structure", f"keys: {list(data.keys())}")

    return data


def test_concepts_structure(base):
    data = fetch_json(base, "/api/concepts")

    if len(data) > 0:
        total_concepts = sum(len(d.get("concepts", [])) for d in data.values())
        passed("concepts_structure", f"{len(data)} domains, {total_concepts} concepts")
    else:
        failed("concepts_structure", "empty response")

    return data


def test_topics_structure(base):
    data = fetch_json(base, "/api/topics")
    topics = data.get("topics", [])

    if len(topics) > 0:
        passed("topics_not_empty", f"{len(topics)} topics")
    else:
        warned("topics_not_empty", "0 topics (may need LLM backfill)")

    return data


def test_world_overview(base):
    data = fetch_json(base, "/api/world-overview")

    if data.get("summary"):
        passed("world_overview_has_summary", f"{len(data['summary'])} chars")
    else:
        warned("world_overview_has_summary", "no summary text")

    return data


# ---------------------------------------------------------------------------
# 2. Data Consistency
# ---------------------------------------------------------------------------

def test_rss_gdelt_balance(base):
    print("\n--- Data Consistency ---")
    data = fetch_json(base, "/api/stories", {"limit": 2000})
    features = data.get("features", [])

    rss = sum(1 for f in features if f["properties"]["origin"] == "rss")
    gdelt = sum(1 for f in features if f["properties"]["origin"] == "gdelt")
    total = len(features)

    if total == 0:
        failed("rss_gdelt_balance", "no stories")
        return data

    rss_pct = rss / total * 100
    gdelt_pct = gdelt / total * 100

    # Allow 30-70 range for "roughly balanced"
    if 30 <= rss_pct <= 70:
        passed("rss_gdelt_balance", f"RSS={rss} ({rss_pct:.0f}%), GDELT={gdelt} ({gdelt_pct:.0f}%)")
    else:
        warned("rss_gdelt_balance", f"RSS={rss} ({rss_pct:.0f}%), GDELT={gdelt} ({gdelt_pct:.0f}%)")

    return data


def test_narrative_story_refs(base, stories_data, narratives_data):
    """Narrative story_ids should reference actual stories in the DB.

    Narratives span much wider time ranges than the 2000-story API window,
    so we test via the detail endpoint which returns actual story objects.
    """
    narratives = narratives_data.get("narratives", [])
    if not narratives:
        warned("narrative_story_refs", "no narratives")
        return

    # Check a few narratives via detail endpoint
    tested = 0
    issues = 0
    for n in narratives[:3]:
        detail = fetch_json(base, f"/api/narratives/{n['id']}")
        detail_story_ids = {s["id"] for s in detail.get("stories", [])}
        listed_ids = set(n.get("story_ids", []))
        # Detail stories should be a subset of listed story_ids
        if detail_story_ids and not detail_story_ids <= listed_ids:
            extra = detail_story_ids - listed_ids
            issues += 1
            log(f"narrative {n['id']}: {len(extra)} stories in detail not in list")
        tested += 1

    if issues == 0:
        passed("narrative_story_refs", f"checked {tested} narratives")
    else:
        warned("narrative_story_refs", f"{issues}/{tested} have detail/list mismatches")


def test_event_story_refs(base, stories_data, events_data):
    """Event sample_stories should reference actual stories."""
    story_ids = {f["properties"]["id"] for f in stories_data.get("features", [])}
    events = events_data.get("events", [])

    if not events:
        warned("event_story_refs", "no events to check")
        return

    # Check first few events via detail endpoint
    tested = 0
    has_stories = 0
    for e in events[:3]:
        detail = fetch_json(base, f"/api/events/{e['id']}")
        stories = detail.get("stories", [])
        if stories:
            has_stories += 1
        tested += 1

    if has_stories > 0:
        passed("event_story_refs", f"{has_stories}/{tested} events have stories in detail")
    else:
        warned("event_story_refs", f"0/{tested} events have stories in detail")


def test_sources_match_stories(base, stories_data, sources_data):
    """Sources endpoint should list all sources present in stories."""
    story_sources = {f["properties"]["source"] for f in stories_data.get("features", [])}
    api_sources = set(sources_data.get("sources", []))

    # Story sources should be a subset of API sources
    missing = story_sources - api_sources
    if not missing:
        passed("sources_cover_stories")
    else:
        warned("sources_cover_stories", f"story sources not in /api/sources: {missing}")


def test_coordinates_valid(base, stories_data):
    """All story coordinates should be valid lat/lon ranges."""
    features = stories_data.get("features", [])
    invalid = 0
    for f in features:
        coords = f.get("geometry", {}).get("coordinates", [0, 0])
        lon, lat = coords[0], coords[1]
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            invalid += 1

    if invalid == 0:
        passed("coordinates_valid", f"all {len(features)} valid")
    else:
        failed("coordinates_valid", f"{invalid}/{len(features)} out of range")


def test_published_dates_sane(base, stories_data):
    """Published dates should not be in the far future or far past."""
    features = stories_data.get("features", [])
    now = datetime.now(timezone.utc)
    future_cutoff = now + timedelta(days=7)
    past_cutoff = now - timedelta(days=365 * 30)  # 30 years

    future_count = 0
    ancient_count = 0
    no_date = 0
    for f in features:
        pub = f["properties"].get("published_at")
        if not pub:
            no_date += 1
            continue
        try:
            dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            if dt > future_cutoff:
                future_count += 1
            elif dt < past_cutoff:
                ancient_count += 1
        except (ValueError, TypeError):
            pass

    issues = []
    if future_count:
        issues.append(f"{future_count} future")
    if ancient_count:
        issues.append(f"{ancient_count} ancient")
    if no_date:
        issues.append(f"{no_date} missing")

    if not issues:
        passed("published_dates_sane")
    else:
        warned("published_dates_sane", ", ".join(issues))


# ---------------------------------------------------------------------------
# 3. Filter Behavior Tests
# ---------------------------------------------------------------------------

def test_time_filter(base):
    print("\n--- Filter Behavior ---")
    # Fetch with 1-hour time filter via the 'since' param
    now = datetime.now(timezone.utc)
    since = (now - timedelta(hours=1)).isoformat()
    data = fetch_json(base, "/api/stories", {"since": since, "limit": 500})
    features = data.get("features", [])

    if len(features) > 0:
        passed("time_filter_returns_results", f"{len(features)} stories in last hour")
    else:
        warned("time_filter_returns_results", "0 stories in last hour (pipeline may be slow)")

    # All returned stories should have scraped_at after `since`
    cutoff = now - timedelta(hours=2)  # generous buffer
    old_count = 0
    for f in features:
        scraped = f["properties"].get("scraped_at", "")
        try:
            dt = datetime.fromisoformat(scraped.replace("Z", "+00:00"))
            if dt < cutoff:
                old_count += 1
        except (ValueError, TypeError):
            pass

    if old_count == 0:
        passed("time_filter_correctness")
    else:
        failed("time_filter_correctness", f"{old_count} stories older than 2h buffer")


def test_search_filter(base):
    """Search filter should return only matching stories."""
    data = fetch_json(base, "/api/stories", {"search": "president", "limit": 100})
    features = data.get("features", [])

    if len(features) > 0:
        # Every story should contain 'president' in title or summary
        misses = 0
        for f in features:
            p = f["properties"]
            text = f"{p.get('title', '')} {p.get('summary', '')}".lower()
            if "president" not in text:
                misses += 1

        if misses == 0:
            passed("search_filter_correctness", f"{len(features)} results all match")
        else:
            failed("search_filter_correctness", f"{misses}/{len(features)} don't contain 'president'")
    else:
        warned("search_filter_no_results", "no results for 'president'")


def test_source_filter(base, sources_data):
    """Filtering by a specific source should return only that source."""
    counts = sources_data.get("counts", [])
    if not counts:
        warned("source_filter", "no sources to test")
        return

    # Pick the source with the most stories
    test_source = max(counts, key=lambda s: s.get("count", 0))["source"]
    data = fetch_json(base, "/api/stories", {"source": test_source, "limit": 100})
    features = data.get("features", [])

    if len(features) > 0:
        wrong = sum(1 for f in features if f["properties"]["source"] != test_source)
        if wrong == 0:
            passed("source_filter_correctness", f"all {len(features)} from '{test_source}'")
        else:
            failed("source_filter_correctness", f"{wrong}/{len(features)} from wrong source")
    else:
        warned("source_filter_no_results", f"no results for source '{test_source}'")


def test_limit_parameter(base):
    """Limit parameter should be respected (±small dedup variance)."""
    for limit in [10, 50]:
        data = fetch_json(base, "/api/stories", {"limit": limit})
        got = len(data.get("features", []))
        if got == limit:
            passed(f"limit_{limit}_respected")
        elif got >= limit * 0.9:
            # Dedup can remove a few cross-origin duplicate titles
            passed(f"limit_{limit}_respected", f"got {got} (minor dedup variance)")
        else:
            failed(f"limit_{limit}_respected", f"expected ~{limit}, got {got}")


def test_concept_filter(base, concepts_data):
    """Concept filter should return only stories with matching concepts."""
    # Find a concept with stories
    test_concept = None
    for domain, info in concepts_data.items():
        for c in info.get("concepts", []):
            if c.get("count", 0) > 5:
                test_concept = c["name"]
                break
        if test_concept:
            break

    if not test_concept:
        warned("concept_filter", "no concept with enough stories to test")
        return

    data = fetch_json(base, "/api/stories", {"concepts": test_concept, "limit": 50})
    features = data.get("features", [])

    if len(features) > 0:
        misses = 0
        for f in features:
            concepts = f["properties"].get("concepts", [])
            concept_names = [c if isinstance(c, str) else c.get("name", "") for c in concepts]
            if not any(test_concept.lower() in cn.lower() for cn in concept_names):
                misses += 1

        if misses == 0:
            passed("concept_filter_correctness", f"all {len(features)} match '{test_concept}'")
        elif misses < len(features) * 0.1:
            warned("concept_filter_correctness", f"{misses}/{len(features)} don't match '{test_concept}' (may be domain match)")
        else:
            failed("concept_filter_correctness", f"{misses}/{len(features)} don't contain '{test_concept}'")
    else:
        warned("concept_filter_no_results", f"no results for concept '{test_concept}'")


# ---------------------------------------------------------------------------
# 4. Cross-Endpoint Consistency
# ---------------------------------------------------------------------------

def test_narrative_detail_consistency(base, narratives_data):
    print("\n--- Cross-Endpoint Consistency ---")
    narratives = narratives_data.get("narratives", [])
    if not narratives:
        warned("narrative_detail", "no narratives to test")
        return

    # Test detail endpoint for first narrative
    n = narratives[0]
    detail = fetch_json(base, f"/api/narratives/{n['id']}")

    if detail.get("title") == n.get("title"):
        passed("narrative_detail_matches_list")
    else:
        failed("narrative_detail_matches_list",
               f"list='{n.get('title')[:50]}' vs detail='{detail.get('title', '')[:50]}'")

    # Detail should include stories array
    stories = detail.get("stories", [])
    if len(stories) > 0:
        passed("narrative_detail_has_stories", f"{len(stories)} stories")
    else:
        warned("narrative_detail_has_stories", "0 stories in detail view")


def test_event_detail_consistency(base, events_data):
    events = events_data.get("events", [])
    if not events:
        warned("event_detail", "no events to test")
        return

    e = events[0]
    detail = fetch_json(base, f"/api/events/{e['id']}")

    if detail.get("title") == e.get("title"):
        passed("event_detail_matches_list")
    else:
        failed("event_detail_matches_list",
               f"list='{e.get('title', '')[:50]}' vs detail='{detail.get('title', '')[:50]}'")

    stories = detail.get("stories", [])
    if len(stories) > 0:
        passed("event_detail_has_stories", f"{len(stories)} stories")
    else:
        warned("event_detail_has_stories", "0 stories in detail view")


def test_clouds_match_stories(base, stories_data):
    """Cloud story_ids should be a subset of stories in the API."""
    clouds = fetch_json(base, "/api/stories/clouds", {"limit": 500})
    story_ids = {f["properties"]["id"] for f in stories_data.get("features", [])}
    cloud_sids = {f["properties"]["story_id"] for f in clouds.get("features", [])}

    orphans = cloud_sids - story_ids
    if not orphans:
        passed("clouds_stories_subset", f"{len(cloud_sids)} cloud stories all valid")
    else:
        # Clouds use same limit logic so some mismatch expected
        pct = len(orphans) / max(len(cloud_sids), 1) * 100
        if pct < 20:
            warned("clouds_stories_subset", f"{len(orphans)} cloud stories outside API window")
        else:
            failed("clouds_stories_subset", f"{len(orphans)}/{len(cloud_sids)} orphaned")


def test_bright_side_fields(base, stories_data):
    """Stories with bright_side_score should also have category and headline."""
    features = stories_data.get("features", [])
    has_score = 0
    missing_fields = 0

    for f in features:
        p = f["properties"]
        if p.get("bright_side_score") is not None:
            has_score += 1
            if not p.get("bright_side_category") or not p.get("bright_side_headline"):
                missing_fields += 1

    if has_score == 0:
        warned("bright_side_completeness", "no stories have bright_side_score (backfill needed?)")
    elif missing_fields == 0:
        passed("bright_side_completeness", f"{has_score} stories have complete bright_side data")
    else:
        failed("bright_side_completeness", f"{missing_fields}/{has_score} missing category/headline")


def test_advanced_search(base):
    """Advanced search endpoint should return valid GeoJSON."""
    data = fetch_json(base, "/api/search", {"search": "war", "limit": 20})

    if data.get("type") == "FeatureCollection":
        features = data.get("features", [])
        if len(features) > 0:
            passed("advanced_search", f"{len(features)} results for 'war'")
        else:
            warned("advanced_search", "no results for 'war'")
    else:
        failed("advanced_search", f"unexpected type: {data.get('type')}")


def test_trending(base):
    """Trending endpoint should return valid structure."""
    data = fetch_json(base, "/api/trending")
    trending = data.get("trending", [])
    recent = data.get("recent_stories", 0)

    if recent > 0:
        passed("trending_has_data", f"{len(trending)} trending, {recent} recent")
    else:
        warned("trending_has_data", f"0 recent stories (pipeline may be down)")

    # Trending items should have spike > 1
    if trending:
        low_spike = [t for t in trending if t.get("spike", 0) < 1]
        if not low_spike:
            passed("trending_spike_values")
        else:
            warned("trending_spike_values", f"{len(low_spike)} items with spike < 1")


def test_cache_version_consistency(base):
    """CSS and JS cache busters should match."""
    url = f"{base}/"
    req = Request(url, headers={"User-Agent": "thisminute-smoke-test/1.0"})
    resp = urlopen(req, timeout=15)
    html = resp.read().decode()

    import re
    versions = re.findall(r'\?v=(\d+)', html)
    unique = set(versions)

    if len(unique) == 1:
        passed("cache_version_consistency", f"all assets at v{versions[0]}")
    elif len(unique) == 0:
        warned("cache_version_consistency", "no cache busters found")
    else:
        failed("cache_version_consistency", f"mixed versions: {unique}")


def test_stats_endpoint(base):
    """Stats endpoint should return valid metrics."""
    data = fetch_json(base, "/api/stats")
    if data and isinstance(data, dict) and len(data) > 0:
        passed("stats_structure", f"{len(data)} keys")
    else:
        failed("stats_structure", f"empty or invalid: {type(data).__name__}")


def test_actors_endpoint(base):
    """Actors endpoint should return data without crashing."""
    data = fetch_json(base, "/api/actors", {"limit": 10})
    actors = data if isinstance(data, list) else data.get("actors", [])
    if len(actors) > 0:
        passed("actors_structure", f"{len(actors)} actors")
    else:
        warned("actors_structure", "0 actors (needs LLM extraction)")


def test_wiki_events_endpoint(base):
    """Wiki events endpoint should return data."""
    data = fetch_json(base, "/api/wiki-events")
    events = data.get("wiki_events", [])
    if len(events) > 0:
        passed("wiki_events_structure", f"{len(events)} wiki events")
    else:
        warned("wiki_events_structure", "0 wiki events")


# ---------------------------------------------------------------------------
# 5. Performance / Latency Tests
# ---------------------------------------------------------------------------

def test_response_times(base):
    print("\n--- Performance ---")
    endpoints = [
        ("/api/health", {}),
        ("/api/stories", {"limit": 100}),
        ("/api/narratives", {}),
        ("/api/events", {}),
        ("/api/registry", {}),
    ]

    for path, params in endpoints:
        start = time.time()
        try:
            fetch_json(base, path, params, timeout=15)
            elapsed = time.time() - start
            name = path.split("/")[-1]
            if elapsed < 5:
                passed(f"latency_{name}", f"{elapsed:.1f}s")
            elif elapsed < 10:
                warned(f"latency_{name}", f"{elapsed:.1f}s (slow)")
            else:
                failed(f"latency_{name}", f"{elapsed:.1f}s (very slow)")
        except Exception as e:
            failed(f"latency_{path}", str(e))


def test_stories_2000_latency(base):
    """The main stories endpoint at full limit should respond in time."""
    start = time.time()
    data = fetch_json(base, "/api/stories", {"limit": 2000}, timeout=30)
    elapsed = time.time() - start
    count = len(data.get("features", []))

    if elapsed < 10:
        passed("stories_2000_latency", f"{count} stories in {elapsed:.1f}s")
    elif elapsed < 20:
        warned("stories_2000_latency", f"{count} stories in {elapsed:.1f}s")
    else:
        failed("stories_2000_latency", f"{count} stories in {elapsed:.1f}s")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_all(base):
    global PASS, FAIL, WARN, RESULTS
    PASS = FAIL = WARN = 0
    RESULTS = []

    print(f"\n{'='*60}")
    print(f"SMOKE TESTS — {base}")
    print(f"{'='*60}")

    def safe_run(fn, *args, **kwargs):
        """Run a test function, catching and reporting any exceptions."""
        try:
            return fn(*args, **kwargs)
        except (URLError, HTTPError) as e:
            failed(fn.__name__, f"HTTP error: {e}")
        except Exception as e:
            failed(fn.__name__, f"{type(e).__name__}: {e}")
        return None

    # 1. Structure tests
    health = safe_run(test_health, base)
    stories = safe_run(test_stories_structure, base)
    clouds = safe_run(test_clouds_structure, base)
    narratives = safe_run(test_narratives_structure, base) or {"narratives": []}
    events = safe_run(test_events_structure, base) or {"events": []}
    registry = safe_run(test_registry_structure, base)
    sources = safe_run(test_sources_structure, base) or {"sources": [], "counts": []}
    concepts = safe_run(test_concepts_structure, base) or {}
    topics = safe_run(test_topics_structure, base)
    overview = safe_run(test_world_overview, base)

    # 2. Data consistency (need full story set)
    full_stories = fetch_json(base, "/api/stories", {"limit": 2000})
    safe_run(test_rss_gdelt_balance, base)
    safe_run(test_narrative_story_refs, base, full_stories, narratives)
    safe_run(test_event_story_refs, base, full_stories, events)
    safe_run(test_sources_match_stories, base, full_stories, sources)
    safe_run(test_coordinates_valid, base, full_stories)
    safe_run(test_published_dates_sane, base, full_stories)
    safe_run(test_bright_side_fields, base, full_stories)

    # 3. Filter tests
    safe_run(test_time_filter, base)
    safe_run(test_search_filter, base)
    safe_run(test_source_filter, base, sources)
    safe_run(test_limit_parameter, base)
    safe_run(test_concept_filter, base, concepts)

    # 4. Cross-endpoint consistency
    safe_run(test_narrative_detail_consistency, base, narratives)
    safe_run(test_event_detail_consistency, base, events)
    safe_run(test_clouds_match_stories, base, full_stories)
    safe_run(test_advanced_search, base)
    safe_run(test_trending, base)
    safe_run(test_cache_version_consistency, base)
    safe_run(test_stats_endpoint, base)
    safe_run(test_actors_endpoint, base)
    safe_run(test_wiki_events_endpoint, base)

    # 5. Performance
    safe_run(test_response_times, base)
    safe_run(test_stories_2000_latency, base)

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
    parser = argparse.ArgumentParser(description="thisminute production smoke tests")
    parser.add_argument("--base-url", default="https://thisminute.org",
                        help="Base URL to test (default: https://thisminute.org)")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--loop", type=int, default=0,
                        help="Run continuously every N minutes (0 = once)")
    args = parser.parse_args()

    global VERBOSE
    VERBOSE = args.verbose

    if args.loop > 0:
        while True:
            success = run_all(args.base_url)
            print(f"\nNext run in {args.loop} minutes...")
            time.sleep(args.loop * 60)
    else:
        success = run_all(args.base_url)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
