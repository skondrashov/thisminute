"""GDELT GKG 2.0 bulk integration for supplemental news scraping.

Downloads the latest 15-minute GKG (Global Knowledge Graph) file, which contains
~900 articles with pre-extracted themes, geocoded locations, people, organizations,
and tone/sentiment. One 3-4MB ZIP download replaces hundreds of API calls.
"""

import html
import io
import logging
import random
import re
import zipfile
import urllib.request
from datetime import datetime, timezone
from typing import Optional

from .config import REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

GDELT_LASTUPDATE_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"

# Hard cap per 15-minute cycle. Prevents volume spikes regardless of sample rate.
# At 96 cycles/day, 50 * 96 = 4,800/day worst case -- well within pipeline capacity.
MAX_GDELT_PER_CYCLE = 50

# Domains we already scrape via RSS — skip these to avoid duplicates
_RSS_DOMAINS = {
    "bbc.co.uk", "bbc.com", "aljazeera.com", "npr.org", "theguardian.com",
    "cnn.com", "nytimes.com", "washingtonpost.com", "abc.net.au",
    "france24.com", "dw.com", "japantimes.co.jp", "rt.com",
    "timesofindia.indiatimes.com", "thehindu.com", "irishtimes.com",
    "jpost.com", "scmp.com", "straitstimes.com", "bangkokpost.com",
    "dailymaverick.co.za", "mercopress.com", "sciencedaily.com",
    "phys.org", "space.com", "arstechnica.com", "wired.com",
    "goodnewsnetwork.org", "positive.news", "euronews.com",
    "vox.com", "africasacountry.com",
    "reasonstobecheerful.world", "thehappybroadcast.com",
}

_KNOWN_SOURCES = {
    "reuters.com": "Reuters",
    "apnews.com": "AP News",
    "afp.com": "AFP",
    "xinhuanet.com": "Xinhua",
    "english.news.cn": "Xinhua",
    "tass.com": "TASS",
    "yna.co.kr": "Yonhap",
    "kyodonews.net": "Kyodo News",
    "aa.com.tr": "Anadolu Agency",
    "bernama.com": "Bernama",
    "pna.gov.ph": "PNA Philippines",
    "dawn.com": "Dawn",
    "nation.africa": "The Nation Africa",
    "allafrica.com": "AllAfrica",
    "middleeasteye.net": "Middle East Eye",
    "haaretz.com": "Haaretz",
    "themoscowtimes.com": "Moscow Times",
    "english.alarabiya.net": "Al Arabiya",
    "channelnewsasia.com": "CNA",
    "livemint.com": "Mint",
    "ndtv.com": "NDTV",
    "globaltimes.cn": "Global Times",
    "efe.com": "EFE",
    "antaranews.com": "Antara",
    "tribune.com.pk": "Express Tribune",
    "geo.tv": "Geo News",
    "news24.com": "News24",
    "monitor.co.ug": "Daily Monitor",
    "standardmedia.co.ke": "The Standard",
    "punch.ng": "The Punch",
    "premiumtimesng.com": "Premium Times",
    "cbc.ca": "CBC",
    "abc.es": "ABC Spain",
    "elpais.com": "El País",
    "lemonde.fr": "Le Monde",
    "spiegel.de": "Der Spiegel",
    "chinadaily.com.cn": "China Daily",
    "koreaherald.com": "Korea Herald",
    "hindustantimes.com": "Hindustan Times",
    "theeastafrican.co.ke": "The East African",
    "dailystar.co.uk": "Daily Star",
    "independent.co.uk": "The Independent",
    "telegraph.co.uk": "The Telegraph",
    "metro.co.uk": "Metro UK",
    "mirror.co.uk": "The Mirror",
    "express.co.uk": "Daily Express",
    "standard.co.uk": "Evening Standard",
    "sky.com": "Sky News",
    "itv.com": "ITV News",
}

# GDELT themes → thisminute concepts mapping
_THEME_TO_CONCEPT = {
    "TERROR": "terrorism",
    "ARMEDCONFLICT": "conflict",
    "UNREST_BELLIGERENT": "conflict",
    "MILITARY": "military",
    "PROTEST": "protest",
    "REFUGEE": "migration",
    "DISPLACEMENT": "migration",
    "ELECTION": "election",
    "GENERAL_GOVERNMENT": "politics",
    "DISASTER_EARTHQUAKE": "disaster",
    "DISASTER_FLOOD": "disaster",
    "DISASTER_FIRE": "disaster",
    "DISASTER_HURRICANE": "disaster",
    "DISASTER_VOLCANO": "disaster",
    "DISASTER_TSUNAMI": "disaster",
    "MANMADE_DISASTER": "disaster",
    "ENV_DEFORESTATION": "environment",
    "ENV_WATERWAYS": "environment",
    "CLIMATE_CHANGE": "climate",
    "GENERAL_HEALTH": "health",
    "DISEASE": "health",
    "EDUCATION": "education",
    "CYBER": "cyber",
    "CRISISLEX": "crisis",
    "HUMAN_RIGHTS": "human rights",
    "NUCLEAR": "nuclear",
}

_TITLE_RE = re.compile(r"<PAGE_TITLE>([^<]+)</PAGE_TITLE>")
_TIMESTAMP_RE = re.compile(r"<PAGE_PRECISEPUBTIMESTAMP>(\d{14})</PAGE_PRECISEPUBTIMESTAMP>")

# Patterns that indicate radio show segments, podcast episodes, or non-news content
_JUNK_TITLE_PATTERNS = [
    re.compile(r"\bFULL SHOW\b", re.IGNORECASE),
    re.compile(r"\bFull\s+\w+\s+Show\b"),  # "Full Jubal Show from..."
    re.compile(r"\bPT\s*[12345]\b.*:"),  # "PT 1:", "PT 2:" — show segments
    re.compile(r"\|\s*\d+\.\d+\s+\w"),  # "| 93.3 The Eagle" station IDs
    re.compile(r"\|\s*(K[A-Z0-9]{2,5}|W[A-Z0-9]{2,5})\b"),  # "| KJ108 FM", "| WJOX"
    re.compile(r"\|\s*\w+\s+(FM|AM)\b"),  # "| KISS FM", "| JAM'N 107"
    re.compile(r"Carroll Broadcasting", re.IGNORECASE),  # GDELT radio syndication
]


def _is_junk_title(title: str) -> bool:
    """Filter out radio show segments and podcast episodes from GDELT."""
    return any(p.search(title) for p in _JUNK_TITLE_PATTERNS)


# Track last downloaded file to avoid re-processing
_last_gkg_url = None


def _domain_to_source(domain: str) -> str:
    """Convert a domain to a readable source name."""
    d = domain.lower().removeprefix("www.")
    if d in _KNOWN_SOURCES:
        return _KNOWN_SOURCES[d]
    name = d.split(".")[0]
    return f"{name.capitalize()} (GDELT)"


def _is_rss_domain(domain: str) -> bool:
    """Check if this domain is already covered by our RSS feeds."""
    d = domain.lower().removeprefix("www.")
    for rss_d in _RSS_DOMAINS:
        if d == rss_d or d.endswith("." + rss_d):
            return True
    return False


def _parse_gkg_timestamp(ts: str) -> Optional[str]:
    """Parse GDELT timestamp (YYYYMMDDHHMMSS) to ISO 8601."""
    if not ts or len(ts) < 14:
        return None
    try:
        dt = datetime.strptime(ts[:14], "%Y%m%d%H%M%S")
        return dt.replace(tzinfo=timezone.utc).isoformat()
    except (ValueError, TypeError):
        return None


def _parse_gkg_location(loc_str: str) -> Optional[dict]:
    """Parse the first usable GKG location entry.

    GKG location format: Type#Name#CountryCode#ADM1#Lat#Lon#FeatureID
    Types: 1=country, 2=US state, 3=US city, 4=world city, 5=world ADM1
    Prefer type 3-5 (specific) over 1-2 (country/state).
    """
    if not loc_str or not loc_str.strip():
        return None

    entries = loc_str.split(";")
    best = None
    best_type = 0

    for entry in entries:
        parts = entry.split("#")
        if len(parts) < 6:
            continue
        try:
            loc_type = int(parts[0])
            name = parts[1].strip()
            lat = float(parts[4]) if parts[4] else None
            lon = float(parts[5]) if parts[5] else None
            if not name or lat is None or lon is None:
                continue
            # Prefer more specific locations
            if loc_type > best_type:
                best_type = loc_type
                best = {"name": name, "lat": lat, "lon": lon}
        except (ValueError, IndexError):
            continue

    return best


def _extract_concepts(themes_str: str) -> list[str]:
    """Map GDELT themes to thisminute concepts."""
    if not themes_str:
        return []
    themes = themes_str.split(";")
    concepts = set()
    for theme in themes:
        theme_upper = theme.strip().upper()
        for prefix, concept in _THEME_TO_CONCEPT.items():
            if theme_upper.startswith(prefix):
                concepts.add(concept)
                break
    return list(concepts)[:5]  # Cap at 5


def _get_latest_gkg_url() -> Optional[str]:
    """Fetch the URL of the latest GKG file from GDELT's lastupdate.txt."""
    try:
        req = urllib.request.Request(
            GDELT_LASTUPDATE_URL,
            headers={"User-Agent": "thisminute-news-map/1.0"}
        )
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            text = resp.read().decode("utf-8")
        for line in text.strip().split("\n"):
            parts = line.strip().split()
            if len(parts) >= 3 and parts[2].endswith(".gkg.csv.zip"):
                return parts[2]
    except Exception as e:
        logger.error("Failed to fetch GDELT lastupdate.txt: %s", e)
    return None


def parse_gkg_csv(raw: str) -> list[dict]:
    """Parse raw GKG CSV text into story dicts.

    Shared by both scrape_gdelt() and the backfill script.
    """
    stories = []
    now = datetime.now(timezone.utc).isoformat()
    seen_urls = set()

    for line in raw.split("\n"):
        if not line.strip():
            continue
        cols = line.split("\t")
        if len(cols) < 27:
            continue

        domain = cols[3].strip()
        url = cols[4].strip()

        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        if _is_rss_domain(domain):
            continue

        title_match = _TITLE_RE.search(cols[26])
        if not title_match:
            continue
        title = html.unescape(title_match.group(1)).strip()
        if not title:
            continue

        if _is_junk_title(title):
            continue

        ts_match = _TIMESTAMP_RE.search(cols[26])
        published_at = _parse_gkg_timestamp(ts_match.group(1)) if ts_match else _parse_gkg_timestamp(cols[1])

        location = _parse_gkg_location(cols[9])
        concepts = _extract_concepts(cols[7])

        story = {
            "title": title,
            "url": url,
            "summary": "",
            "source": _domain_to_source(domain),
            "published_at": published_at,
            "scraped_at": now,
            "origin": "gdelt",
        }

        if location:
            story["location_name"] = location["name"]
            story["lat"] = location["lat"]
            story["lon"] = location["lon"]
            story["geocode_confidence"] = 0.5

        if concepts:
            story["concepts"] = concepts
            story["category"] = concepts[0]

        stories.append(story)

    return stories


def scrape_gdelt() -> list[dict]:
    """Download the latest GDELT GKG file and extract stories.

    Returns list of story dicts compatible with pipeline.process_story(),
    with pre-populated location and concept data from GDELT's extraction.
    """
    global _last_gkg_url

    # Get latest file URL
    gkg_url = _get_latest_gkg_url()
    if not gkg_url:
        return []

    # Skip if we already processed this file
    if gkg_url == _last_gkg_url:
        logger.info("GDELT GKG: already processed %s, skipping", gkg_url.split("/")[-1])
        return []

    # Download and unzip
    try:
        req = urllib.request.Request(
            gkg_url,
            headers={"User-Agent": "thisminute-news-map/1.0"}
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            zip_data = resp.read()
    except Exception as e:
        logger.error("Failed to download GKG file %s: %s", gkg_url, e)
        return []

    try:
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            csv_name = zf.namelist()[0]
            raw = zf.read(csv_name).decode("utf-8", errors="replace")
    except Exception as e:
        logger.error("Failed to unzip GKG file: %s", e)
        return []

    _last_gkg_url = gkg_url

    stories = parse_gkg_csv(raw)

    # Sample GDELT stories to control volume and LLM costs
    from .config import GDELT_SAMPLE_RATE
    if GDELT_SAMPLE_RATE < 1.0 and stories:
        before = len(stories)
        stories = [s for s in stories if random.random() < GDELT_SAMPLE_RATE]
        logger.info("GDELT sampling: %d -> %d stories (rate=%.0f%%)",
                     before, len(stories), GDELT_SAMPLE_RATE * 100)

    # Hard cap: truncate if sampling still yields too many stories
    if len(stories) > MAX_GDELT_PER_CYCLE:
        print("GDELT WARNING: %d stories after sampling exceeds cap of %d, truncating"
              % (len(stories), MAX_GDELT_PER_CYCLE), flush=True)
        random.shuffle(stories)  # Shuffle before truncating for variety
        stories = stories[:MAX_GDELT_PER_CYCLE]

    logger.info("GDELT GKG: %s -> %d stories",
                gkg_url.split("/")[-1], len(stories))
    return stories
