"""SQLite database for thisminute."""

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    summary TEXT,
    source TEXT NOT NULL,
    location_name TEXT,
    lat REAL,
    lon REAL,
    published_at TEXT,
    scraped_at TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    concepts TEXT DEFAULT '[]',
    ner_entities TEXT,
    geocode_confidence REAL,
    sentiment TEXT DEFAULT NULL,
    extraction_status TEXT DEFAULT 'pending'
);

CREATE INDEX IF NOT EXISTS idx_stories_scraped_at ON stories(scraped_at);
CREATE INDEX IF NOT EXISTS idx_stories_source ON stories(source);
CREATE INDEX IF NOT EXISTS idx_stories_category ON stories(category);

CREATE TABLE IF NOT EXISTS geocode_cache (
    location_name TEXT PRIMARY KEY,
    lat REAL,
    lon REAL,
    display_name TEXT,
    importance REAL,
    cached_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feed_state (
    feed_url TEXT PRIMARY KEY,
    last_etag TEXT,
    last_modified TEXT,
    last_checked TEXT
);

-- Clustered events
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'emerging',
    key_actors TEXT DEFAULT '[]',
    primary_location TEXT,
    primary_lat REAL,
    primary_lon REAL,
    concepts TEXT DEFAULT '[]',
    story_count INTEGER DEFAULT 0,
    first_seen TEXT NOT NULL,
    last_updated TEXT NOT NULL,
    last_analyzed TEXT,
    analysis_hash TEXT,
    related_events TEXT DEFAULT '[]',
    created_at TEXT NOT NULL,
    merged_into INTEGER,
    severity INTEGER,
    primary_action TEXT,
    affected_parties TEXT DEFAULT '[]',
    event_type TEXT
);

CREATE INDEX IF NOT EXISTS idx_events_status ON events(status);
CREATE INDEX IF NOT EXISTS idx_events_last_updated ON events(last_updated);

-- Many-to-many join
CREATE TABLE IF NOT EXISTS event_stories (
    event_id INTEGER NOT NULL,
    story_id INTEGER NOT NULL,
    added_at TEXT NOT NULL,
    PRIMARY KEY (event_id, story_id)
);

CREATE INDEX IF NOT EXISTS idx_event_stories_story ON event_stories(story_id);

-- Event registry: canonical list of known events for story matching
CREATE TABLE IF NOT EXISTS event_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    registry_label TEXT NOT NULL,
    map_label TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    story_count INTEGER DEFAULT 0,
    first_seen TEXT NOT NULL,
    last_matched TEXT,
    primary_location TEXT,
    primary_lat REAL,
    primary_lon REAL,
    created_at TEXT NOT NULL,
    retired_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_event_registry_status ON event_registry(status);

-- Link stories to registry events
CREATE TABLE IF NOT EXISTS registry_stories (
    registry_event_id INTEGER NOT NULL,
    story_id INTEGER NOT NULL,
    added_at TEXT NOT NULL,
    PRIMARY KEY (registry_event_id, story_id)
);

CREATE INDEX IF NOT EXISTS idx_registry_stories_story ON registry_stories(story_id);

-- Wikipedia event articles: canonical event identification via Wikipedia
CREATE TABLE IF NOT EXISTS wiki_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_title TEXT NOT NULL UNIQUE,
    display_title TEXT,
    status TEXT DEFAULT 'active',
    story_count INTEGER DEFAULT 0,
    first_seen TEXT NOT NULL,
    last_matched TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_wiki_events_status ON wiki_events(status);
CREATE INDEX IF NOT EXISTS idx_wiki_events_title ON wiki_events(article_title);

-- Link stories to wiki events (many-to-many)
CREATE TABLE IF NOT EXISTS story_wiki_events (
    story_id INTEGER NOT NULL,
    wiki_event_id INTEGER NOT NULL,
    added_at TEXT NOT NULL,
    PRIMARY KEY (story_id, wiki_event_id)
);

CREATE INDEX IF NOT EXISTS idx_story_wiki_events_wiki ON story_wiki_events(wiki_event_id);

-- Singleton: periodic "state of the world"
CREATE TABLE IF NOT EXISTS world_overview (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    summary TEXT,
    generated_at TEXT,
    top_events TEXT DEFAULT '[]'
);

-- LLM-extracted structured data per story
CREATE TABLE IF NOT EXISTS story_extractions (
    story_id INTEGER PRIMARY KEY,
    extraction_json TEXT NOT NULL,
    topics TEXT DEFAULT '[]',
    sentiment TEXT,
    severity INTEGER,
    primary_action TEXT,
    event_signature TEXT,
    location_type TEXT DEFAULT 'terrestrial',
    search_keywords TEXT DEFAULT '[]',
    is_opinion INTEGER DEFAULT 0,
    extracted_at TEXT NOT NULL,
    extraction_model TEXT DEFAULT 'claude-haiku-4-5-20251001',
    extraction_version INTEGER DEFAULT 1
);

-- Denormalized actors for multi-dimensional search
CREATE TABLE IF NOT EXISTS story_actors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    type TEXT,
    description TEXT,
    demographic TEXT,
    UNIQUE(story_id, name, role)
);

CREATE INDEX IF NOT EXISTS idx_story_actors_role ON story_actors(role);
CREATE INDEX IF NOT EXISTS idx_story_actors_name ON story_actors(name);
CREATE INDEX IF NOT EXISTS idx_story_actors_demographic ON story_actors(demographic);
CREATE INDEX IF NOT EXISTS idx_story_actors_story ON story_actors(story_id);

-- Richer location data from LLM
CREATE TABLE IF NOT EXISTS story_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    context TEXT,
    UNIQUE(story_id, name, role)
);

CREATE INDEX IF NOT EXISTS idx_story_locations_story ON story_locations(story_id);

-- Narratives: long-running themes spanning multiple events
CREATE TABLE IF NOT EXISTS narratives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'active',
    theme_tags TEXT DEFAULT '[]',
    domain TEXT DEFAULT 'news',
    first_seen TEXT NOT NULL,
    last_updated TEXT NOT NULL,
    event_count INTEGER DEFAULT 0,
    story_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    last_analyzed TEXT
);

-- Many-to-many: narratives <-> events
CREATE TABLE IF NOT EXISTS narrative_events (
    narrative_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL,
    relevance_score REAL DEFAULT 1.0,
    added_at TEXT NOT NULL,
    PRIMARY KEY (narrative_id, event_id)
);
CREATE INDEX IF NOT EXISTS idx_narrative_events_event ON narrative_events(event_id);
CREATE INDEX IF NOT EXISTS idx_narratives_status_domain ON narratives(status, domain);
"""


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Get a SQLite connection with WAL mode enabled."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(str(path), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """Initialize database schema."""
    conn = get_connection(db_path)
    conn.executescript(SCHEMA)
    # Migrate: add bbox columns to geocode_cache if missing
    for col in ("bbox_south", "bbox_north", "bbox_west", "bbox_east"):
        try:
            conn.execute(f"ALTER TABLE geocode_cache ADD COLUMN {col} REAL")
        except sqlite3.OperationalError:
            pass  # column already exists
    # Migrate: add sentiment column to stories if missing
    try:
        conn.execute("ALTER TABLE stories ADD COLUMN sentiment TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass  # column already exists
    # Migrate: add extraction_status column to stories if missing
    try:
        conn.execute("ALTER TABLE stories ADD COLUMN extraction_status TEXT DEFAULT 'pending'")
    except sqlite3.OperationalError:
        pass
    # Migrate: add new event columns if missing
    for col, default in [
        ("severity", None), ("primary_action", None),
        ("affected_parties", "'[]'"), ("event_type", None),
    ]:
        try:
            defstr = f" DEFAULT {default}" if default else ""
            conn.execute(f"ALTER TABLE events ADD COLUMN {col} TEXT{defstr}")
        except sqlite3.OperationalError:
            pass
    # Migrate: add new story_extractions columns if missing
    for col, default in [
        ("location_type", "'terrestrial'"), ("search_keywords", "'[]'"),
        ("is_opinion", "0"),
    ]:
        try:
            conn.execute(f"ALTER TABLE story_extractions ADD COLUMN {col} TEXT DEFAULT {default}")
        except sqlite3.OperationalError:
            pass
    # Migrate: add registry_event_id to story_extractions
    try:
        conn.execute("ALTER TABLE story_extractions ADD COLUMN registry_event_id INTEGER")
    except sqlite3.OperationalError:
        pass
    # Migrate: add bright_side columns to story_extractions
    for col, default in [
        ("bright_side_score", "NULL"),
        ("bright_side_category", "NULL"),
        ("bright_side_headline", "NULL"),
    ]:
        try:
            conn.execute(f"ALTER TABLE story_extractions ADD COLUMN {col} TEXT DEFAULT {default}")
        except sqlite3.OperationalError:
            pass
    # Migrate: add human_interest_score to story_extractions
    try:
        conn.execute("ALTER TABLE story_extractions ADD COLUMN human_interest_score INTEGER DEFAULT NULL")
    except sqlite3.OperationalError:
        pass
    # Migrate: add translated_title to story_extractions (for non-English feeds)
    try:
        conn.execute("ALTER TABLE story_extractions ADD COLUMN translated_title TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass
    # Migrate: deduplicate existing stories with same title+source, keeping newest
    try:
        dupes = conn.execute("""
            SELECT id FROM stories WHERE id NOT IN (
                SELECT MAX(id) FROM stories GROUP BY title, source
            )
        """).fetchall()
        if dupes:
            dupe_ids = [r[0] for r in dupes]
            placeholders = ",".join("?" * len(dupe_ids))
            conn.execute(f"DELETE FROM event_stories WHERE story_id IN ({placeholders})", dupe_ids)
            conn.execute(f"DELETE FROM stories WHERE id IN ({placeholders})", dupe_ids)
            conn.commit()
    except sqlite3.OperationalError:
        pass
    # Migrate: add unique index on title+source
    try:
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_stories_title_source ON stories(title, source)")
    except sqlite3.OperationalError:
        pass
    # Migrate: add origin column (rss/gdelt)
    try:
        conn.execute("ALTER TABLE stories ADD COLUMN origin TEXT DEFAULT 'rss'")
    except sqlite3.OperationalError:
        pass
    # Migrate: add domain column to narratives
    try:
        conn.execute("ALTER TABLE narratives ADD COLUMN domain TEXT DEFAULT 'news'")
    except sqlite3.OperationalError:
        pass
    # Migrate: add index on event_signature for fast clustering lookups
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_extractions_event_signature ON story_extractions(event_signature)")
    except sqlite3.OperationalError:
        pass
    # Migrate: add image_url column to stories
    try:
        conn.execute("ALTER TABLE stories ADD COLUMN image_url TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass
    # Migrate: add composite index for stories API query performance
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_stories_origin_scraped ON stories(origin, scraped_at DESC)")
    except sqlite3.OperationalError:
        pass
    # Migrate: add user_feedback table
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS user_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feedback_type TEXT NOT NULL,
            target_type TEXT,
            target_id INTEGER,
            target_title TEXT,
            message TEXT,
            context_json TEXT DEFAULT '{}',
            browser_hash TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_user_feedback_status ON user_feedback(status);
        CREATE INDEX IF NOT EXISTS idx_user_feedback_type ON user_feedback(feedback_type);
    """)
    # Migrate: add resolution_note column to user_feedback
    try:
        conn.execute("ALTER TABLE user_feedback ADD COLUMN resolution_note TEXT DEFAULT ''")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    # Migrate: add source_type column to stories (reported vs inferred)
    try:
        conn.execute("ALTER TABLE stories ADD COLUMN source_type TEXT DEFAULT 'reported'")
    except sqlite3.OperationalError:
        pass
    # Migrate: add user_feeds table for user-added RSS feeds
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS user_feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            title TEXT,
            feed_tag TEXT DEFAULT 'news',
            browser_hash TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            last_fetched TEXT,
            last_error TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_user_feeds_url_hash ON user_feeds(url, browser_hash);
        CREATE INDEX IF NOT EXISTS idx_user_feeds_active ON user_feeds(is_active);
        CREATE INDEX IF NOT EXISTS idx_user_feeds_browser ON user_feeds(browser_hash);
    """)
    conn.close()


def insert_story(conn: sqlite3.Connection, story: dict) -> bool:
    """Insert a story, returning True if new (not duplicate)."""
    try:
        cursor = conn.execute(
            """INSERT OR IGNORE INTO stories
               (title, url, summary, source, location_name, lat, lon,
                published_at, scraped_at, category, concepts, ner_entities, geocode_confidence, origin, image_url, source_type)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                story["title"],
                story["url"],
                story.get("summary"),
                story["source"],
                story.get("location_name"),
                story.get("lat"),
                story.get("lon"),
                story.get("published_at"),
                story.get("scraped_at", datetime.now(timezone.utc).isoformat()),
                story.get("category", "general"),
                json.dumps(story.get("concepts", [])),
                json.dumps(story.get("ner_entities", [])),
                story.get("geocode_confidence"),
                story.get("origin", "rss"),
                story.get("image_url"),
                story.get("source_type", "reported"),
            ),
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.IntegrityError:
        return False


def get_stories(
    conn: sqlite3.Connection,
    since: Optional[str] = None,
    source: Optional[str] = None,
    category: Optional[str] = None,
    concepts: Optional[list[str]] = None,
    exclude_concepts: Optional[list[str]] = None,
    search: Optional[str] = None,
    limit: int = 500,
) -> list[dict]:
    """Query stories with optional filters. Returns only geocoded stories.

    concepts: if provided, story must match ANY of these concepts
    exclude_concepts: if provided, story must NOT match any of these
    search: text search in title and summary
    """
    base_where = "lat IS NOT NULL AND lon IS NOT NULL"
    extra_clauses = []
    params = []

    if since:
        extra_clauses.append("scraped_at > ?")
        params.append(since)
    if source:
        extra_clauses.append("source = ?")
        params.append(source)
    if category:
        extra_clauses.append("category = ?")
        params.append(category)
    if search:
        extra_clauses.append("(title LIKE ? OR summary LIKE ?)")
        term = f"%{search}%"
        params.extend([term, term])
    if concepts:
        concept_clauses = []
        for c in concepts:
            concept_clauses.append("concepts LIKE ?")
            params.append(f'%"{c}"%')
        extra_clauses.append("(" + " OR ".join(concept_clauses) + ")")
    if exclude_concepts:
        for c in exclude_concepts:
            extra_clauses.append("concepts NOT LIKE ?")
            params.append(f'%"{c}"%')

    where = base_where
    if extra_clauses:
        where += " AND " + " AND ".join(extra_clauses)

    # Balance RSS and GDELT origins ~50/50, plus all USGS stories (tiny volume)
    half = limit // 2
    cols = "id, title, url, summary, source, location_name, lat, lon, published_at, scraped_at, category, concepts, origin, image_url, source_type"
    rss_query = f"SELECT {cols} FROM stories WHERE {where} AND origin = 'rss' ORDER BY scraped_at DESC LIMIT ?"
    gdelt_query = f"SELECT {cols} FROM stories WHERE {where} AND origin = 'gdelt' ORDER BY scraped_at DESC LIMIT ?"
    usgs_query = f"SELECT {cols} FROM stories WHERE {where} AND origin = 'usgs' ORDER BY scraped_at DESC LIMIT ?"

    rss_params = params + [half]
    gdelt_params = params + [half]

    rss_rows = conn.execute(rss_query, rss_params).fetchall()
    gdelt_rows = conn.execute(gdelt_query, gdelt_params).fetchall()
    # USGS volume is tiny (~5-15/day), fetch all recent ones
    usgs_rows = conn.execute(usgs_query, params + [50]).fetchall()

    # Fetch all other origins (noaa, eonet, gdacs, reliefweb, who, launches,
    # openaq, travel, firms, meteoalarm, acled, jma, etc.) -- typically low
    # volume so no special balancing is needed.
    inferred_query = f"SELECT {cols} FROM stories WHERE {where} AND origin NOT IN ('rss', 'gdelt', 'usgs') ORDER BY scraped_at DESC LIMIT ?"
    inferred_rows = conn.execute(inferred_query, params + [limit]).fetchall()

    # If one origin has fewer, give remaining slots to the other
    rss_count = len(rss_rows)
    gdelt_count = len(gdelt_rows)
    if rss_count < half and gdelt_count == half:
        extra = half - rss_count
        gdelt_rows = conn.execute(
            f"SELECT {cols} FROM stories WHERE {where} AND origin = 'gdelt' ORDER BY scraped_at DESC LIMIT ?",
            params + [half + extra],
        ).fetchall()
    elif gdelt_count < half and rss_count == half:
        extra = half - gdelt_count
        rss_rows = conn.execute(
            f"SELECT {cols} FROM stories WHERE {where} AND origin = 'rss' ORDER BY scraped_at DESC LIMIT ?",
            params + [half + extra],
        ).fetchall()

    # Merge, dedup by title (keep first = most recent), sort by scraped_at
    all_rows = [dict(r) for r in rss_rows] + [dict(r) for r in gdelt_rows] + [dict(r) for r in usgs_rows] + [dict(r) for r in inferred_rows]
    all_rows.sort(key=lambda s: s.get("scraped_at", ""), reverse=True)

    seen_titles = set()
    deduped = []
    for s in all_rows:
        title_key = s.get("title", "").lower().strip()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        deduped.append(s)

    return deduped


def get_sources(conn: sqlite3.Connection) -> list[str]:
    """Get distinct source names."""
    rows = conn.execute(
        "SELECT DISTINCT source FROM stories ORDER BY source"
    ).fetchall()
    return [r["source"] for r in rows]


def get_source_counts(conn: sqlite3.Connection) -> list[dict]:
    """Get source names with story counts, ordered by count descending."""
    rows = conn.execute(
        "SELECT source, COUNT(*) as count FROM stories GROUP BY source ORDER BY count DESC"
    ).fetchall()
    return [{"source": r["source"], "count": r["count"]} for r in rows]


def get_categories(conn: sqlite3.Connection) -> list[str]:
    """Get distinct categories."""
    rows = conn.execute(
        "SELECT DISTINCT category FROM stories ORDER BY category"
    ).fetchall()
    return [r["category"] for r in rows]


def get_stats(conn: sqlite3.Connection) -> dict:
    """Get database statistics."""
    total = conn.execute("SELECT COUNT(*) as c FROM stories").fetchone()["c"]
    geocoded = conn.execute(
        "SELECT COUNT(*) as c FROM stories WHERE lat IS NOT NULL"
    ).fetchone()["c"]
    oldest = conn.execute(
        "SELECT MIN(scraped_at) as m FROM stories"
    ).fetchone()["m"]
    newest = conn.execute(
        "SELECT MAX(scraped_at) as m FROM stories"
    ).fetchone()["m"]
    last_1h = conn.execute(
        "SELECT COUNT(*) as c FROM stories WHERE scraped_at > datetime('now', '-1 hour')"
    ).fetchone()["c"]
    return {
        "total_stories": total,
        "geocoded_stories": geocoded,
        "oldest": oldest,
        "newest": newest,
        "last_1h": last_1h,
    }


def get_domain_distribution(conn: sqlite3.Connection, hours: int = 24) -> dict:
    """Return domain distribution metrics for stories in the last *hours* hours.

    Computes:
    - Story counts per feed tag (news, sports, entertainment, positive, tech, etc.)
    - Story counts per source_type (reported vs inferred)
    - Positive proxy: stories with bright_side_score >= 4
    - Curious proxy: stories with human_interest_score >= 6
    - Total story count for the period
    - Active narrative counts per domain
    - Event counts with domain breakdown via constituent stories
    """
    from .config import FEED_TAG_MAP

    cutoff_clause = f"datetime('now', '-{hours} hours')"

    # Total stories in window
    total = conn.execute(
        f"SELECT COUNT(*) as c FROM stories WHERE scraped_at > {cutoff_clause}"
    ).fetchone()["c"]

    # Stories per source_type
    source_type_rows = conn.execute(
        f"""SELECT COALESCE(source_type, 'reported') as st, COUNT(*) as c
            FROM stories WHERE scraped_at > {cutoff_clause}
            GROUP BY st"""
    ).fetchall()
    by_source_type = {r["st"]: r["c"] for r in source_type_rows}

    # Stories per feed tag -- a story may count toward multiple tags
    # via its source name in FEED_TAG_MAP
    source_rows = conn.execute(
        f"""SELECT source, COUNT(*) as c
            FROM stories WHERE scraped_at > {cutoff_clause}
            GROUP BY source"""
    ).fetchall()
    tag_counts = {}
    untagged = 0
    for row in source_rows:
        tags = FEED_TAG_MAP.get(row["source"], [])
        if not tags:
            untagged += row["c"]
        for tag in tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + row["c"]

    # Positive proxy: stories with bright_side_score >= 4
    positive_proxy = conn.execute(
        f"""SELECT COUNT(*) as c
            FROM stories s
            JOIN story_extractions se ON se.story_id = s.id
            WHERE s.scraped_at > {cutoff_clause}
            AND se.bright_side_score >= 4"""
    ).fetchone()["c"]

    # Curious proxy: stories with human_interest_score >= 6
    curious_proxy = conn.execute(
        f"""SELECT COUNT(*) as c
            FROM stories s
            JOIN story_extractions se ON se.story_id = s.id
            WHERE s.scraped_at > {cutoff_clause}
            AND se.human_interest_score >= 6"""
    ).fetchone()["c"]

    # Extracted vs pending
    extracted = conn.execute(
        f"""SELECT COUNT(*) as c
            FROM stories s
            JOIN story_extractions se ON se.story_id = s.id
            WHERE s.scraped_at > {cutoff_clause}"""
    ).fetchone()["c"]

    # Active narrative counts per domain
    narrative_rows = conn.execute(
        """SELECT domain, COUNT(*) as c
           FROM narratives WHERE status = 'active'
           GROUP BY domain"""
    ).fetchall()
    narratives_by_domain = {r["domain"]: r["c"] for r in narrative_rows}

    # Event counts in the window with story-source-based domain breakdown
    event_rows = conn.execute(
        f"""SELECT e.id, GROUP_CONCAT(s.source, '||') as sources
            FROM events e
            JOIN event_stories es ON es.event_id = e.id
            JOIN stories s ON s.id = es.story_id
            WHERE e.last_updated > {cutoff_clause}
            GROUP BY e.id"""
    ).fetchall()
    event_tag_counts = {}
    total_events = len(event_rows)
    for erow in event_rows:
        sources = (erow["sources"] or "").split("||")
        event_tags = set()
        for src in sources:
            for tag in FEED_TAG_MAP.get(src.strip(), []):
                event_tags.add(tag)
        for tag in event_tags:
            event_tag_counts[tag] = event_tag_counts.get(tag, 0) + 1

    return {
        "hours": hours,
        "total_stories": total,
        "extracted_stories": extracted,
        "by_feed_tag": tag_counts,
        "untagged_stories": untagged,
        "by_source_type": by_source_type,
        "positive_proxy": positive_proxy,
        "curious_proxy": curious_proxy,
        "narratives_by_domain": narratives_by_domain,
        "total_events": total_events,
        "events_by_tag": event_tag_counts,
    }


# --- Feed state ---

def get_feed_state(conn: sqlite3.Connection, feed_url: str) -> Optional[dict]:
    """Get cached ETag/Last-Modified for a feed."""
    row = conn.execute(
        "SELECT * FROM feed_state WHERE feed_url = ?", (feed_url,)
    ).fetchone()
    return dict(row) if row else None


def update_feed_state(
    conn: sqlite3.Connection,
    feed_url: str,
    etag: Optional[str] = None,
    modified: Optional[str] = None,
) -> None:
    """Update feed state after a fetch."""
    conn.execute(
        """INSERT OR REPLACE INTO feed_state (feed_url, last_etag, last_modified, last_checked)
           VALUES (?, ?, ?, ?)""",
        (feed_url, etag, modified, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()


# --- Geocode cache ---

def get_cached_geocode(conn: sqlite3.Connection, location_name: str) -> Optional[dict]:
    """Look up a cached geocode result. Returns dict or None if not cached."""
    row = conn.execute(
        "SELECT * FROM geocode_cache WHERE location_name = ?", (location_name,)
    ).fetchone()
    return dict(row) if row else None


def cache_geocode(
    conn: sqlite3.Connection,
    location_name: str,
    lat: Optional[float],
    lon: Optional[float],
    display_name: Optional[str] = None,
    importance: Optional[float] = None,
    bbox_south: Optional[float] = None,
    bbox_north: Optional[float] = None,
    bbox_west: Optional[float] = None,
    bbox_east: Optional[float] = None,
) -> None:
    """Cache a geocode result (including null results for failed lookups)."""
    conn.execute(
        """INSERT OR REPLACE INTO geocode_cache
           (location_name, lat, lon, display_name, importance, cached_at,
            bbox_south, bbox_north, bbox_west, bbox_east)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            location_name,
            lat,
            lon,
            display_name,
            importance,
            datetime.now(timezone.utc).isoformat(),
            bbox_south,
            bbox_north,
            bbox_west,
            bbox_east,
        ),
    )
    conn.commit()


# --- Events ---

def get_active_events(conn: sqlite3.Connection, limit: int = 100) -> list[dict]:
    """Get active (non-resolved, non-merged) events sorted by story count."""
    rows = conn.execute(
        """SELECT * FROM events
           WHERE merged_into IS NULL AND status != 'resolved'
           ORDER BY story_count DESC, last_updated DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_all_events(
    conn: sqlite3.Connection,
    status: Optional[str] = None,
    limit: int = 50,
    min_stories: int = 1,
) -> list[dict]:
    """Get events with optional status filter."""
    query = "SELECT * FROM events WHERE merged_into IS NULL"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    else:
        query += " AND status != 'resolved'"
    if min_stories > 1:
        query += " AND story_count >= ?"
        params.append(min_stories)
    query += " ORDER BY story_count DESC, last_updated DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_event_by_id(conn: sqlite3.Connection, event_id: int) -> Optional[dict]:
    """Get a single event by ID."""
    row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    return dict(row) if row else None


def get_event_stories(
    conn: sqlite3.Connection,
    event_id: int,
    limit: int = 50,
) -> list[dict]:
    """Get stories for an event, newest first."""
    rows = conn.execute(
        """SELECT s.* FROM stories s
           JOIN event_stories es ON s.id = es.story_id
           WHERE es.event_id = ?
           ORDER BY s.scraped_at DESC
           LIMIT ?""",
        (event_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def get_unassigned_stories(conn: sqlite3.Connection, limit: int = 200) -> list[dict]:
    """Get stories not yet assigned to any event, newest first."""
    rows = conn.execute(
        """SELECT * FROM stories
           WHERE id NOT IN (SELECT story_id FROM event_stories)
           ORDER BY scraped_at DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def upsert_world_overview(
    conn: sqlite3.Connection,
    summary: str,
    top_events: list[int],
) -> None:
    """Insert or update the singleton world overview."""
    conn.execute(
        """INSERT OR REPLACE INTO world_overview (id, summary, generated_at, top_events)
           VALUES (1, ?, ?, ?)""",
        (summary, datetime.now(timezone.utc).isoformat(), json.dumps(top_events)),
    )
    conn.commit()


def get_world_overview(conn: sqlite3.Connection) -> Optional[dict]:
    """Get the current world overview."""
    row = conn.execute("SELECT * FROM world_overview WHERE id = 1").fetchone()
    return dict(row) if row else None


# --- Story extractions ---

def get_pending_extraction_stories(
    conn: sqlite3.Connection, limit: int = 50,
) -> list[dict]:
    """Get stories that haven't been LLM-extracted yet.

    Priority: 'pending' first (newly scraped), then 'legacy' stories
    that belong to active events (worth enriching), then remaining legacy.
    """
    # First: pending stories (highest priority, always process)
    rows = conn.execute(
        """SELECT id, title, summary, source, location_name, lat, lon, scraped_at
           FROM stories
           WHERE extraction_status = 'pending'
           ORDER BY scraped_at DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    result = [dict(r) for r in rows]
    remaining = limit - len(result)

    if remaining > 0:
        # Second: legacy stories in active events (worth enriching)
        seen_ids = {r["id"] for r in result}
        rows = conn.execute(
            """SELECT DISTINCT s.id, s.title, s.summary, s.source,
                      s.location_name, s.lat, s.lon, s.scraped_at
               FROM stories s
               JOIN event_stories es ON s.id = es.story_id
               JOIN events e ON es.event_id = e.id
               WHERE s.extraction_status = 'legacy'
               AND e.merged_into IS NULL AND e.status != 'resolved'
               ORDER BY s.scraped_at DESC
               LIMIT ?""",
            (remaining,),
        ).fetchall()
        for r in rows:
            if r["id"] not in seen_ids:
                result.append(dict(r))
                seen_ids.add(r["id"])

    return result


def store_extraction(
    conn: sqlite3.Connection,
    story_id: int,
    extraction: dict,
) -> None:
    """Store LLM extraction results into story_extractions, story_actors, story_locations."""
    now = datetime.now(timezone.utc).isoformat()

    # Main extraction record
    # Extract bright_side fields
    bright_side = extraction.get("bright_side")
    bs_score = None
    bs_category = None
    bs_headline = None
    if isinstance(bright_side, dict):
        raw_score = bright_side.get("score")
        bs_score = int(raw_score) if raw_score is not None else None
        bs_category = bright_side.get("category")
        bs_headline = bright_side.get("headline")

    # Extract human_interest_score
    hi_score = extraction.get("human_interest_score")
    if hi_score is not None:
        try:
            hi_score = int(hi_score)
        except (ValueError, TypeError):
            hi_score = None

    conn.execute(
        """INSERT OR REPLACE INTO story_extractions
           (story_id, extraction_json, topics, sentiment, severity,
            primary_action, event_signature, location_type, search_keywords,
            is_opinion, extracted_at, registry_event_id,
            bright_side_score, bright_side_category, bright_side_headline,
            human_interest_score, translated_title)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            story_id,
            json.dumps(extraction),
            json.dumps(extraction.get("topics") or []),
            extraction.get("sentiment"),
            extraction.get("severity"),
            extraction.get("primary_action"),
            extraction.get("event_signature"),
            extraction.get("location_type", "terrestrial"),
            json.dumps(extraction.get("search_keywords") or []),
            1 if extraction.get("is_opinion") else 0,
            now,
            extraction.get("registry_event_id"),
            bs_score,
            bs_category,
            bs_headline,
            hi_score,
            extraction.get("translated_title"),
        ),
    )

    # Actors
    for actor in extraction.get("actors") or []:
        try:
            conn.execute(
                """INSERT OR IGNORE INTO story_actors
                   (story_id, name, role, type, description, demographic)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    story_id,
                    actor.get("name", ""),
                    actor.get("role", "participant"),
                    actor.get("type"),
                    actor.get("description"),
                    actor.get("demographic"),
                ),
            )
        except Exception:
            pass

    # Locations
    for loc in extraction.get("locations") or []:
        try:
            conn.execute(
                """INSERT OR IGNORE INTO story_locations
                   (story_id, name, role, context)
                   VALUES (?, ?, ?, ?)""",
                (
                    story_id,
                    loc.get("name", ""),
                    loc.get("role", "mentioned"),
                    loc.get("context"),
                ),
            )
        except Exception:
            pass

    # Update story extraction status and overwrite concepts/sentiment
    status = "legacy" if extraction.get("_legacy") else "done"
    conn.execute(
        """UPDATE stories SET
           extraction_status = ?,
           concepts = ?,
           sentiment = ?,
           category = ?
           WHERE id = ?""",
        (
            status,
            json.dumps(extraction.get("topics") or []),
            extraction.get("sentiment"),
            extraction.get("topics", ["general"])[0] if extraction.get("topics") else "general",
            story_id,
        ),
    )
    conn.commit()


def get_story_extraction(conn: sqlite3.Connection, story_id: int) -> Optional[dict]:
    """Get extraction for a single story."""
    row = conn.execute(
        "SELECT * FROM story_extractions WHERE story_id = ?", (story_id,)
    ).fetchone()
    return dict(row) if row else None


def get_story_actors(conn: sqlite3.Connection, story_id: int) -> list[dict]:
    """Get actors for a story."""
    rows = conn.execute(
        "SELECT * FROM story_actors WHERE story_id = ?", (story_id,)
    ).fetchall()
    return [dict(r) for r in rows]


# --- Multi-dimensional search ---

def search_stories_by_actor(
    conn: sqlite3.Connection,
    role: Optional[str] = None,
    name: Optional[str] = None,
    demographic: Optional[str] = None,
    limit: int = 200,
) -> list[dict]:
    """Search stories by actor attributes."""
    query = """
        SELECT DISTINCT s.* FROM stories s
        JOIN story_actors sa ON s.id = sa.story_id
        WHERE 1=1
    """
    params = []
    if role:
        query += " AND sa.role = ?"
        params.append(role)
    if name:
        query += " AND sa.name LIKE ?"
        params.append(f"%{name}%")
    if demographic:
        query += " AND sa.demographic LIKE ?"
        params.append(f"%{demographic}%")
    query += " ORDER BY s.scraped_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def search_stories_multi(
    conn: sqlite3.Connection,
    actor_role: Optional[str] = None,
    actor_name: Optional[str] = None,
    actor_demographic: Optional[str] = None,
    action: Optional[str] = None,
    topic: Optional[str] = None,
    severity_min: Optional[int] = None,
    location_type: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 200,
) -> list[dict]:
    """Multi-dimensional search across stories, extractions, and actors."""
    has_actor_filter = actor_role or actor_name or actor_demographic
    has_extraction_filter = action or severity_min or location_type

    query = "SELECT DISTINCT s.* FROM stories s"
    joins = []
    conditions = ["1=1"]
    params = []

    if has_actor_filter:
        joins.append("JOIN story_actors sa ON s.id = sa.story_id")
        if actor_role:
            conditions.append("sa.role = ?")
            params.append(actor_role)
        if actor_name:
            conditions.append("sa.name LIKE ?")
            params.append(f"%{actor_name}%")
        if actor_demographic:
            conditions.append("sa.demographic LIKE ?")
            params.append(f"%{actor_demographic}%")

    if has_extraction_filter or topic:
        joins.append("LEFT JOIN story_extractions se ON s.id = se.story_id")
        if action:
            conditions.append("se.primary_action LIKE ?")
            params.append(f"%{action}%")
        if severity_min is not None:
            conditions.append("se.severity >= ?")
            params.append(severity_min)
        if topic:
            conditions.append("se.topics LIKE ?")
            params.append(f'%"{topic}"%')
        if location_type:
            conditions.append("se.location_type = ?")
            params.append(location_type)

    # Search: check title, summary, AND search_keywords
    if search:
        # Ensure extraction join exists for keyword search
        se_join = "LEFT JOIN story_extractions se ON s.id = se.story_id"
        if se_join not in joins:
            joins.append(se_join)
        conditions.append("(s.title LIKE ? OR s.summary LIKE ? OR se.search_keywords LIKE ?)")
        term = f"%{search}%"
        params.extend([term, term, term])

    query += " " + " ".join(joins)
    query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY s.scraped_at DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


# --- Narratives ---

def get_active_narratives(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    """Get active narratives sorted by story count."""
    rows = conn.execute(
        """SELECT * FROM narratives
           WHERE status = 'active'
           ORDER BY story_count DESC, last_updated DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_narrative_by_id(conn: sqlite3.Connection, narrative_id: int) -> Optional[dict]:
    """Get a single narrative by ID."""
    row = conn.execute(
        "SELECT * FROM narratives WHERE id = ?", (narrative_id,)
    ).fetchone()
    return dict(row) if row else None


def get_narrative_events(conn: sqlite3.Connection, narrative_id: int) -> list[dict]:
    """Get events linked to a narrative."""
    rows = conn.execute(
        """SELECT e.*, ne.relevance_score FROM events e
           JOIN narrative_events ne ON e.id = ne.event_id
           WHERE ne.narrative_id = ?
           ORDER BY ne.relevance_score DESC, e.last_updated DESC""",
        (narrative_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def upsert_narrative(
    conn: sqlite3.Connection,
    title: str,
    description: str,
    theme_tags: list[str],
    event_ids: list[int],
    narrative_id: Optional[int] = None,
    domain: str = "news",
) -> int:
    """Create or update a narrative and link events."""
    now = datetime.now(timezone.utc).isoformat()

    if narrative_id:
        conn.execute(
            """UPDATE narratives SET
               title = ?, description = ?, theme_tags = ?,
               domain = ?, last_updated = ?, last_analyzed = ?
               WHERE id = ?""",
            (title, description, json.dumps(theme_tags), domain, now, now, narrative_id),
        )
    else:
        cursor = conn.execute(
            """INSERT INTO narratives
               (title, description, theme_tags, domain, first_seen, last_updated,
                event_count, story_count, created_at, last_analyzed)
               VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)""",
            (title, description, json.dumps(theme_tags), domain, now, now,
             len(event_ids), now, now),
        )
        narrative_id = cursor.lastrowid

    # Link events
    for eid in event_ids:
        conn.execute(
            """INSERT OR IGNORE INTO narrative_events
               (narrative_id, event_id, relevance_score, added_at)
               VALUES (?, ?, 1.0, ?)""",
            (narrative_id, eid, now),
        )

    # Compute story_count from linked events (AFTER linking)
    # Use COUNT(DISTINCT) to avoid double-counting stories in multiple events
    story_count = conn.execute(
        """SELECT COUNT(DISTINCT es.story_id)
           FROM narrative_events ne
           JOIN event_stories es ON es.event_id = ne.event_id
           WHERE ne.narrative_id = ?""",
        (narrative_id,),
    ).fetchone()[0]
    event_count = conn.execute(
        "SELECT COUNT(*) FROM narrative_events WHERE narrative_id = ?",
        (narrative_id,),
    ).fetchone()[0]
    conn.execute(
        "UPDATE narratives SET event_count = ?, story_count = ? WHERE id = ?",
        (event_count, story_count, narrative_id),
    )

    conn.commit()
    return narrative_id


# --- Event Registry ---

def get_active_registry_events(conn: sqlite3.Connection, limit: int = 200) -> list[dict]:
    """Get active registry events sorted by recency."""
    rows = conn.execute(
        """SELECT * FROM event_registry
           WHERE status = 'active'
             AND primary_lat IS NOT NULL AND primary_lon IS NOT NULL
           ORDER BY last_matched DESC NULLS LAST, story_count DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_registry_event_by_id(conn: sqlite3.Connection, reg_id: int) -> Optional[dict]:
    """Get a single registry event."""
    row = conn.execute(
        "SELECT * FROM event_registry WHERE id = ?", (reg_id,)
    ).fetchone()
    return dict(row) if row else None


def create_registry_event(
    conn: sqlite3.Connection,
    registry_label: str,
    map_label: str,
    location: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
) -> int:
    """Create a new registry event. Returns the new ID."""
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        """INSERT INTO event_registry
           (registry_label, map_label, status, story_count,
            first_seen, last_matched, primary_location, primary_lat, primary_lon,
            created_at)
           VALUES (?, ?, 'active', 0, ?, ?, ?, ?, ?, ?)""",
        (registry_label, map_label, now, now, location, lat, lon, now),
    )
    conn.commit()
    return cursor.lastrowid


def assign_story_to_registry(
    conn: sqlite3.Connection,
    registry_event_id: int,
    story_id: int,
) -> None:
    """Link a story to a registry event and update counts/location."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT OR IGNORE INTO registry_stories
           (registry_event_id, story_id, added_at) VALUES (?, ?, ?)""",
        (registry_event_id, story_id, now),
    )
    # Update count and last_matched
    count = conn.execute(
        "SELECT COUNT(*) FROM registry_stories WHERE registry_event_id = ?",
        (registry_event_id,),
    ).fetchone()[0]
    conn.execute(
        """UPDATE event_registry SET story_count = ?, last_matched = ?
           WHERE id = ?""",
        (count, now, registry_event_id),
    )
    # Update location: fill if empty, or recalculate every 5 stories
    reg = conn.execute(
        "SELECT primary_lat, story_count FROM event_registry WHERE id = ?",
        (registry_event_id,),
    ).fetchone()
    if reg:
        should_recalc = reg["primary_lat"] is None or (count >= 3 and count % 5 == 0)
        if should_recalc:
            if count >= 3:
                # Recalculate from median of all stories in this registry event
                coord_rows = conn.execute(
                    """SELECT s.lat, s.lon, s.location_name FROM stories s
                       JOIN registry_stories rs ON s.id = rs.story_id
                       WHERE rs.registry_event_id = ? AND s.lat IS NOT NULL""",
                    (registry_event_id,),
                ).fetchall()
                if len(coord_rows) >= 2:
                    lats = sorted(r["lat"] for r in coord_rows)
                    lons = sorted(r["lon"] for r in coord_rows)
                    new_lat = lats[len(lats) // 2]
                    new_lon = lons[len(lons) // 2]
                    loc_counts = {}
                    for r in coord_rows:
                        name = r["location_name"]
                        if name:
                            loc_counts[name] = loc_counts.get(name, 0) + 1
                    new_location = max(loc_counts, key=loc_counts.get) if loc_counts else None
                    conn.execute(
                        """UPDATE event_registry SET
                           primary_location = COALESCE(?, primary_location),
                           primary_lat = ?, primary_lon = ?
                           WHERE id = ?""",
                        (new_location, new_lat, new_lon, registry_event_id),
                    )
            else:
                # Few stories — use this story's location
                story = conn.execute(
                    "SELECT location_name, lat, lon FROM stories WHERE id = ?",
                    (story_id,),
                ).fetchone()
                if story and story["lat"] is not None:
                    conn.execute(
                        """UPDATE event_registry SET
                           primary_location = ?, primary_lat = ?, primary_lon = ?
                           WHERE id = ?""",
                        (story["location_name"], story["lat"], story["lon"],
                         registry_event_id),
                    )
    conn.commit()


def update_registry_event(
    conn: sqlite3.Connection,
    reg_id: int,
    registry_label: Optional[str] = None,
    map_label: Optional[str] = None,
    status: Optional[str] = None,
) -> None:
    """Update a registry event's label or status."""
    updates = []
    params = []
    if registry_label is not None:
        updates.append("registry_label = ?")
        params.append(registry_label)
    if map_label is not None:
        updates.append("map_label = ?")
        params.append(map_label)
    if status is not None:
        updates.append("status = ?")
        params.append(status)
        if status == "retired":
            updates.append("retired_at = ?")
            params.append(datetime.now(timezone.utc).isoformat())
    if not updates:
        return
    params.append(reg_id)
    conn.execute(
        f"UPDATE event_registry SET {', '.join(updates)} WHERE id = ?",
        params,
    )
    conn.commit()


def merge_registry_events(
    conn: sqlite3.Connection,
    keep_id: int,
    merge_id: int,
) -> None:
    """Merge one registry event into another. Reassigns all stories."""
    conn.execute(
        """UPDATE OR IGNORE registry_stories SET registry_event_id = ?
           WHERE registry_event_id = ?""",
        (keep_id, merge_id),
    )
    # Delete any that couldn't be moved (duplicate story_id)
    conn.execute(
        "DELETE FROM registry_stories WHERE registry_event_id = ?",
        (merge_id,),
    )
    # Recount
    count = conn.execute(
        "SELECT COUNT(*) FROM registry_stories WHERE registry_event_id = ?",
        (keep_id,),
    ).fetchone()[0]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE event_registry SET story_count = ?, last_matched = ? WHERE id = ?",
        (count, now, keep_id),
    )
    conn.execute(
        "UPDATE event_registry SET status = 'merged', retired_at = ? WHERE id = ?",
        (now, merge_id),
    )
    conn.commit()


# ==================== WIKIPEDIA EVENTS ====================

def get_active_wiki_events(conn: sqlite3.Connection, limit: int = 300) -> list[dict]:
    """Get active wiki events sorted by recency."""
    rows = conn.execute(
        """SELECT * FROM wiki_events
           WHERE status = 'active'
           ORDER BY last_matched DESC NULLS LAST, story_count DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_recent_event_signatures(conn: sqlite3.Connection, limit: int = 200) -> list[dict]:
    """Get the most-used event signatures from recent active events.

    Returns signatures with 2+ stories, ordered by story count descending.
    These are shown to the LLM so it can reuse existing signatures
    instead of generating new variations of the same event.
    """
    rows = conn.execute(
        """SELECT se.event_signature, COUNT(DISTINCT se.story_id) as story_count,
                  e.title as event_title
           FROM story_extractions se
           JOIN event_stories es ON es.story_id = se.story_id
           JOIN events e ON e.id = es.event_id
           WHERE e.status IN ('active', 'emerging')
             AND se.event_signature <> ''
             AND e.last_updated > datetime('now', '-7 days')
           GROUP BY se.event_signature
           HAVING COUNT(DISTINCT se.story_id) >= 2
           ORDER BY COUNT(DISTINCT se.story_id) DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_or_create_wiki_event(conn: sqlite3.Connection, article_title: str) -> int:
    """Get existing wiki event by article title, or create it. Returns the ID."""
    row = conn.execute(
        "SELECT id FROM wiki_events WHERE article_title = ?",
        (article_title,),
    ).fetchone()
    if row:
        return row["id"]
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        """INSERT INTO wiki_events
           (article_title, display_title, status, story_count,
            first_seen, last_matched, created_at)
           VALUES (?, ?, 'active', 0, ?, ?, ?)""",
        (article_title, article_title, now, now, now),
    )
    conn.commit()
    return cursor.lastrowid


def assign_story_to_wiki_event(
    conn: sqlite3.Connection,
    story_id: int,
    wiki_event_id: int,
) -> None:
    """Link a story to a wiki event and update counts."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT OR IGNORE INTO story_wiki_events
           (story_id, wiki_event_id, added_at) VALUES (?, ?, ?)""",
        (story_id, wiki_event_id, now),
    )
    count = conn.execute(
        "SELECT COUNT(*) FROM story_wiki_events WHERE wiki_event_id = ?",
        (wiki_event_id,),
    ).fetchone()[0]
    conn.execute(
        "UPDATE wiki_events SET story_count = ?, last_matched = ? WHERE id = ?",
        (count, now, wiki_event_id),
    )
    conn.commit()


def get_story_wiki_events(conn: sqlite3.Connection, story_id: int) -> list[dict]:
    """Get all wiki events linked to a story."""
    rows = conn.execute(
        """SELECT w.* FROM wiki_events w
           JOIN story_wiki_events sw ON sw.wiki_event_id = w.id
           WHERE sw.story_id = ?""",
        (story_id,),
    ).fetchall()
    return [dict(r) for r in rows]
