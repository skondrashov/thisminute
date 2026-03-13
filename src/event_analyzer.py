"""LLM event analysis with Claude API + template fallback."""

import hashlib
import json
import logging
from datetime import datetime, timezone, timedelta

from .database import (
    get_active_events,
    get_event_stories,
    get_world_overview,
    upsert_world_overview,
)
from .llm_utils import get_anthropic_client, parse_llm_json, parse_json_field, HAIKU_MODEL


def _compute_analysis_hash(conn, event_id: int) -> str:
    """Compute a hash of story IDs for change detection."""
    rows = conn.execute(
        "SELECT story_id FROM event_stories WHERE event_id = ? ORDER BY story_id",
        (event_id,),
    ).fetchall()
    ids_str = ",".join(str(r["story_id"]) for r in rows)
    return hashlib.md5(ids_str.encode()).hexdigest()

logger = logging.getLogger(__name__)

# Max LLM calls per cycle (every 15 min)
MAX_LLM_CALLS_PER_CYCLE = 15

# Events per batch in a single LLM call
EVENTS_PER_BATCH = 4

# Only regenerate world overview if older than 1 hour
WORLD_OVERVIEW_STALENESS_HOURS = 1


def _template_event_title(stories: list[dict]) -> str:
    """Generate event title from stories (no LLM)."""
    if not stories:
        return "Unknown Event"
    # Use the most recent story's title
    return stories[0].get("title", "Unknown Event")


def _template_event_description(stories: list[dict]) -> str:
    """Generate event description from stories (no LLM)."""
    if not stories:
        return ""
    summaries = []
    for s in stories[:5]:
        summary = s.get("summary", "")
        if summary:
            summaries.append(summary[:200])
    return " | ".join(summaries) if summaries else stories[0].get("title", "")


def _template_event_status(event: dict) -> str:
    """Determine event status from story count and timing (no LLM)."""
    count = event.get("story_count", 1)
    if count <= 2:
        return "emerging"
    return "ongoing"


def _template_key_actors(event: dict) -> list[str]:
    """Extract key actors from event data (no LLM)."""
    actors = parse_json_field(event.get("key_actors"))
    # Deduplicate and limit
    seen = set()
    result = []
    for a in actors:
        if a.lower() not in seen:
            seen.add(a.lower())
            result.append(a)
        if len(result) >= 5:
            break
    return result


def _template_world_overview(events: list[dict]) -> str:
    """Generate world overview from top events (no LLM). Structural summary."""
    if not events:
        return "No significant events detected."

    total_stories = sum(e.get("story_count", 0) for e in events)
    locations = [e.get("primary_location") for e in events if e.get("primary_location")]

    parts = [f"Tracking {len(events)} events ({total_stories} stories)."]

    # Top event
    top = events[0]
    if top.get("story_count", 0) >= 3:
        title = top["title"][:60]
        parts.append(f"Top story: {title}.")

    # Most active regions
    if locations:
        from collections import Counter
        top_locs = [loc for loc, _ in Counter(locations).most_common(3)]
        parts.append(f"Most active: {', '.join(top_locs)}.")

    return " ".join(parts)


def _get_event_extraction_summary(conn, event_id: int) -> str:
    """Build a summary of extraction data for stories in an event."""
    rows = conn.execute(
        """SELECT se.topics, se.severity, se.primary_action, se.sentiment
           FROM story_extractions se
           JOIN event_stories es ON se.story_id = es.story_id
           WHERE es.event_id = ?""",
        (event_id,),
    ).fetchall()
    if not rows:
        return ""

    all_topics = []
    severities = []
    actions = []
    sentiments = []
    for r in rows:
        topics = parse_json_field(r["topics"])
        all_topics.extend(topics)
        if r["severity"]:
            severities.append(r["severity"])
        if r["primary_action"]:
            actions.append(r["primary_action"])
        if r["sentiment"]:
            sentiments.append(r["sentiment"])

    from collections import Counter
    top_topics = [t for t, _ in Counter(all_topics).most_common(5)]
    top_actions = [a for a, _ in Counter(actions).most_common(3)]
    avg_severity = round(sum(severities) / len(severities), 1) if severities else None

    parts = []
    if top_topics:
        parts.append(f"Topics: {', '.join(top_topics)}")
    if top_actions:
        parts.append(f"Actions: {', '.join(top_actions)}")
    if avg_severity:
        parts.append(f"Avg severity: {avg_severity}/5")
    return " | ".join(parts)


def _build_event_summary(event: dict, stories: list[dict], conn=None) -> str:
    """Build a concise summary of an event for batch analysis."""
    story_texts = []
    for i, s in enumerate(stories[:5]):
        title = s.get("title", "")
        source = s.get("source", "")
        line = f"  [{source}] {title}"
        # Include summary for first 2 stories to give LLM more context
        if i < 2:
            summary = (s.get("summary") or "")[:150]
            if summary:
                line += f"\n    Summary: {summary}"
        story_texts.append(line)
    stories_str = "\n".join(story_texts)

    extraction_summary = ""
    if conn:
        extraction_summary = _get_event_extraction_summary(conn, event["id"])
    ext_line = f"\n  Extraction: {extraction_summary}" if extraction_summary else ""

    return (
        f"EVENT {event['id']}:\n"
        f"  Current title: {event.get('title', '')[:100]}\n"
        f"  Status: {event.get('status', 'emerging')}, Stories: {event.get('story_count', 0)}{ext_line}\n"
        f"{stories_str}"
    )


EVENT_ANALYSIS_SYSTEM_PROMPT = """You analyze news events for a real-time global news map. Each event is a cluster of related stories.

For each event, return a JSON object containing:
- "event_id": The event ID number
- "title": Concise, informative event title (max 80 chars). Must name a SPECIFIC real-world event. NEVER use vague titles like "Miscellaneous News", "Mixed Updates", "Various Regional Stories", or "Data Quality Issues". Every cluster is about ONE event — name it precisely.
- "description": 2-3 sentence summary
- "status": One of "emerging", "ongoing", "escalating", "de-escalating", "resolved"
- "key_actors": Array of up to 5 key actors

Return ONLY a valid JSON array with one object per event (in the same order). No other text."""


def _llm_analyze_events_batch(client, event_data: list[tuple], conn=None) -> list[dict]:
    """Analyze multiple events in a single LLM call.

    event_data: list of (event, stories) tuples
    Returns: list of dicts with event_id and analysis results
    """
    if not event_data:
        return []

    event_blocks = []
    for event, stories in event_data:
        event_blocks.append(_build_event_summary(event, stories, conn))

    events_input = "\n\n".join(event_blocks)
    if len(events_input) > 7000:
        events_input = events_input[:7000] + "\n..."

    prompt = f"Analyze each of these {len(event_data)} news events:\n\n{events_input}"

    try:
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=250 * len(event_data),
            system=[{
                "type": "text",
                "text": EVENT_ANALYSIS_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        results = parse_llm_json(text, expected_type="list")
        if results is None:
            return []
        return results
    except Exception as e:
        logger.warning("LLM batch event analysis failed: %s", e)
        return []


def _llm_analyze_event(client, stories: list[dict], event: dict, conn=None) -> dict:
    """Analyze a single event (fallback for batch failures)."""
    results = _llm_analyze_events_batch(client, [(event, stories)], conn)
    return results[0] if results else None


def _llm_world_overview(client, events: list[dict]) -> str:
    """Use Claude to generate a world overview."""
    event_summaries = []
    for e in events[:15]:
        desc = (e.get("description") or e.get("title", ""))[:100]
        loc = e.get("primary_location", "")
        loc_str = f" ({loc})" if loc else ""
        count = e.get("story_count", 0)
        event_summaries.append(f"- {e['title']}{loc_str}: {desc} [{count} stories]")

    events_input = "\n".join(event_summaries)

    prompt = f"""Based on these current news events, write a 1-2 sentence overview of what's happening in the world right now. Be factual and extremely concise — this is a status bar, not an article.

Events:
{events_input}

One short paragraph, no bullet points."""

    try:
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.warning("LLM world overview failed: %s", e)
        return None


def analyze_events(conn) -> dict:
    """Main analysis entry point. Enrich events with LLM or templates.

    Prioritizes unanalyzed events with 2+ stories, then checks for
    changes in already-analyzed events.

    Returns stats: {"analyzed": int, "overview_updated": bool}
    """
    client = get_anthropic_client()

    analyzed = 0

    max_events = MAX_LLM_CALLS_PER_CYCLE * EVENTS_PER_BATCH

    # Phase 1: Find unanalyzed events with 2+ stories (highest priority)
    unanalyzed = conn.execute(
        """SELECT * FROM events
           WHERE merged_into IS NULL AND last_analyzed IS NULL
           AND story_count >= 2
           ORDER BY story_count DESC
           LIMIT ?""",
        (max_events,),
    ).fetchall()
    unanalyzed = [dict(r) for r in unanalyzed]

    needs_analysis = [(e, _compute_analysis_hash(conn, e["id"])) for e in unanalyzed]

    # Phase 2: Fill remaining slots with events whose content changed
    remaining_slots = max_events - len(needs_analysis)
    if remaining_slots > 0:
        events = get_active_events(conn, limit=200)
        for event in events:
            if remaining_slots <= 0:
                break
            # Skip ones already in our list
            if any(e["id"] == event["id"] for e, _ in needs_analysis):
                continue
            current_hash = _compute_analysis_hash(conn, event["id"])
            if event.get("analysis_hash") != current_hash:
                needs_analysis.append((event, current_hash))
                remaining_slots -= 1

    to_analyze = needs_analysis[:max_events]

    # Prepare event data (fetch stories for each)
    event_data_with_hash = []
    for event, new_hash in to_analyze:
        stories = get_event_stories(conn, event["id"], limit=15)
        if stories:
            event_data_with_hash.append((event, stories, new_hash))

    # Process in batches
    for batch_start in range(0, len(event_data_with_hash), EVENTS_PER_BATCH):
        batch = event_data_with_hash[batch_start:batch_start + EVENTS_PER_BATCH]

        if client:
            batch_input = [(ev, stories) for ev, stories, _ in batch]
            results = _llm_analyze_events_batch(client, batch_input, conn)
        else:
            results = []

        # Map results by event_id
        result_map = {}
        for r in results:
            eid = r.get("event_id")
            if eid:
                result_map[eid] = r

        for event, stories, new_hash in batch:
            result = result_map.get(event["id"])
            if result:
                title = result.get("title", event["title"])[:200]
                description = result.get("description", "")[:500]
                status = result.get("status", event["status"])
                if status not in ("emerging", "ongoing", "escalating", "de-escalating", "resolved"):
                    status = event["status"]
                # Don't let LLM keep high-story events as "emerging"
                if status == "emerging" and event.get("story_count", 0) >= 3:
                    status = "ongoing"
                key_actors = result.get("key_actors", [])
                if not isinstance(key_actors, list):
                    key_actors = []
            else:
                # Template fallback
                title = _template_event_title(stories)
                description = _template_event_description(stories)
                status = _template_event_status(event)
                key_actors = _template_key_actors(event)

            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """UPDATE events SET
                   title = ?, description = ?, status = ?,
                   key_actors = ?, last_analyzed = ?, analysis_hash = ?
                   WHERE id = ?""",
                (
                    title, description, status,
                    json.dumps(key_actors), now, new_hash,
                    event["id"],
                ),
            )
            conn.commit()
            analyzed += 1

    # World overview
    overview_updated = False
    overview = get_world_overview(conn)
    stale = True
    if overview and overview.get("generated_at"):
        try:
            gen_time = datetime.fromisoformat(overview["generated_at"])
            age_hours = (datetime.now(timezone.utc) - gen_time).total_seconds() / 3600
            stale = age_hours >= WORLD_OVERVIEW_STALENESS_HOURS
        except (ValueError, TypeError):
            pass

    if stale:
        top_events = get_active_events(conn, limit=15)
        if top_events:
            top_event_ids = [e["id"] for e in top_events[:10]]

            if client:
                summary = _llm_world_overview(client, top_events)
            else:
                summary = None

            if not summary:
                summary = _template_world_overview(top_events)

            upsert_world_overview(conn, summary, top_event_ids)
            overview_updated = True

    logger.info("Analysis: %d events analyzed, overview=%s", analyzed, overview_updated)
    return {"analyzed": analyzed, "overview_updated": overview_updated}
