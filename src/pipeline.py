"""Pipeline: scrape -> NER -> geocode -> categorize -> store -> LLM extract -> cluster -> analyze."""

import logging
from datetime import datetime, timezone

from .scraper import scrape_all_feeds
from .gdelt import scrape_gdelt
from .ner import extract_story_location
from .geocoder import geocode_location
from .categorizer import tag_concepts, get_primary_category
from .database import get_connection, init_db, insert_story
from .semantic_clusterer import cluster_new_stories
from .event_analyzer import analyze_events
from .llm_extractor import enrich_stories
from .registry_manager import maintain_registry

logger = logging.getLogger(__name__)


def process_story(story: dict) -> dict:
    """Run NER, geocoding, and categorization on a single story.

    If the story already has location/concept data (e.g. from GDELT GKG),
    skip the redundant extraction steps.
    """
    # Skip NER + geocoding if GDELT already provided lat/lon
    if story.get("lat") is not None and story.get("lon") is not None:
        # Still run NER for ner_entities if not present
        if "ner_entities" not in story:
            _, entities = extract_story_location(story)
            story["ner_entities"] = [{"text": e["text"], "role": e.get("role", "mentioned")} for e in entities]
    else:
        # NER: extract location
        location_name, entities = extract_story_location(story)
        story["location_name"] = location_name
        story["ner_entities"] = [{"text": e["text"], "role": e.get("role", "mentioned")} for e in entities]

        # Geocode the primary location
        if location_name:
            geo = geocode_location(location_name)
            if geo:
                story["lat"] = geo["lat"]
                story["lon"] = geo["lon"]
                story["geocode_confidence"] = geo.get("importance")

    # Concept tagging — skip if already populated (e.g. from GDELT themes)
    if not story.get("concepts"):
        concepts = tag_concepts(story.get("title", ""), story.get("summary", ""))
        story["concepts"] = [c["name"] for c in concepts]
        story["category"] = get_primary_category(concepts)

    return story


def run_pipeline() -> dict:
    """Run the full pipeline: scrape all feeds, process, and store.

    Returns stats dict with counts.
    """
    start = datetime.now(timezone.utc)
    logger.info("Pipeline starting at %s", start.isoformat())

    # Ensure DB is initialized
    init_db()

    # Scrape RSS feeds + GDELT
    raw_stories = scrape_all_feeds()
    try:
        gdelt_stories = scrape_gdelt()
        raw_stories.extend(gdelt_stories)
        logger.info("GDELT added %d stories to pipeline", len(gdelt_stories))
    except Exception as e:
        logger.error("GDELT scrape failed (non-fatal): %s", e)

    # Process each story
    new_count = 0
    geocoded_count = 0
    new_story_ids = []
    conn = get_connection()

    for story in raw_stories:
        try:
            processed = process_story(story)
            was_new = insert_story(conn, processed)
            if was_new:
                new_count += 1
                if processed.get("lat") is not None:
                    geocoded_count += 1
                # Get the inserted story's ID
                row = conn.execute(
                    "SELECT id FROM stories WHERE url = ?", (processed["url"],)
                ).fetchone()
                if row:
                    new_story_ids.append(row["id"])
        except Exception as e:
            logger.error("Error processing story '%s': %s", story.get("title", "?"), e)
            continue

    conn.close()
    logger.info("Scrape+process: %d scraped, %d new, %d geocoded in %.1fs",
                len(raw_stories), new_count, geocoded_count,
                (datetime.now(timezone.utc) - start).total_seconds())

    # LLM extraction, clustering, and analysis
    extraction_count = 0
    backfill_count = 0
    cluster_stats = {"assigned": 0, "new_events": 0, "merged": 0}
    analysis_stats = {"analyzed": 0, "overview_updated": False}
    registry_stats = {"retired": 0, "capped": 0, "merged": 0, "relabeled": 0}

    try:
        conn = get_connection()

        # Extract new stories
        if new_count > 0:
            t0 = datetime.now(timezone.utc)
            extraction_count = enrich_stories(conn, new_story_ids)
            logger.info("LLM extraction: %d new stories enriched in %.1fs",
                        extraction_count, (datetime.now(timezone.utc) - t0).total_seconds())

        # Backfill: process pending stories that were never extracted
        t0 = datetime.now(timezone.utc)
        backfill_count = enrich_stories(conn)
        logger.info("LLM backfill: %d pending stories enriched in %.1fs",
                     backfill_count, (datetime.now(timezone.utc) - t0).total_seconds())

        # Semantic clustering using event signatures
        t0 = datetime.now(timezone.utc)
        cluster_stats = cluster_new_stories(conn)
        logger.info("Clustering done in %.1fs", (datetime.now(timezone.utc) - t0).total_seconds())

        # Event analysis (LLM or template)
        t0 = datetime.now(timezone.utc)
        analysis_stats = analyze_events(conn)
        logger.info("Analysis done in %.1fs", (datetime.now(timezone.utc) - t0).total_seconds())

        # Registry maintenance (retire stale, merge duplicates, refine labels)
        t0 = datetime.now(timezone.utc)
        registry_stats = maintain_registry(conn)
        logger.info("Registry maintenance done in %.1fs", (datetime.now(timezone.utc) - t0).total_seconds())

        conn.close()
    except Exception as e:
        logger.error("Event processing failed: %s", e)

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    stats = {
        "scraped": len(raw_stories),
        "new": new_count,
        "geocoded": geocoded_count,
        "extracted": extraction_count,
        "backfilled": backfill_count,
        "elapsed_seconds": round(elapsed, 1),
        "events": cluster_stats,
        "analysis": analysis_stats,
        "registry": registry_stats,
    }
    logger.info(
        "Pipeline complete: %d scraped, %d new, %d geocoded, %d extracted, %d backfilled in %.1fs | "
        "Events: %d assigned (%d new, %d merged), %d analyzed, overview=%s",
        stats["scraped"], stats["new"], stats["geocoded"], stats["extracted"],
        stats["backfilled"], stats["elapsed_seconds"],
        cluster_stats["assigned"], cluster_stats["new_events"], cluster_stats["merged"],
        analysis_stats["analyzed"], analysis_stats["overview_updated"],
    )
    return stats
