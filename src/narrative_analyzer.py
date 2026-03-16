"""Narrative analysis: identify long-running themes spanning multiple events.

Uses Claude Sonnet for higher-quality abstract reasoning.
Runs on a separate schedule (every 1-2 hours, not every 15 min).
Supports domain-specific analysis: news, sports, entertainment, positive.
"""

import json
import logging
from datetime import datetime, timezone

from .config import FEED_TAG_MAP
from .database import upsert_narrative
from .llm_utils import get_anthropic_client, parse_llm_json, SONNET_MODEL

logger = logging.getLogger(__name__)

ANALYSIS_INTERVAL_HOURS = 1  # minimum hours between analyses

# Per-domain narrative caps
DOMAIN_MAX_NARRATIVES = {
    "news": 20,
    "sports": 10,
    "entertainment": 10,
    "positive": 10,
    "curious": 10,
    "science": 8,
    "business": 8,
    "health": 6,
}

# Which feed tags map to which domain
DOMAIN_FEED_TAGS = {
    "news": {"news"},
    "sports": {"sports"},
    "entertainment": {"entertainment"},
    "positive": None,  # positive uses all events, filtered by bright_side_score
    "curious": None,   # curious uses all events, filtered by human_interest_score
    "science": {"science", "tech"},
    "business": {"business"},
    "health": {"health"},
}

# Source-ratio thresholds per domain.  Sports events are dominated by
# sports-only sources so 0.5 works fine.  Entertainment events get heavy
# cross-coverage from general news outlets (BBC, CNN, NYT all cover the
# Oscars), so the entertainment threshold must be much lower.
# News uses the default (0.5).
DOMAIN_SOURCE_RATIO = {
    "news": 0.5,
    "sports": 0.5,
    "entertainment": 0.15,
    "science": 0.3,
    "business": 0.3,
    "health": 0.3,
}

# Topic slugs that act as a secondary signal for entertainment events.
# If an event's LLM-extracted topics contain any of these, it qualifies
# for the entertainment domain even if its source ratio is below threshold.
_ENTERTAINMENT_TOPIC_SIGNALS = {
    "film", "movie", "movies", "cinema", "oscars", "academy-awards",
    "grammy", "grammys", "emmy", "emmys", "tony", "tonys", "golden-globes",
    "bafta", "cannes", "sundance", "sxsw", "tiff", "venice-film",
    "box-office", "streaming", "netflix", "disney", "hbo", "amazon-prime",
    "k-pop", "kpop", "k-drama", "bollywood", "hollywood", "broadway",
    "music", "album", "concert", "tour", "festival", "celebrity",
    "tv-show", "television", "series", "reality-tv", "entertainment",
    "comic-con", "anime", "manga", "gaming", "video-games",
    "marvel", "dc-comics", "star-wars", "franchise",
    "billboard", "charts", "record-label", "awards",
}

_SCIENCE_TOPIC_SIGNALS = {
    "space", "nasa", "esa", "spacex", "rocket", "satellite", "asteroid",
    "mars", "moon", "jupiter", "exoplanet", "telescope", "jwst", "hubble",
    "quantum", "physics", "chemistry", "biology", "genetics", "crispr",
    "climate-change", "climate", "fossil", "evolution", "archaeology",
    "neuroscience", "brain", "dna", "genome", "stem-cells",
    "ai", "artificial-intelligence", "machine-learning", "deep-learning",
    "cybersecurity", "cyber", "hacking", "data-breach",
    "robotics", "autonomous", "semiconductor", "chip",
    "renewable-energy", "solar", "nuclear-fusion", "battery",
    "research", "discovery", "experiment", "study",
}

_BUSINESS_TOPIC_SIGNALS = {
    "stocks", "stock-market", "wall-street", "nasdaq", "dow-jones", "s&p-500",
    "fed", "federal-reserve", "interest-rates", "inflation", "recession",
    "gdp", "trade", "tariffs", "sanctions", "trade-war",
    "oil", "oil-prices", "opec", "commodities", "gold",
    "crypto", "bitcoin", "cryptocurrency", "blockchain",
    "ipo", "merger", "acquisition", "earnings", "revenue",
    "layoffs", "hiring", "unemployment", "jobs-report",
    "real-estate", "housing", "mortgage",
    "banking", "finance", "fintech", "venture-capital",
}

_HEALTH_TOPIC_SIGNALS = {
    "covid", "pandemic", "epidemic", "outbreak", "virus", "vaccine",
    "who", "cdc", "disease", "infection", "pathogen",
    "cancer", "diabetes", "heart-disease", "alzheimers", "dementia",
    "mental-health", "depression", "anxiety", "suicide",
    "drug", "pharmaceutical", "fda", "clinical-trial",
    "hospital", "healthcare", "nhs", "public-health",
    "antimicrobial-resistance", "antibiotic", "bird-flu", "h5n1", "mpox",
}

# Domain-specific prompt preambles
DOMAIN_PROMPTS = {
    "news": {
        "intro": 'You are grouping current news events into SITUATIONS — concrete, real-world developments that a reader would recognize as "one big thing."',
        "examples_good": '"2026 Iran war", "Trump tariff escalation", "UK NHS crisis", "California wildfire season 2026"',
        "examples_bad": '"Global energy market disruption" (too abstract), "Middle East tensions" (too vague), "Political developments" (meaningless)',
        "guidance": 'Think: would this be a Wikipedia article title? Would a person say "did you hear about the ___"?',
    },
    "sports": {
        "intro": 'You are grouping current sports events into SITUATIONS — ongoing sports stories that a fan would follow as "one big thing."',
        "examples_good": '"2026 IPL Season", "NFL Free Agency 2026", "FIFA World Cup Qualifying", "NBA Playoffs 2026", "Premier League Title Race", "Tiger Woods Comeback"',
        "examples_bad": '"Sports developments" (meaningless), "Global athletics" (too vague), "Team performance" (too abstract), "Cricket" with rugby/football events inside (cross-sport contamination)',
        "guidance": 'A situation is a tournament, a season, a transfer saga, a rivalry series, a record chase, or a scandal. Think: would a sports fan say "are you following the ___"? NEVER create catch-all buckets like "Global Sports Highlights" or "Champions & Record-Breakers." Every situation must be a SPECIFIC story.\n\nCRITICAL — ONE SPORT PER SITUATION: Each situation MUST contain events from only ONE sport or ONE specific competition/league. NEVER mix sports. A cricket situation must ONLY contain cricket events. A football situation must ONLY contain football events. "2026 Six Nations Rugby" is rugby — it does NOT belong in a cricket situation. "FIFA World Cup" is football — it does NOT belong in a tennis or cricket situation. If you have cricket events and rugby events, those are SEPARATE situations, even if they are happening at the same time. A situation titled "2026 IPL Season" should contain ZERO rugby, football, tennis, motorsport, or MMA events. When in doubt, check the event title — if it names a different sport, it belongs in a different situation.',
    },
    "entertainment": {
        "intro": 'You are grouping current entertainment events into SITUATIONS — ongoing entertainment stories that a fan would follow as "one big thing."',
        "examples_good": '"Oscar Season 2026", "Marvel Phase 7 Rollout", "K-pop Group Disbandment Wave", "Beyoncé World Tour 2026", "Netflix Password Crackdown Fallout"',
        "examples_bad": '"Entertainment news" (meaningless), "Celebrity activity" (too vague), "Film industry developments" (too abstract)',
        "guidance": 'A situation is an awards season, a franchise rollout, a celebrity scandal arc, a music tour, or a streaming wars development. Think: would someone say "did you see the latest on ___"?',
    },
    "positive": {
        "intro": 'You are grouping events into POSITIVE SITUATIONS — inherently uplifting, inspiring developments that would make someone\'s day better.',
        "examples_good": '"Renewable Energy Milestone 2026", "Great Barrier Reef Recovery", "Global Poverty Decline Report", "Community Garden Movement", "Space Telescope Discovery"',
        "examples_bad": '"The Iran war" (even if some stories are positive, war is not a positive situation), "Bright side of economic crisis" (the crisis itself is not positive), "Record-Breaking Sports Moments" (vague thematic bucket), "Women\'s Empowerment Worldwide" (too broad — name the SPECIFIC campaign, law, or milestone)',
        "guidance": 'A positive situation is something you\'d tell a friend about to make their day better. "Progress on Middle East peace talks" qualifies. "The Iran war" does not, even if some stories within it are positive. Exclude "the bright side of a fundamentally negative situation." NEVER create thematic buckets that group unrelated stories by vibes. "Medical Breakthroughs" is too vague — "mRNA Malaria Vaccine Trial Success" is specific. If stories don\'t share a CONCRETE connection, they are separate situations, not one bucket.',
    },
    "curious": {
        "intro": 'You are grouping events into CURIOUS SITUATIONS — fascinating, engaging, "you won\'t believe this" stories that capture human curiosity. These are the stories people share because they\'re remarkable, bizarre, heartwarming, or mind-bending — NOT because they\'re politically important.',
        "examples_good": '"New Deep-Sea Species Discovered 2026", "Small Town Viral Moments", "Backyard Archaeology Finds", "AI Art Controversy", "Record-Breaking Human Feats 2026", "Weird Weather Phenomena", "Animal Heroes & Oddities"',
        "examples_bad": '"Interesting news" (meaningless), "Human interest stories" (too vague), "Viral content" (too broad), "Miscellaneous curiosities" (catch-all bucket), "Good news roundup" (that\'s positive, not curious)',
        "guidance": 'A curious situation is something that makes people say "wait, really?" or "you have to see this." Think viral stories, quirky science, unusual discoveries, local heroes doing remarkable things, animal stories, odd coincidences, record-breaking feats, and unexpected events. "Dog Elected Mayor of Small Town" qualifies. "Senate Passes Budget" does not. This is NOT the same as positive — a gripping true crime investigation or a bizarre natural disaster can be highly curious without being positive. And a routine charity donation is positive but not curious. Focus on stories with high engagement/shareability factor. NEVER create thematic buckets — each situation must be about ONE specific story or connected set of events.',
    },
    "science": {
        "intro": 'You are grouping current science and technology events into SITUATIONS — ongoing research breakthroughs, space missions, tech industry developments, and scientific discoveries that a curious reader would follow.',
        "examples_good": '"James Webb Telescope Deep Field 2026", "CRISPR Gene Therapy Trials", "OpenAI GPT-5 Rollout", "Mars Sample Return Mission", "Quantum Computing Breakthrough Race", "mRNA Cancer Vaccine Trials"',
        "examples_bad": '"Science news" (meaningless), "Tech developments" (too vague), "Innovation" (too abstract), "AI advances" (too broad — name the specific product, company, or breakthrough)',
        "guidance": 'A situation is a specific research program, space mission, product launch cycle, regulatory battle, or discovery arc. "LIGO Detects New Gravitational Wave Source" qualifies. "Science is advancing" does not. Keep science and tech situations separate when they are unrelated — a climate study and an AI model release are different situations. NEVER group unrelated discoveries into thematic buckets.',
    },
    "business": {
        "intro": 'You are grouping current business and financial events into SITUATIONS — market movements, trade policy developments, corporate stories, and economic trends that someone following the markets would track.',
        "examples_good": '"US-China Tariff Escalation 2026", "Fed Interest Rate Decision Cycle", "Tesla Stock Volatility", "Oil Price Surge from Hormuz Disruption", "Tech Layoffs Wave Q1 2026", "Crypto Regulation Push"',
        "examples_bad": '"Market movements" (meaningless), "Economic developments" (too vague), "Business news" (too abstract), "Global economy" (not a situation)',
        "guidance": 'A situation is a specific market event, trade dispute, corporate saga, economic policy shift, or sector trend. "Boeing 737 MAX Production Crisis" qualifies. "Stocks went up" does not. Wars and geopolitics ONLY belong here if the situation is specifically about their MARKET IMPACT — "Oil Price Surge from Iran War" is a business situation, but "Iran War" itself is not. NEVER create catch-all buckets.',
    },
    "health": {
        "intro": 'You are grouping current health and medical events into SITUATIONS — disease outbreaks, public health campaigns, medical breakthroughs, and health policy developments that someone following global health would track.',
        "examples_good": '"H5N1 Bird Flu Outbreak 2026", "WHO Mpox Emergency Response", "mRNA Malaria Vaccine Trial", "US Healthcare Policy Overhaul", "Antimicrobial Resistance Crisis", "Long COVID Research Findings"',
        "examples_bad": '"Health news" (meaningless), "Medical developments" (too vague), "Disease concerns" (too abstract), "Public health" (not a situation)',
        "guidance": 'A situation is a specific outbreak, clinical trial, health policy battle, or medical milestone. "Measles Resurgence in Unvaccinated Communities" qualifies. "People are getting sick" does not. Focus on stories from WHO, health agencies, and medical research — not general news that happens to mention health. NEVER create thematic buckets.',
    },
}


_JUNK_TITLE_WORDS = {
    "miscellaneous", "mixed", "various", "general", "roundup", "digest",
    "compilation", "data quality", "data integrity", "misclassified",
    "radio segment", "stock downgrade", "job listings", "puzzle solutions",
    "product review", "horoscope", "daily quiz", "crossword", "wordle",
    "multiple deaths reported", "multiple stock",
}

_JUNK_NARRATIVE_WORDS = {
    "miscellaneous", "mixed updates", "various", "roundup",
    "global entertainment, sports, and culture",
    "global democratic accountability, crime",
    "global feel-good", "global sports:", "human interest stories",
    "champions & record-breakers", "good news roundup",
    "record-breaking sports", "sports moments",
    "social progress worldwide", "progress worldwide",
    "highlights 20",  # "Highlights 2025", "Highlights 2026" etc
    "wins & milestones", "news & updates",
}

MAX_TITLE_LEN = 60


def _clean_title(title: str) -> str:
    """Enforce title length and quality constraints."""
    title = title.strip()
    if len(title) <= MAX_TITLE_LEN:
        return title
    # Try truncating at last separator before limit
    for sep in [": ", " — ", " - ", ", ", " & "]:
        idx = title.rfind(sep, 0, MAX_TITLE_LEN)
        if idx > 20:  # keep at least 20 chars
            return title[:idx]
    # Hard truncate at word boundary
    truncated = title[:MAX_TITLE_LEN]
    last_space = truncated.rfind(" ")
    if last_space > 20:
        return truncated[:last_space]
    return truncated

def _is_junk_event(event: dict) -> bool:
    """Detect catch-all/junk-drawer events that shouldn't be in situations."""
    title = (event.get("title") or "").lower()
    return any(w in title for w in _JUNK_TITLE_WORDS)

def _build_events_summary(conn, events: list[dict]) -> str:
    """Build a compact summary of recent events for the LLM."""
    ev_slice = [e for e in events if not _is_junk_event(e)][:30]
    # Batch-fetch topics for all events in one query (replaces N+1)
    topics_map = {}
    if ev_slice:
        ev_ids = [e["id"] for e in ev_slice]
        ph = ",".join("?" * len(ev_ids))
        rows = conn.execute(
            f"""SELECT es.event_id, se.topics
                FROM story_extractions se
                JOIN event_stories es ON se.story_id = es.story_id
                WHERE es.event_id IN ({ph})
                GROUP BY es.event_id""",
            ev_ids,
        ).fetchall()
        for r in rows:
            if r["topics"]:
                try:
                    topics = json.loads(r["topics"])
                    if topics:
                        topics_map[r["event_id"]] = topics[:3]
                except (json.JSONDecodeError, TypeError):
                    pass

    lines = []
    for e in ev_slice:
        desc = (e.get("description") or e.get("title", ""))[:120]
        loc = e.get("primary_location", "")
        loc_str = f" ({loc})" if loc else ""
        count = e.get("story_count", 0)
        severity = e.get("severity", "?")

        topics = topics_map.get(e["id"])
        topics_str = f" [{', '.join(topics)}]" if topics else ""

        lines.append(f"  Event #{e['id']}: {e['title']}{loc_str} - {desc} [{count} stories, severity={severity}]{topics_str}")

    return "\n".join(lines)


def _build_narratives_summary(narratives: list[dict]) -> str:
    """Build summary of existing narratives."""
    if not narratives:
        return "  (none yet)"
    lines = []
    for n in narratives:
        tags = json.loads(n.get("theme_tags", "[]")) if isinstance(n.get("theme_tags"), str) else n.get("theme_tags", [])
        tags_str = f" [{', '.join(tags)}]" if tags else ""
        lines.append(f"  Narrative #{n['id']}: {n['title']} - {(n.get('description') or '')[:100]}{tags_str} [{n.get('event_count', 0)} events]")
    return "\n".join(lines)



def _get_domain_events(conn, domain: str, limit: int = 50) -> list[dict]:
    """Fetch events relevant to a specific domain directly from the database.

    Each domain gets its own pool of top events (by story_count), rather than
    sharing from a single global top-N. This ensures sports/entertainment events
    are found even when news events dominate by volume.

    Filtering uses two signals combined with OR:
      1. Source ratio — fraction of stories from domain-tagged feeds
      2. Topic signal — LLM-extracted topics matching domain keywords
         (currently used for entertainment only)

    For positive: uses bright_side_score ratio OR positive-feed source ratio.
    """
    if domain == "positive":
        return _get_positive_events(conn, limit)

    if domain == "curious":
        return _get_curious_events(conn, limit)

    # Tag-based domains: find sources that have the domain's tags
    domain_tags = DOMAIN_FEED_TAGS.get(domain, {"news"})
    domain_sources = [
        src for src, tags in FEED_TAG_MAP.items()
        if any(t in domain_tags for t in tags)
    ]

    if not domain_sources:
        return []

    source_threshold = DOMAIN_SOURCE_RATIO.get(domain, 0.5)
    placeholders = ",".join("?" * len(domain_sources))
    rows = conn.execute(
        f"""SELECT e.*,
                   SUM(CASE WHEN s.source IN ({placeholders}) THEN 1 ELSE 0 END) as domain_count,
                   COUNT(*) as total_count
            FROM events e
            JOIN event_stories es ON e.id = es.event_id
            JOIN stories s ON es.story_id = s.id
            WHERE e.merged_into IS NULL AND e.status != 'resolved'
            GROUP BY e.id
            HAVING CAST(domain_count AS REAL) / total_count >= ?
            ORDER BY e.story_count DESC
            LIMIT ?""",
        (*domain_sources, source_threshold, limit),
    ).fetchall()
    results = {r["id"]: dict(r) for r in rows}

    # Add events matched by topic signal (for domains with topic keywords)
    _DOMAIN_TOPIC_SIGNALS = {
        "entertainment": _ENTERTAINMENT_TOPIC_SIGNALS,
        "science": _SCIENCE_TOPIC_SIGNALS,
        "business": _BUSINESS_TOPIC_SIGNALS,
        "health": _HEALTH_TOPIC_SIGNALS,
    }
    topic_signals = _DOMAIN_TOPIC_SIGNALS.get(domain)
    if topic_signals:
        topic_events = _get_events_by_topic_signal(
            conn, topic_signals, limit,
            exclude_ids=set(results.keys()),
        )
        for ev in topic_events:
            if len(results) >= limit:
                break
            results[ev["id"]] = ev

    # Return sorted by story_count descending
    return sorted(results.values(), key=lambda e: e.get("story_count", 0), reverse=True)[:limit]


def _get_events_by_topic_signal(
    conn, topic_keywords: set[str], limit: int, exclude_ids: set[int] | None = None,
) -> list[dict]:
    """Find events whose LLM-extracted topics match domain keywords.

    Scans story_extractions.topics (JSON array of slugs) for events not
    already matched by source ratio.  Requires at least 2 topic-matched
    stories per event to avoid false positives from a single mis-tagged story.
    """
    # Build a LIKE pattern for each keyword.  Topics are stored as JSON arrays
    # of slugs like ["oscars","film","celebrity"].  We match with LIKE against
    # the raw JSON string for simplicity — no json_each needed.
    if not topic_keywords:
        return []

    # We use a union of LIKE clauses: topics LIKE '%film%' OR topics LIKE '%oscars%' etc.
    # To keep it efficient, we limit to a reasonable number of keywords.
    like_clauses = " OR ".join(["se.topics LIKE ?"] * len(topic_keywords))
    like_params = [f"%{kw}%" for kw in topic_keywords]

    rows = conn.execute(
        f"""SELECT e.*,
                   COUNT(DISTINCT es.story_id) as topic_match_count
            FROM events e
            JOIN event_stories es ON e.id = es.event_id
            JOIN story_extractions se ON es.story_id = se.story_id
            WHERE e.merged_into IS NULL AND e.status != 'resolved'
              AND ({like_clauses})
            GROUP BY e.id
            HAVING topic_match_count >= 2
            ORDER BY e.story_count DESC
            LIMIT ?""",
        (*like_params, limit),
    ).fetchall()

    exclude = exclude_ids or set()
    return [dict(r) for r in rows if r["id"] not in exclude]


def _get_positive_events(conn, limit: int) -> list[dict]:
    """Fetch events for the positive domain.

    Two signals combined with OR:
      1. Bright-side ratio: >= 15% of stories have bright_side_score >= 3
      2. Positive-source ratio: >= 30% of stories come from positive-tagged feeds

    This ensures events from dedicated positive sources (Good News Network, etc.)
    always surface, while also catching inherently positive events from any source
    that the LLM scored highly.
    """
    # Signal 1: bright_side_score ratio (lowered from >= 4/30% to >= 3/15%)
    bright_rows = conn.execute(
        """SELECT e.*,
                  CAST(SUM(CASE WHEN se.bright_side_score >= 3 THEN 1 ELSE 0 END) AS REAL)
                      / COUNT(*) as bright_ratio
           FROM events e
           JOIN event_stories es ON e.id = es.event_id
           LEFT JOIN story_extractions se ON es.story_id = se.story_id
           WHERE e.merged_into IS NULL AND e.status != 'resolved'
           GROUP BY e.id
           HAVING bright_ratio >= 0.15
           ORDER BY e.story_count DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    results = {r["id"]: dict(r) for r in bright_rows}

    # Signal 2: positive-tagged feed sources
    positive_sources = [
        src for src, tags in FEED_TAG_MAP.items()
        if "positive" in tags
    ]
    if positive_sources:
        placeholders = ",".join("?" * len(positive_sources))
        source_rows = conn.execute(
            f"""SELECT e.*,
                       SUM(CASE WHEN s.source IN ({placeholders}) THEN 1 ELSE 0 END) as pos_source_count,
                       COUNT(*) as total_count
                FROM events e
                JOIN event_stories es ON e.id = es.event_id
                JOIN stories s ON es.story_id = s.id
                WHERE e.merged_into IS NULL AND e.status != 'resolved'
                GROUP BY e.id
                HAVING CAST(pos_source_count AS REAL) / total_count >= 0.3
                ORDER BY e.story_count DESC
                LIMIT ?""",
            (*positive_sources, limit),
        ).fetchall()
        for r in source_rows:
            if len(results) >= limit:
                break
            if r["id"] not in results:
                results[r["id"]] = dict(r)

    return sorted(results.values(), key=lambda e: e.get("story_count", 0), reverse=True)[:limit]


def _get_curious_events(conn, limit: int) -> list[dict]:
    """Fetch events for the curious/human-interest domain.

    Uses human_interest_score: events where >= 15% of stories score >= 5
    on human_interest_score qualify. This surfaces events with engaging,
    shareable, "you won't believe this" stories regardless of domain.
    """
    rows = conn.execute(
        """SELECT e.*,
                  CAST(SUM(CASE WHEN se.human_interest_score >= 5 THEN 1 ELSE 0 END) AS REAL)
                      / COUNT(*) as hi_ratio
           FROM events e
           JOIN event_stories es ON e.id = es.event_id
           LEFT JOIN story_extractions se ON es.story_id = se.story_id
           WHERE e.merged_into IS NULL AND e.status != 'resolved'
           GROUP BY e.id
           HAVING hi_ratio >= 0.15
           ORDER BY e.story_count DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def analyze_narratives(conn, domain: str = "news") -> dict:
    """Narrative analysis for a specific domain.

    Each domain gets its own prompt, event filter, and narrative cap.
    Returns stats: {"created": int, "updated": int, "domain": str}
    """
    client = get_anthropic_client()
    if not client:
        logger.info("No API key, skipping narrative analysis")
        return {"created": 0, "updated": 0, "domain": domain}

    max_narratives = DOMAIN_MAX_NARRATIVES.get(domain, 10)

    # Check if we analyzed this domain recently enough
    existing = conn.execute(
        """SELECT last_analyzed FROM narratives
           WHERE status = 'active' AND domain = ?
           ORDER BY last_analyzed DESC LIMIT 1""",
        (domain,),
    ).fetchone()
    if existing and existing["last_analyzed"]:
        try:
            last_time = datetime.fromisoformat(existing["last_analyzed"])
            hours_since = (datetime.now(timezone.utc) - last_time).total_seconds() / 3600
            if hours_since < ANALYSIS_INTERVAL_HOURS:
                return {"created": 0, "updated": 0, "domain": domain}
        except (ValueError, TypeError):
            pass

    # Get events relevant to this domain (each domain gets its own pool)
    events = _get_domain_events(conn, domain, limit=50)

    min_events = 2 if domain in ("sports", "entertainment", "positive", "curious") else 3
    if len(events) < min_events:
        logger.info("Domain '%s': only %d events, need %d — skipping", domain, len(events), min_events)
        return {"created": 0, "updated": 0, "domain": domain}

    # Get existing narratives for this domain only
    domain_narratives = [
        dict(r) for r in conn.execute(
            """SELECT * FROM narratives
               WHERE status = 'active' AND domain = ?
               ORDER BY story_count DESC, last_updated DESC
               LIMIT ?""",
            (domain, max_narratives),
        ).fetchall()
    ]

    events_summary = _build_events_summary(conn, events)
    narratives_summary = _build_narratives_summary(domain_narratives)

    dp = DOMAIN_PROMPTS.get(domain, DOMAIN_PROMPTS["news"])

    prompt = f"""{dp['intro']}

CURRENT EVENTS:
{events_summary}

EXISTING SITUATIONS:
{narratives_summary}

Your task:
1. Assign events to existing situations (by situation ID)
2. Create NEW situations when events clearly belong together but don't fit any existing situation
3. A situation is a specific, recognizable development:
   GOOD: {dp['examples_good']}
   BAD: {dp['examples_bad']}
   {dp['guidance']}

Return a JSON object with:
- "updates": array of updates to existing situations, each with:
  - "narrative_id": int (the situation ID)
  - "title": updated title if needed (max 60 chars, concrete phrase — NOT a comma-separated list)
  - "description": 1-2 sentence summary of current state
  - "theme_tags": array of topic tags
  - "event_ids": array of event IDs that belong to this situation
- "new_narratives": array of new situations to create, each with:
  - "title": string (max 60 chars, concrete situation name — NOT a list of sub-events)
  - "description": 1-2 sentence description of the situation
  - "theme_tags": array of topic tags
  - "event_ids": array of event IDs that belong (minimum 2)
- "deactivate": array of situation IDs to remove (use when two situations overlap heavily — move all events to the better one, then deactivate the redundant one)

Rules:
- TITLE LENGTH: Maximum 60 characters. No exceptions. No comma-separated lists. Use a single concrete phrase like "2026 Iran War" not "Iran War, Oil Crisis & Regional Tensions". Titles over 60 chars will be rejected.
- Only assign an event to a situation if it genuinely belongs — do NOT force-fit unrelated events. It's OK for events to be orphans.
- One event can belong to multiple situations IF it genuinely relates to both
- Prefer FEWER, LARGER situations over many small ones — merge aggressively
- DEDUP: If two existing situations cover the same topic (e.g. same policy, same sporting event, same crisis), MERGE them: update the larger one with all events from both, and deactivate the smaller one.
- Don't duplicate existing situations — update them instead
- If an existing situation is a "kitchen sink" lumping unrelated events (e.g., "Global Crime, Legal Proceedings, and Unrelated Updates"), deactivate it and create focused replacements.
- Max {max_narratives} total active situations
- Max 5 new situations per analysis

Return ONLY valid JSON, no other text."""

    try:
        response = client.messages.create(
            model=SONNET_MODEL,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        result = parse_llm_json(text, expected_type="dict")
        if result is None:
            return {"created": 0, "updated": 0, "domain": domain}
    except Exception as e:
        logger.warning("Narrative analysis (%s) LLM call failed: %s", domain, e)
        return {"created": 0, "updated": 0, "domain": domain}

    created = 0
    updated = 0

    # Build set of valid event IDs for this domain — reject hallucinated or junk events
    valid_event_ids = {e["id"] for e in events if not _is_junk_event(e)}

    # Process updates — accept both "event_ids" and "add_events" from LLM
    for update in result.get("updates", []):
        try:
            nid = update.get("narrative_id")
            if not nid:
                continue
            raw_event_ids = update.get("event_ids") or update.get("add_events") or []
            event_ids = [eid for eid in raw_event_ids if eid in valid_event_ids]
            existing_narr = conn.execute(
                "SELECT title, description, theme_tags FROM narratives WHERE id = ?",
                (nid,),
            ).fetchone()
            if not existing_narr:
                continue
            title = _clean_title(update.get("title") or existing_narr["title"])
            description = update.get("description") or existing_narr["description"]
            theme_tags = update.get("theme_tags") or json.loads(existing_narr["theme_tags"] or "[]")

            upsert_narrative(
                conn,
                title=title,
                description=description,
                theme_tags=theme_tags,
                event_ids=event_ids,
                narrative_id=nid,
                domain=domain,
            )
            updated += 1
        except Exception as e:
            logger.warning("Failed to update narrative %s: %s", update.get("narrative_id"), e)

    # Process new narratives
    for new in result.get("new_narratives", [])[:5]:
        try:
            raw_event_ids = new.get("event_ids") or new.get("add_events") or []
            event_ids = [eid for eid in raw_event_ids if eid in valid_event_ids]
            if len(event_ids) < 2:
                continue
            upsert_narrative(
                conn,
                title=_clean_title(new.get("title", "Unnamed theme")),
                description=new.get("description", ""),
                theme_tags=new.get("theme_tags", []),
                event_ids=event_ids,
                domain=domain,
            )
            created += 1
        except Exception as e:
            logger.warning("Failed to create narrative: %s", e)

    # Process explicit deactivations (LLM-flagged redundant narratives)
    deactivated = 0
    for nid in result.get("deactivate", []):
        try:
            if not isinstance(nid, int):
                continue
            # Only deactivate if it belongs to this domain
            row = conn.execute(
                "SELECT domain FROM narratives WHERE id = ? AND status = 'active'",
                (nid,),
            ).fetchone()
            if row and row["domain"] == domain:
                conn.execute(
                    "UPDATE narratives SET status = 'inactive' WHERE id = ?",
                    (nid,),
                )
                deactivated += 1
                logger.info("LLM deactivated redundant narrative [%d] in %s", nid, domain)
        except Exception as e:
            logger.warning("Failed to deactivate narrative %s: %s", nid, e)

    # Clean up empty or junk narratives for this domain only
    cleaned = 0
    domain_all = conn.execute(
        """SELECT id, title, event_count, story_count FROM narratives
           WHERE status = 'active' AND domain = ?
           ORDER BY story_count DESC, last_updated DESC""",
        (domain,),
    ).fetchall()
    for narr in domain_all:
        should_clean = narr["event_count"] == 0
        # Detect kitchen-sink narrative titles
        title_lower = (narr["title"] or "").lower()
        if any(w in title_lower for w in _JUNK_NARRATIVE_WORDS):
            should_clean = True
            logger.info("Deactivating junk narrative [%d]: %s", narr["id"], narr["title"][:60])
        if should_clean:
            conn.execute(
                "UPDATE narratives SET status = 'inactive' WHERE id = ?",
                (narr["id"],),
            )
            cleaned += 1

    # Enforce per-domain cap: deactivate lowest-ranked excess narratives
    active_count = len(domain_all) - cleaned
    if active_count > max_narratives:
        # domain_all is sorted by story_count DESC — keep top N, deactivate rest
        kept = 0
        for narr in domain_all:
            if narr["event_count"] == 0:
                continue  # already cleaned
            kept += 1
            if kept > max_narratives:
                conn.execute(
                    "UPDATE narratives SET status = 'inactive' WHERE id = ?",
                    (narr["id"],),
                )
                cleaned += 1

    if cleaned:
        conn.commit()
        logger.info("Cleaned up %d empty/excess %s narratives", cleaned, domain)

    logger.info("Narrative analysis (%s): %d created, %d updated, %d cleaned",
                domain, created, updated, cleaned)
    return {"created": created, "updated": updated, "cleaned": cleaned, "domain": domain}
