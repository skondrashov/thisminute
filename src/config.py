"""Configuration for thisminute."""

import os
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "thisminute.db"
STATIC_DIR = PROJECT_ROOT / "static"

# Ensure data dir exists
DATA_DIR.mkdir(exist_ok=True)

# Scraper settings
SCRAPE_INTERVAL_SECONDS = 15 * 60  # 15 minutes
REQUEST_TIMEOUT = 30

# RSS Feeds — diverse sources for broad concept coverage
# Each feed has: url, source (display name), tags (list of category tags).
# Tags: news, sports, entertainment, positive, tech, science, business, health
# A feed can have multiple tags. Tags are exposed via /api/feed-tags for frontend filtering.
FEEDS = [
    # === WORLD NEWS ===
    {"url": "https://feeds.bbci.co.uk/news/world/rss.xml", "source": "BBC World", "tags": ["news"]},
    {"url": "https://feeds.bbci.co.uk/news/rss.xml", "source": "BBC Top", "tags": ["news"]},
    {"url": "https://www.aljazeera.com/xml/rss/all.xml", "source": "Al Jazeera", "tags": ["news"]},
    {"url": "https://feeds.npr.org/1001/rss.xml", "source": "NPR", "tags": ["news"]},
    {"url": "https://www.theguardian.com/world/rss", "source": "Guardian World", "tags": ["news"]},
    {"url": "http://rss.cnn.com/rss/edition_world.rss", "source": "CNN", "tags": ["news"]},

    # === WIRE SERVICES / US PAPERS ===
    {"url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "source": "NYT World", "tags": ["news"]},
    {"url": "https://rss.nytimes.com/services/xml/rss/nyt/US.xml", "source": "NYT US", "tags": ["news"]},
    {"url": "https://feeds.washingtonpost.com/rss/world", "source": "Washington Post", "tags": ["news"]},

    # === INTERNATIONAL PERSPECTIVES ===
    {"url": "https://www.abc.net.au/news/feed/2942460/rss.xml", "source": "ABC Australia", "tags": ["news"]},
    {"url": "https://www.france24.com/en/rss", "source": "France 24", "tags": ["news"]},
    {"url": "https://rss.dw.com/rdf/rss-en-all", "source": "DW", "tags": ["news"]},
    {"url": "https://www.japantimes.co.jp/feed/", "source": "Japan Times", "tags": ["news"]},
    {"url": "https://www.rt.com/rss/news/", "source": "RT", "tags": ["news"]},
    {"url": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms", "source": "Times of India", "tags": ["news"]},
    {"url": "https://www.thehindu.com/news/feeder/default.rss", "source": "The Hindu", "tags": ["news"]},
    {"url": "https://africasacountry.com/feed", "source": "Africa Is a Country", "tags": ["news"]},
    {"url": "https://www.irishtimes.com/cmlink/news-1.1319192", "source": "Irish Times", "tags": ["news"]},
    {"url": "https://www.jpost.com/rss/rssfeedsfrontpage.aspx", "source": "Jerusalem Post", "tags": ["news"]},
    # Al Arabiya RSS removed - malformed XML

    # === EAST & SOUTHEAST ASIA ===
    {"url": "https://www.scmp.com/rss/91/feed", "source": "South China Morning Post", "tags": ["news"]},
    # NHK World and Korea Herald removed - malformed XML
    {"url": "https://www.straitstimes.com/news/asia/rss.xml", "source": "Straits Times", "tags": ["news"]},
    {"url": "https://www.bangkokpost.com/rss/data/topstories.xml", "source": "Bangkok Post", "tags": ["news"]},

    # === AFRICA ===
    {"url": "https://www.dailymaverick.co.za/dmrss/", "source": "Daily Maverick", "tags": ["news"]},
    # East African removed - malformed XML

    # === LATIN AMERICA ===
    {"url": "https://en.mercopress.com/rss", "source": "MercoPress", "tags": ["news"]},

    # === REGIONAL ===
    {"url": "https://www.theguardian.com/us-news/rss", "source": "Guardian US", "tags": ["news"]},
    {"url": "https://www.theguardian.com/uk-news/rss", "source": "Guardian UK", "tags": ["news"]},
    {"url": "https://feeds.bbci.co.uk/news/world/africa/rss.xml", "source": "BBC Africa", "tags": ["news"]},
    {"url": "https://feeds.bbci.co.uk/news/world/asia/rss.xml", "source": "BBC Asia", "tags": ["news"]},
    {"url": "https://feeds.bbci.co.uk/news/world/latin_america/rss.xml", "source": "BBC Latin America", "tags": ["news"]},
    {"url": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml", "source": "BBC Middle East", "tags": ["news"]},

    # === AFRICA ===
    {"url": "https://www.jeuneafrique.com/feed/", "source": "Jeune Afrique", "tags": ["news"], "lang": "fr"},
    {"url": "https://punchng.com/feed/", "source": "Punch Nigeria", "tags": ["news"]},
    {"url": "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf", "source": "AllAfrica", "tags": ["news"]},
    # Nation Africa — 403 blocks scrapers, removed 2026-03-16

    # === CAUCASUS & CENTRAL ASIA ===
    {"url": "https://oc-media.org/feed/", "source": "OC Media", "tags": ["news"]},
    {"url": "https://astanatimes.com/feed/", "source": "Astana Times", "tags": ["news"]},

    # === LATIN AMERICA ===
    {"url": "https://www.prensalibre.com/feed/", "source": "Prensa Libre", "tags": ["news"], "lang": "es"},
    # El Universal (MX) — no public RSS, removed 2026-03-16
    # El Tiempo (CO) — no public RSS, removed 2026-03-16

    # === ASIA-PACIFIC & CARIBBEAN ===
    {"url": "https://en.yna.co.kr/RSS/news.xml", "source": "Yonhap", "tags": ["news"]},
    {"url": "https://www.rappler.com/feed/", "source": "Rappler", "tags": ["news"]},
    {"url": "https://www.jamaicaobserver.com/feed/", "source": "Jamaica Observer", "tags": ["news"]},

    # === SCIENCE & ENVIRONMENT ===
    {"url": "https://www.theguardian.com/science/rss", "source": "Guardian Science", "tags": ["science"]},
    {"url": "https://www.theguardian.com/environment/rss", "source": "Guardian Env", "tags": ["science"]},
    {"url": "https://www.sciencedaily.com/rss/all.xml", "source": "ScienceDaily", "tags": ["science"]},
    {"url": "https://phys.org/rss-feed/", "source": "Phys.org", "tags": ["science"]},
    {"url": "https://www.space.com/feeds/all", "source": "Space.com", "tags": ["science"]},
    # Preprint servers (added 2026-03-14, all verified returning valid RSS/RDF)
    {"url": "https://arxiv.org/rss/cs.AI", "source": "arXiv AI", "tags": ["science", "tech"]},
    {"url": "https://arxiv.org/rss/cs", "source": "arXiv CS", "tags": ["science", "tech"]},
    {"url": "https://connect.biorxiv.org/biorxiv_xml.php?subject=all", "source": "bioRxiv", "tags": ["science", "health"]},
    {"url": "https://connect.medrxiv.org/medrxiv_xml.php?subject=all", "source": "medRxiv", "tags": ["science", "health"]},

    # === TECHNOLOGY ===
    {"url": "https://feeds.bbci.co.uk/news/technology/rss.xml", "source": "BBC Tech", "tags": ["tech"]},
    {"url": "https://www.theguardian.com/technology/rss", "source": "Guardian Tech", "tags": ["tech"]},
    {"url": "https://feeds.arstechnica.com/arstechnica/index", "source": "Ars Technica", "tags": ["tech"]},
    {"url": "https://www.wired.com/feed/rss", "source": "Wired", "tags": ["tech"]},
    {"url": "https://hnrss.org/newest?points=100", "source": "Hacker News", "tags": ["tech"]},
    {"url": "https://techcrunch.com/feed/", "source": "TechCrunch", "tags": ["tech"]},
    {"url": "https://www.theverge.com/rss/index.xml", "source": "The Verge", "tags": ["tech"]},

    # === HEALTH ===
    {"url": "https://feeds.bbci.co.uk/news/health/rss.xml", "source": "BBC Health", "tags": ["health"]},

    # === BUSINESS & ECONOMY ===
    {"url": "https://feeds.bbci.co.uk/news/business/rss.xml", "source": "BBC Business", "tags": ["business"]},
    {"url": "https://www.theguardian.com/business/rss", "source": "Guardian Business", "tags": ["business"]},
    {"url": "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml", "source": "NYT Business", "tags": ["business"]},
    {"url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "source": "CoinDesk", "tags": ["business", "tech"]},
    {"url": "https://decrypt.co/feed", "source": "Decrypt", "tags": ["business", "tech"]},

    # === SPORTS ===
    {"url": "https://feeds.bbci.co.uk/sport/rss.xml", "source": "BBC Sport", "tags": ["sports"]},
    {"url": "https://www.theguardian.com/sport/rss", "source": "Guardian Sport", "tags": ["sports"]},
    {"url": "https://rss.nytimes.com/services/xml/rss/nyt/Sports.xml", "source": "NYT Sports", "tags": ["sports"]},
    # Dedicated sports feeds (added 2026-03-11, all verified returning valid RSS)
    {"url": "https://www.espn.com/espn/rss/news", "source": "ESPN", "tags": ["sports"]},
    {"url": "https://www.espn.com/espn/rss/nfl/news", "source": "ESPN NFL", "tags": ["sports"]},
    {"url": "https://www.espn.com/espn/rss/nba/news", "source": "ESPN NBA", "tags": ["sports"]},
    {"url": "https://www.espn.com/espn/rss/mlb/news", "source": "ESPN MLB", "tags": ["sports"]},
    {"url": "https://www.espn.com/espn/rss/nhl/news", "source": "ESPN NHL", "tags": ["sports"]},
    {"url": "https://www.espn.com/espn/rss/ncf/news", "source": "ESPN College Football", "tags": ["sports"]},
    {"url": "https://www.espn.com/espn/rss/ncb/news", "source": "ESPN College Basketball", "tags": ["sports"]},
    {"url": "https://www.espn.com/espn/rss/soccer/news", "source": "ESPN Soccer", "tags": ["sports"]},
    {"url": "https://www.espn.com/espn/rss/mma/news", "source": "ESPN MMA", "tags": ["sports"]},
    {"url": "https://www.espn.com/espn/rss/rpm/news", "source": "ESPN Racing", "tags": ["sports"]},
    {"url": "https://www.espn.com/espn/rss/golf/news", "source": "ESPN Golf", "tags": ["sports"]},
    {"url": "https://www.espn.com/espn/rss/tennis/news", "source": "ESPN Tennis", "tags": ["sports"]},
    {"url": "https://www.espncricinfo.com/rss/content/story/feeds/0.xml", "source": "ESPNcricinfo", "tags": ["sports"]},
    {"url": "https://www.skysports.com/rss/12040", "source": "Sky Sports", "tags": ["sports"]},
    {"url": "https://sportstar.thehindu.com/feeder/default.rss", "source": "Sportstar", "tags": ["sports"]},
    {"url": "https://www.autosport.com/rss/feed/all", "source": "Autosport", "tags": ["sports"]},
    {"url": "https://www.rugbyworld.com/feed", "source": "Rugby World", "tags": ["sports"]},
    # Dead feeds investigated but not added (2026-03-11):
    # Goal.com — 404, Sports Illustrated — 404, The Athletic — 404, Cricbuzz — 404

    # === ENTERTAINMENT & CULTURE ===
    {"url": "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml", "source": "BBC Entertainment", "tags": ["entertainment"]},
    {"url": "https://www.theguardian.com/culture/rss", "source": "Guardian Culture", "tags": ["entertainment"]},
    {"url": "https://www.theguardian.com/music/rss", "source": "Guardian Music", "tags": ["entertainment"]},
    {"url": "https://www.theguardian.com/film/rss", "source": "Guardian Film", "tags": ["entertainment"]},
    {"url": "https://rss.nytimes.com/services/xml/rss/nyt/Arts.xml", "source": "NYT Arts", "tags": ["entertainment"]},
    {"url": "https://feeds.npr.org/1032/rss.xml", "source": "NPR Books", "tags": ["entertainment"]},
    # Dedicated entertainment feeds (added 2026-03-11, all verified returning valid RSS)
    {"url": "https://variety.com/feed/", "source": "Variety", "tags": ["entertainment"]},
    {"url": "https://www.hollywoodreporter.com/feed/", "source": "Hollywood Reporter", "tags": ["entertainment"]},
    {"url": "https://deadline.com/feed/", "source": "Deadline", "tags": ["entertainment"]},
    {"url": "https://www.rollingstone.com/feed/", "source": "Rolling Stone", "tags": ["entertainment"]},
    {"url": "https://www.billboard.com/feed/", "source": "Billboard", "tags": ["entertainment"]},
    {"url": "https://pitchfork.com/feed/feed-news/rss", "source": "Pitchfork", "tags": ["entertainment"]},
    {"url": "https://www.nme.com/feed", "source": "NME", "tags": ["entertainment"]},
    {"url": "https://www.soompi.com/feed", "source": "Soompi", "tags": ["entertainment"]},
    {"url": "https://www.bollywoodhungama.com/feed/", "source": "Bollywood Hungama", "tags": ["entertainment"]},
    {"url": "https://feeds.ign.com/ign/all", "source": "IGN", "tags": ["entertainment", "tech"]},
    # Dead feeds investigated but not added (2026-03-11):
    # Entertainment Weekly (ew.com/feed/) — 404

    # === CURIOUS / ODDITIES ===
    {"url": "https://www.atlasobscura.com/feeds/latest", "source": "Atlas Obscura", "tags": ["positive", "entertainment"]},
    {"url": "https://www.odditycentral.com/feed", "source": "Oddity Central", "tags": ["positive", "entertainment"]},

    # === POSITIVE / UPLIFTING ===
    {"url": "https://www.goodnewsnetwork.org/feed/", "source": "Good News Network", "tags": ["positive"]},
    {"url": "https://www.positive.news/feed/", "source": "Positive News", "tags": ["positive"]},
    {"url": "https://reasonstobecheerful.world/feed/", "source": "Reasons to be Cheerful", "tags": ["positive"]},
    # Euronews Good — consistently malformed XML, disabled 2026-03-12
    # {"url": "https://www.euronews.com/rss?level=theme&name=my-europe", "source": "Euronews Good", "tags": ["positive"]},
    {"url": "https://thehappybroadcast.com/rss", "source": "Happy Broadcast", "tags": ["positive"]},
    {"url": "https://www.vox.com/rss/future-perfect/index.xml", "source": "Vox Future Perfect", "tags": ["positive"]},
]

# Build source-name -> tags lookup from FEEDS config.
# Used by /api/feed-tags endpoint and internal tag queries.
FEED_TAG_MAP = {}
for _feed in FEEDS:
    FEED_TAG_MAP[_feed["source"]] = _feed.get("tags", [])

# GDELT sampling — controls how many GDELT stories are ingested per cycle.
# Set to 1.0 to ingest all, 0.0 to disable GDELT entirely.
# At 0.003 (~0.3%), GDELT ingests ~1,700/day (raw volume ~643K/day as of 2026-03).
GDELT_SAMPLE_RATE = float(os.environ.get("GDELT_SAMPLE_RATE", "0.003"))

# USGS earthquake feeds
USGS_SIGNIFICANT_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_hour.geojson"
USGS_4_5_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson"
USGS_MIN_MAGNITUDE = float(os.environ.get("USGS_MIN_MAGNITUDE", "4.5"))

# NOAA weather alerts
NOAA_ALERTS_URL = "https://api.weather.gov/alerts/active?status=actual&message_type=alert"
NOAA_MAX_ALERTS = int(os.environ.get("NOAA_MAX_ALERTS", "150"))

# NASA EONET (Earth Observatory Natural Event Tracker)
EONET_URL = "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=100"

# GDACS (Global Disaster Alert and Coordination System)
GDACS_GEOJSON_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/MAP"
GDACS_RSS_URL = "https://www.gdacs.org/xml/rss.xml"

# ReliefWeb (UN OCHA)
RELIEFWEB_URL = ("https://api.reliefweb.int/v1/reports?appname=thisminute.org"
                 "&filter[field]=date.created&filter[value][from]=now-1d&limit=50"
                 "&fields[include][]=title&fields[include][]=url&fields[include][]=body"
                 "&fields[include][]=country&fields[include][]=primary_country"
                 "&fields[include][]=disaster&fields[include][]=date"
                 "&fields[include][]=source")

# WHO Disease Outbreak News
WHO_DON_URL = "https://www.who.int/feeds/entity/don/en/rss.xml"

# US State Department Travel Advisories
TRAVEL_ADVISORY_URL = "https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories.xml"

# OpenAQ air quality
OPENAQ_API_KEY = os.environ.get("OPENAQ_API_KEY", "")
OPENAQ_URL = "https://api.openaq.org/v2/latest?limit=100&order_by=lastUpdated&sort_order=desc&has_geo=true"

# NASA FIRMS (Fire Information for Resource Management System)
FIRMS_API_KEY = os.environ.get("FIRMS_API_KEY", "")
FIRMS_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/VIIRS_SNPP_NRT/world/1"
FIRMS_MAX_ROWS = int(os.environ.get("FIRMS_MAX_ROWS", "5000"))
FIRMS_MAX_BYTES = int(os.environ.get("FIRMS_MAX_BYTES", str(10 * 1024 * 1024)))  # 10 MB

# Launch Library 2 (space launches)
LAUNCHES_UPCOMING_URL = "https://ll.thespacedevs.com/2.3.0/launches/upcoming/?format=json&limit=25"
LAUNCHES_PREVIOUS_URL = "https://ll.thespacedevs.com/2.3.0/launches/previous/?format=json&limit=10"
LAUNCHES_CACHE_SECONDS = int(os.environ.get("LAUNCHES_CACHE_SECONDS", "2700"))  # 45 min

# ACLED (Armed Conflict Location & Event Data)
ACLED_API_KEY = os.environ.get("ACLED_API_KEY", "")
ACLED_EMAIL = os.environ.get("ACLED_EMAIL", "")
ACLED_URL = "https://api.acleddata.com/acled/read"
ACLED_MAX_EVENTS = int(os.environ.get("ACLED_MAX_EVENTS", "200"))

# Meteoalarm (European severe weather alerts)
METEOALARM_BASE_URL = "https://feeds.meteoalarm.org/api/v1/warnings/feeds-{country}"
METEOALARM_CACHE_SECONDS = int(os.environ.get("METEOALARM_CACHE_SECONDS", "900"))  # 15 min
METEOALARM_MAX_ALERTS = int(os.environ.get("METEOALARM_MAX_ALERTS", "200"))
METEOALARM_TIMEOUT = int(os.environ.get("METEOALARM_TIMEOUT", "5"))  # per-request timeout (seconds)
METEOALARM_TOTAL_BUDGET = int(os.environ.get("METEOALARM_TOTAL_BUDGET", "60"))  # total time budget (seconds)
# High-population European countries to fetch (keeps API calls manageable)
METEOALARM_COUNTRIES = [
    "germany", "france", "italy", "spain", "united-kingdom",
    "poland", "netherlands", "belgium", "austria", "switzerland",
    "sweden", "norway", "finland", "denmark", "portugal",
    "czech-republic", "romania", "hungary", "greece", "ireland",
]

# JMA (Japan Meteorological Agency) weather warnings
JMA_WARNINGS_URL = "https://www.jma.go.jp/bosai/warning/data/warning/map.json"
JMA_AREA_URL = "https://www.jma.go.jp/bosai/common/const/area.json"
JMA_CACHE_SECONDS = int(os.environ.get("JMA_CACHE_SECONDS", "900"))  # 15 min
JMA_MAX_ALERTS = int(os.environ.get("JMA_MAX_ALERTS", "100"))
JMA_TIMEOUT = int(os.environ.get("JMA_TIMEOUT", "10"))  # per-request timeout (seconds)

# Data source toggles — set to False to disable ingestion.
# Can be overridden by environment variables: SOURCE_RSS_ENABLED=false, etc.
SOURCE_ENABLED = {
    "rss": os.environ.get("SOURCE_RSS_ENABLED", "true").lower() != "false",
    "gdelt": os.environ.get("SOURCE_GDELT_ENABLED", "true").lower() != "false",
    "usgs": os.environ.get("SOURCE_USGS_ENABLED", "true").lower() != "false",
    "noaa": os.environ.get("SOURCE_NOAA_ENABLED", "true").lower() != "false",
    "eonet": os.environ.get("SOURCE_EONET_ENABLED", "true").lower() != "false",
    "gdacs": os.environ.get("SOURCE_GDACS_ENABLED", "true").lower() != "false",
    "reliefweb": os.environ.get("SOURCE_RELIEFWEB_ENABLED", "true").lower() != "false",
    "who": os.environ.get("SOURCE_WHO_ENABLED", "true").lower() != "false",
    "launches": os.environ.get("SOURCE_LAUNCHES_ENABLED", "true").lower() != "false",
    "openaq": os.environ.get("SOURCE_OPENAQ_ENABLED", "true").lower() != "false",
    "travel": os.environ.get("SOURCE_TRAVEL_ENABLED", "true").lower() != "false",
    "firms": os.environ.get("SOURCE_FIRMS_ENABLED", "true").lower() != "false",
    "meteoalarm": os.environ.get("SOURCE_METEOALARM_ENABLED", "true").lower() != "false",
    "acled": os.environ.get("SOURCE_ACLED_ENABLED", "true").lower() != "false",
    "jma": os.environ.get("SOURCE_JMA_ENABLED", "true").lower() != "false",
    "user_feeds": os.environ.get("SOURCE_USER_FEEDS_ENABLED", "true").lower() != "false",
}

# Geocoder settings
NOMINATIM_USER_AGENT = "thisminute-news-map/1.0"
GEOCODE_MIN_DELAY = 1.0  # seconds between Nominatim requests

# Frontend polling
FRONTEND_POLL_SECONDS = 60

# User-added RSS feeds
USER_FEED_MAX = int(os.environ.get("USER_FEED_MAX", "20"))
USER_FEED_MAX_STORIES = int(os.environ.get("USER_FEED_MAX_STORIES", "50"))
USER_FEED_TOTAL_MAX_STORIES = int(os.environ.get("USER_FEED_TOTAL_MAX_STORIES", "500"))

# Per-source story caps — prevents academic preprint feeds from dominating
# science/tech/health worlds. These are interesting for search but shouldn't
# flood the map with ungeocodable paper titles.
ARXIV_MAX_PER_CYCLE = int(os.environ.get("ARXIV_MAX_PER_CYCLE", "20"))
BIORXIV_MAX_PER_CYCLE = int(os.environ.get("BIORXIV_MAX_PER_CYCLE", "20"))

# LLM analysis (optional)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
