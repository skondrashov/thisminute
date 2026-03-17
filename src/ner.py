"""Location extraction using a gazetteer of countries and major cities.

Uses regex matching against known place names instead of spaCy (which is
incompatible with Python 3.14). For news articles, this approach works well
since locations mentioned are typically well-known places.
"""

import logging
import re
from collections import Counter
from typing import Optional

logger = logging.getLogger(__name__)

# --- Gazetteer: countries and major world cities ---
# These are the locations most likely to appear in world news.

_COUNTRIES = [
    "Afghanistan", "Albania", "Algeria", "Argentina", "Armenia", "Australia",
    "Austria", "Azerbaijan", "Bahrain", "Bangladesh", "Belarus", "Belgium",
    "Bolivia", "Bosnia", "Brazil", "Bulgaria", "Cambodia", "Cameroon", "Canada",
    "Chad", "Chile", "China", "Colombia", "Congo", "Costa Rica", "Croatia",
    "Cuba", "Cyprus", "Czech Republic", "Denmark", "Dominican Republic",
    "Ecuador", "Egypt", "El Salvador", "Estonia", "Ethiopia", "Finland",
    "France", "Georgia", "Germany", "Ghana", "Greece", "Guatemala",
    "Haiti", "Honduras", "Hungary", "Iceland", "India", "Indonesia", "Iran",
    "Iraq", "Ireland", "Israel", "Italy", "Ivory Coast", "Jamaica", "Japan",
    "Jordan", "Kazakhstan", "Kenya", "Kosovo", "Kuwait", "Kyrgyzstan",
    "Latvia", "Lebanon", "Libya", "Lithuania", "Luxembourg",
    "Madagascar", "Malaysia", "Mali", "Malta", "Mexico", "Moldova", "Mongolia",
    "Montenegro", "Morocco", "Mozambique", "Myanmar", "Nepal", "Netherlands",
    "New Zealand", "Nicaragua", "Niger", "Nigeria", "North Korea", "North Macedonia",
    "Norway", "Oman", "Pakistan", "Palestine", "Panama", "Paraguay", "Peru",
    "Philippines", "Poland", "Portugal", "Qatar", "Romania", "Russia", "Rwanda",
    "Saudi Arabia", "Senegal", "Serbia", "Sierra Leone", "Singapore", "Slovakia",
    "Slovenia", "Somalia", "South Africa", "South Korea", "South Sudan", "Spain",
    "Sri Lanka", "Sudan", "Sweden", "Switzerland", "Syria", "Taiwan", "Tajikistan",
    "Tanzania", "Thailand", "Tunisia", "Turkey", "Turkmenistan", "Uganda", "Ukraine",
    "United Arab Emirates", "United Kingdom", "United States", "Uruguay", "Uzbekistan",
    "Venezuela", "Vietnam", "Yemen", "Zambia", "Zimbabwe",
]

_CITIES = [
    "Kabul", "Tirana", "Algiers", "Buenos Aires", "Yerevan", "Sydney", "Melbourne",
    "Vienna", "Baku", "Manama", "Dhaka", "Minsk", "Brussels", "La Paz",
    "Sarajevo", "Brasilia", "Sao Paulo", "Rio de Janeiro", "Sofia", "Phnom Penh",
    "Ottawa", "Toronto", "Montreal", "Vancouver", "Santiago", "Beijing", "Shanghai",
    "Hong Kong", "Bogota", "Kinshasa", "San Jose", "Zagreb", "Havana", "Nicosia",
    "Prague", "Copenhagen", "Quito", "Cairo", "Tallinn", "Addis Ababa", "Helsinki",
    "Paris", "Marseille", "Lyon", "Tbilisi", "Berlin", "Munich", "Frankfurt",
    "Hamburg", "Accra", "Athens", "Port-au-Prince", "Budapest", "Reykjavik",
    "New Delhi", "Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata", "Hyderabad",
    "Jakarta", "Tehran", "Baghdad", "Dublin", "Jerusalem", "Tel Aviv", "Rome",
    "Milan", "Naples", "Tokyo", "Osaka", "Amman", "Nairobi", "Pristina", "Kuwait City",
    "Riga", "Beirut", "Tripoli", "Vilnius", "Luxembourg City",
    "Kuala Lumpur", "Bamako", "Mexico City", "Guadalajara", "Chisinau",
    "Ulaanbaatar", "Podgorica", "Rabat", "Casablanca", "Maputo", "Yangon",
    "Kathmandu", "Amsterdam", "The Hague", "Rotterdam", "Auckland", "Wellington",
    "Managua", "Abuja", "Lagos", "Pyongyang", "Skopje", "Oslo",
    "Muscat", "Islamabad", "Karachi", "Lahore", "Ramallah", "Panama City",
    "Asuncion", "Lima", "Manila", "Warsaw", "Krakow", "Lisbon", "Doha",
    "Bucharest", "Moscow", "St Petersburg", "Saint Petersburg", "Kigali",
    "Riyadh", "Jeddah", "Dakar", "Belgrade", "Freetown", "Bratislava",
    "Ljubljana", "Mogadishu", "Johannesburg", "Cape Town", "Pretoria", "Durban",
    "Seoul", "Busan", "Juba", "Madrid", "Barcelona", "Colombo",
    "Khartoum", "Stockholm", "Gothenburg", "Geneva", "Zurich", "Bern",
    "Damascus", "Aleppo", "Taipei", "Dar es Salaam", "Bangkok",
    "Tunis", "Ankara", "Istanbul", "Ashgabat", "Kampala", "Kyiv", "Kiev",
    "Kharkiv", "Odesa", "Lviv", "Abu Dhabi", "Dubai", "London", "Manchester",
    "Birmingham", "Edinburgh", "Glasgow", "Washington", "New York", "Los Angeles",
    "Chicago", "Houston", "San Francisco", "Boston", "Miami", "Seattle",
    "Denver", "Atlanta", "Philadelphia", "Dallas", "Phoenix",
    "Montevideo", "Tashkent", "Caracas", "Hanoi", "Ho Chi Minh City",
    "Sanaa", "Lusaka", "Harare",
    # More US cities
    "Austin", "San Antonio", "San Diego", "Portland", "Las Vegas",
    "Nashville", "Detroit", "Memphis", "Baltimore", "Milwaukee",
    "Minneapolis", "Charlotte", "Sacramento", "Pittsburgh", "Cincinnati",
    "Orlando", "Tampa", "St Louis", "Cleveland", "New Orleans",
    "Honolulu", "Anchorage",
    # More European cities
    "Toulouse", "Nice", "Bordeaux", "Cologne", "Stuttgart", "Dresden",
    "Antwerp", "Porto", "Valencia", "Seville", "Florence", "Venice",
    "Turin", "Gothenburg", "Malmo",
    # More Asian cities
    "Shenzhen", "Guangzhou", "Chengdu", "Wuhan", "Nanjing",
    "Kabul", "Kandahar", "Herat", "Mosul", "Basra", "Erbil",
    "Donetsk", "Luhansk", "Mariupol", "Zaporizhzhia",
    # More African cities
    "Cairo", "Alexandria", "Addis Ababa", "Mombasa", "Kano",
    # More Latin American cities
    "Havana", "Bogota", "Medellin", "Quito", "Santiago",
    # Regions and areas that appear in news
    "Gaza", "West Bank", "Crimea", "Donbas", "Kashmir", "Tibet", "Xinjiang",
    "Kurdistan", "Catalonia", "Sahel", "Sahara", "Arctic", "Antarctic",
    "Silicon Valley", "Wall Street", "Pentagon", "Hollywood", "Broadway",
    "Capitol Hill", "Downing Street", "Kremlin", "Vatican",
    "Chernobyl", "Fukushima", "Guantanamo",
    # US states (for stories that mention state names)
    "California", "Texas", "Florida", "New York", "Pennsylvania",
    "Ohio", "Georgia", "Michigan", "Illinois", "Virginia",
    "North Carolina", "Arizona", "Nevada", "Colorado", "Oregon",
    "Hawaii", "Alaska",
    # UK regions
    "Scotland", "Wales", "Northern Ireland", "England",
]

# Institutions, venues, and landmarks that are meaningful locations in news
_INSTITUTIONS = [
    # Research
    "MIT", "CERN", "NIH", "CDC", "Stanford", "Harvard", "Caltech",
    "Johns Hopkins", "Max Planck", "Pasteur Institute",
    # Entertainment venues
    "Dolby Theatre", "Madison Square Garden", "Wembley Stadium",
    "O2 Arena", "Coachella", "Sundance",
    # Sports venues
    "Augusta National", "Old Trafford", "Camp Nou", "Maracana", "MCG",
    # Tech
    "Cupertino", "Menlo Park", "Redmond",
]

# Additional multi-word location patterns
_REGIONS = [
    "Middle East", "Southeast Asia", "Central Asia", "East Africa",
    "West Africa", "North Africa", "South America", "Central America",
    "Eastern Europe", "Western Europe", "Pacific Islands",
    "Persian Gulf", "Red Sea", "Black Sea", "Mediterranean",
    "European Union", "African Union", "Arab League",
]

# Demonyms / adjectives that resolve to countries
_DEMONYMS = {
    "British": "United Kingdom", "American": "United States",
    "French": "France", "German": "Germany", "Italian": "Italy",
    "Spanish": "Spain", "Russian": "Russia", "Chinese": "China",
    "Japanese": "Japan", "Indian": "India", "Brazilian": "Brazil",
    "Mexican": "Mexico", "Canadian": "Canada", "Australian": "Australia",
    "Turkish": "Turkey", "Egyptian": "Egypt", "Israeli": "Israel",
    "Palestinian": "Palestine", "Iranian": "Iran", "Iraqi": "Iraq",
    "Syrian": "Syria", "Lebanese": "Lebanon", "Saudi": "Saudi Arabia",
    "Pakistani": "Pakistan", "Afghan": "Afghanistan",
    "Ukrainian": "Ukraine", "Polish": "Poland", "Greek": "Greece",
    "Dutch": "Netherlands", "Swedish": "Sweden", "Norwegian": "Norway",
    "Danish": "Denmark", "Finnish": "Finland", "Swiss": "Switzerland",
    "Portuguese": "Portugal", "Romanian": "Romania", "Hungarian": "Hungary",
    "Czech": "Czech Republic", "Serbian": "Serbia", "Croatian": "Croatia",
    "Nigerian": "Nigeria", "Kenyan": "Kenya", "Ethiopian": "Ethiopia",
    "Somali": "Somalia", "Sudanese": "Sudan",
    "South Korean": "South Korea", "North Korean": "North Korea",
    "Thai": "Thailand", "Vietnamese": "Vietnam", "Filipino": "Philippines",
    "Indonesian": "Indonesia", "Malaysian": "Malaysia",
    "Colombian": "Colombia", "Venezuelan": "Venezuela",
    "Peruvian": "Peru", "Chilean": "Chile", "Argentine": "Argentina",
    "Cuban": "Cuba", "Haitian": "Haiti",
    "Yemeni": "Yemen", "Libyan": "Libya", "Tunisian": "Tunisia",
    "Moroccan": "Morocco", "Algerian": "Algeria",
}

# Short abbreviations that map to countries (need special handling)
_ABBREVIATIONS = {
    "UK": "United Kingdom",
    "US": "United States",
    "U.K.": "United Kingdom",
    "U.S.": "United States",
    "UAE": "United Arab Emirates",
}

# --- Location tier classification for confidence clouds ---

_LANDMARK_SET = {
    "Pentagon", "Kremlin", "Wall Street", "Vatican", "Hollywood", "Broadway",
    "Capitol Hill", "Downing Street", "Silicon Valley", "Chernobyl",
    "Fukushima", "Guantanamo",
}

_STATE_SET = {
    "California", "Texas", "Florida", "New York", "Pennsylvania",
    "Ohio", "Georgia", "Michigan", "Illinois", "Virginia",
    "North Carolina", "Arizona", "Nevada", "Colorado", "Oregon",
    "Hawaii", "Alaska",
    "Scotland", "Wales", "Northern Ireland", "England",
    "Catalonia",
}

_LARGE_COUNTRIES = {
    "United States", "Russia", "China", "Brazil", "Australia", "Canada",
    "India", "Argentina", "Kazakhstan", "Algeria", "Indonesia",
}

_REGION_SET = set(_REGIONS)

# Tiers with default radius in km
_TIER_RADIUS = {
    "landmark": 5,
    "city": 25,
    "state": 150,
    "small_country": 200,
    "large_country": 800,
    "region": 1500,
}


def classify_location(name: str) -> tuple[str, int]:
    """Classify a location name into a specificity tier with a default radius.

    Returns (tier, radius_km).
    """
    if name in _LANDMARK_SET:
        return ("landmark", _TIER_RADIUS["landmark"])
    if name in _REGION_SET:
        return ("region", _TIER_RADIUS["region"])
    if name in _COUNTRY_SET:
        if name in _LARGE_COUNTRIES:
            return ("large_country", _TIER_RADIUS["large_country"])
        return ("small_country", _TIER_RADIUS["small_country"])
    if name in _STATE_SET:
        return ("state", _TIER_RADIUS["state"])
    # Default: treat as city (covers cities, neighborhoods, etc.)
    return ("city", _TIER_RADIUS["city"])

# Words that look like locations but aren't (in news context)
_FALSE_POSITIVES = {
    "EU", "UN", "NATO", "BBC", "CNN", "NPR", "AP", "AFP",
    "WHO", "ICJ", "IMF", "NASA", "OPEC", "GDP",
}


def _build_pattern(names: list[str]) -> re.Pattern:
    """Build a compiled regex that matches any of the given names as whole words."""
    # Sort by length (longest first) so "New Zealand" matches before "New"
    sorted_names = sorted(names, key=len, reverse=True)
    escaped = [re.escape(name) for name in sorted_names]
    pattern = r"\b(" + "|".join(escaped) + r")\b"
    return re.compile(pattern)


# Pre-compile patterns
_ALL_LOCATIONS = _COUNTRIES + _CITIES + _INSTITUTIONS + _REGIONS
_LOCATION_PATTERN = _build_pattern(_ALL_LOCATIONS)
_COUNTRY_SET = set(_COUNTRIES)
_CITY_SET = set(_CITIES)

# Compile demonym pattern (sorted by length, longest first)
_DEMONYM_PATTERN = _build_pattern(list(_DEMONYMS.keys()))

# Compile abbreviation pattern (word boundary + uppercase)
_ABBREV_SORTED = sorted(_ABBREVIATIONS.keys(), key=len, reverse=True)
_ABBREV_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(a) for a in _ABBREV_SORTED) + r")\b"
)


_EVENT_PREPS = {"in", "inside", "at", "near", "across", "throughout", "from", "into", "within"}
_ORIGIN_SIGNALS = {"'s", "of"}


def _classify_role(text: str, match_start: int, is_title: bool, is_first: bool) -> str:
    """Classify a location mention's role: event_location, origin, or mentioned.

    Checks the 30-char window before the match for spatial prepositions.
    """
    # Check preceding context (up to 30 chars before match)
    window_start = max(0, match_start - 30)
    before = text[window_start:match_start].lower().strip()

    # Check for event prepositions: "fighting in Tehran", "attack near Kabul"
    for prep in _EVENT_PREPS:
        if before.endswith(prep) or before.endswith(prep + " "):
            return "event_location"

    # Check for possessive/of signals: "Iran's president", "president of Iran"
    if before.endswith("'s") or before.endswith("of"):
        return "origin"

    # Title bias: first location in title is likely the event location
    if is_title and is_first:
        return "event_location"

    return "mentioned"


def extract_locations(text: str) -> list[dict]:
    """Extract location mentions from text using gazetteer matching.

    Returns list of dicts with 'text', 'label', 'count', 'role' sorted by frequency.
    Handles direct place names, demonyms (British->UK), and abbreviations (US, UK).
    """
    if not text or len(text.strip()) < 10:
        return []

    # Find title boundary (text before first ". ")
    title_end = text.find(". ")
    if title_end < 0:
        title_end = len(text)

    # Direct location matches — use finditer for position info
    match_info = []  # list of (name, start_pos)
    for m in _LOCATION_PATTERN.finditer(text):
        match_info.append((m.group(), m.start()))

    # Demonym matches (British -> United Kingdom, etc.)
    for m in _DEMONYM_PATTERN.finditer(text):
        resolved = _DEMONYMS.get(m.group())
        if resolved:
            match_info.append((resolved, m.start()))

    # Abbreviation matches (US, UK, UAE)
    for m in _ABBREV_PATTERN.finditer(text):
        abbr = m.group()
        if abbr not in _FALSE_POSITIVES:
            resolved = _ABBREVIATIONS.get(abbr)
            if resolved:
                match_info.append((resolved, m.start()))

    if not match_info:
        return []

    # Count occurrences and track roles
    counts = Counter()
    roles = {}  # name -> best role (event_location > origin > mentioned)
    seen_first = False

    role_priority = {"event_location": 2, "origin": 1, "mentioned": 0}

    for name, start_pos in match_info:
        if name in _FALSE_POSITIVES:
            continue
        counts[name] += 1

        is_title = start_pos < title_end
        is_first = not seen_first
        seen_first = True

        role = _classify_role(text, start_pos, is_title, is_first)
        if role_priority.get(role, 0) > role_priority.get(roles.get(name, "mentioned"), 0):
            roles[name] = role

    results = []
    for name, count in counts.most_common():
        if name in _FALSE_POSITIVES:
            continue
        # Classify as GPE (country/city) or LOC (region)
        if name in _COUNTRY_SET or name in _CITY_SET:
            label = "GPE"
        else:
            label = "LOC"
        results.append({
            "text": name,
            "label": label,
            "count": count,
            "role": roles.get(name, "mentioned"),
        })

    return results


def pick_primary_location(entities: list[dict]) -> Optional[str]:
    """Pick the most relevant location from extracted entities.

    Strategy: prefer event_location role (where it happened) over origin
    or mentioned. Within same role, prefer specific (cities) over countries.
    Among same tier, prefer most frequently mentioned.
    """
    if not entities:
        return None

    gpe = [e for e in entities if e["label"] == "GPE"]
    if not gpe:
        return entities[0]["text"]

    # Prioritize event_location role — this is WHERE IT HAPPENED
    event_locs = [e for e in gpe if e.get("role") == "event_location"]
    origin_locs = [e for e in gpe if e.get("role") == "origin"]
    mentioned_locs = [e for e in gpe if e.get("role") == "mentioned"]

    # Try each role tier in priority order
    for tier in [event_locs, origin_locs, mentioned_locs, gpe]:
        if not tier:
            continue
        # Within this tier, prefer cities/states over countries
        specific = [e for e in tier if e["text"] not in _COUNTRY_SET]
        countries = [e for e in tier if e["text"] in _COUNTRY_SET]
        if specific:
            return specific[0]["text"]
        if countries:
            return countries[0]["text"]

    return gpe[0]["text"]


def extract_story_location(story: dict) -> tuple[Optional[str], list[dict]]:
    """Extract the primary location from a story's title + summary.

    Returns (primary_location_name, all_entities).
    """
    text = f"{story.get('title', '')}. {story.get('summary', '')}"
    entities = extract_locations(text)
    primary = pick_primary_location(entities)
    return primary, entities
