"""RSS feed scraper with conditional GET support."""

import logging
from datetime import datetime, timezone
from typing import Optional
import re

import feedparser

from .config import FEEDS, REQUEST_TIMEOUT, ARXIV_MAX_PER_CYCLE, BIORXIV_MAX_PER_CYCLE
from .database import get_connection, get_feed_state, update_feed_state

logger = logging.getLogger(__name__)

# Per-source story caps (source display name -> max stories per cycle)
_SOURCE_CAPS = {
    "arXiv AI": ARXIV_MAX_PER_CYCLE,
    "arXiv CS": ARXIV_MAX_PER_CYCLE,
    "bioRxiv": BIORXIV_MAX_PER_CYCLE,
    "medRxiv": BIORXIV_MAX_PER_CYCLE,
}

# Strip HTML tags from summaries
_TAG_RE = re.compile(r"<[^>]+>")

# Extract first <img src="..."> from HTML content
_IMG_SRC_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']|<img[^>]+src=([^\s>]+)', re.IGNORECASE)


def _fix_encoding(text: str) -> str:
    """Fix common mojibake from RSS feeds (UTF-8 decoded as latin-1/cp1252)."""
    if not text:
        return text
    # Try to detect and fix double-encoded UTF-8
    try:
        # If it looks like mojibake, try re-encoding
        if "\u00e2\u0080" in text or "\u00c2" in text:
            fixed = text.encode("cp1252").decode("utf-8")
            return fixed
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass
    return text


def _clean_html(text: str) -> str:
    """Remove HTML tags, fix encoding, and collapse whitespace."""
    if not text:
        return ""
    text = _TAG_RE.sub(" ", text)
    text = _fix_encoding(text)
    return " ".join(text.split()).strip()


def _parse_date(entry: dict) -> Optional[str]:
    """Extract published date as ISO string."""
    for field in ("published_parsed", "updated_parsed"):
        t = entry.get(field)
        if t:
            try:
                dt = datetime(*t[:6], tzinfo=timezone.utc)
                return dt.isoformat()
            except (ValueError, TypeError):
                continue
    return None


def _extract_image_url(entry: dict) -> Optional[str]:
    """Extract the best image URL from an RSS entry.

    Checks media:content, media:thumbnail, enclosures, and og:image-style links.
    """
    # media:content (most common for news)
    media = entry.get("media_content", [])
    for m in media:
        url = m.get("url", "")
        mtype = m.get("type", "")
        if url and ("image" in mtype or url.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))):
            return url

    # media:thumbnail
    thumbs = entry.get("media_thumbnail", [])
    if thumbs:
        url = thumbs[0].get("url")
        if url:
            return url

    # Enclosures (image type)
    for enc in entry.get("enclosures", []):
        if "image" in enc.get("type", ""):
            return enc.get("href") or enc.get("url")

    # Links with image type
    for link in entry.get("links", []):
        if "image" in link.get("type", ""):
            return link.get("href")

    # Fallback: extract first <img src> from content/summary HTML
    for field in ("content", "summary_detail"):
        raw = entry.get(field)
        if raw:
            html = raw[0].get("value", "") if isinstance(raw, list) else getattr(raw, "value", str(raw))
            if html:
                match = _IMG_SRC_RE.search(html)
                if match:
                    url = match.group(1) or match.group(2)
                    # Skip tiny tracking pixels and icons
                    if url and not any(skip in url.lower() for skip in ("pixel", "tracking", "1x1", "spacer", "icon")):
                        return url

    return None


def scrape_feed(feed_config: dict) -> list[dict]:
    """Scrape a single RSS feed. Returns list of story dicts.

    Uses conditional GET (ETag/Last-Modified) to avoid re-downloading unchanged feeds.
    """
    url = feed_config["url"]
    source = feed_config["source"]

    conn = get_connection()
    state = get_feed_state(conn, url)

    # Build conditional GET headers
    kwargs = {}
    if state:
        if state.get("last_etag"):
            kwargs["etag"] = state["last_etag"]
        if state.get("last_modified"):
            kwargs["modified"] = state["last_modified"]

    try:
        feed = feedparser.parse(url, **kwargs)
    except Exception as e:
        logger.error("Failed to fetch %s: %s", url, e)
        conn.close()
        return []

    # Check for 304 Not Modified
    status = feed.get("status", 200)
    if status == 304:
        logger.info("Feed %s not modified (304)", source)
        update_feed_state(conn, url, state.get("last_etag"), state.get("last_modified"))
        conn.close()
        return []

    if feed.bozo and not feed.entries:
        logger.warning("Feed %s is malformed: %s", source, feed.bozo_exception)
        conn.close()
        return []

    # Save feed state for next conditional GET
    new_etag = feed.get("etag")
    new_modified = feed.get("modified")
    update_feed_state(conn, url, new_etag, new_modified)
    conn.close()

    stories = []
    for entry in feed.entries:
        link = entry.get("link", "")
        if not link:
            continue

        title = _fix_encoding(entry.get("title", "")).strip()
        if not title:
            continue

        summary = _clean_html(entry.get("summary", "") or entry.get("description", ""))
        # Truncate long summaries
        if len(summary) > 500:
            summary = summary[:497] + "..."

        stories.append({
            "title": title,
            "url": link,
            "summary": summary,
            "source": source,
            "published_at": _parse_date(entry),
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "image_url": _extract_image_url(entry),
        })

    # Enforce per-source caps for high-volume preprint feeds
    cap = _SOURCE_CAPS.get(source)
    if cap and len(stories) > cap:
        logger.info("Capping %s from %d to %d stories", source, len(stories), cap)
        stories = stories[:cap]

    logger.info("Scraped %d entries from %s", len(stories), source)
    return stories


def scrape_all_feeds() -> list[dict]:
    """Scrape all configured feeds. Returns combined list of stories."""
    all_stories = []
    for feed_config in FEEDS:
        stories = scrape_feed(feed_config)
        all_stories.extend(stories)
    logger.info("Total scraped: %d stories from %d feeds", len(all_stories), len(FEEDS))
    return all_stories
