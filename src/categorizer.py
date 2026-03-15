"""Multi-label concept tagging for news stories.

Instead of assigning one category, we tag stories with ALL matching concepts.
Users filter by toggling concepts on/off — they curate their own front page.
"""

import re
from typing import Optional

# --- Concept taxonomy ---
# Organized by domain. Each concept has keywords that trigger it.
# A story can match MANY concepts simultaneously.

CONCEPT_DOMAINS = {
    "violence": {
        "color": "#e74c3c",
        "concepts": {
            "war": [
                "war", "warfare", "armed conflict", "military operation",
                "invasion", "occupation", "frontline", "battlefield",
            ],
            "terrorism": [
                "terrorism", "terrorist", "extremist", "radicalized",
                "insurgent", "jihadist", "militant group",
            ],
            "shooting": [
                "shooting", "gunfire", "gunshot", "shooter", "gunman",
                "mass shooting", "gun violence",
            ],
            "bombing": [
                "bomb", "bombing", "explosion", "blast", "detonation",
                "ied", "car bomb", "suicide bomb",
            ],
            "airstrike": [
                "airstrike", "air strike", "aerial bombardment",
                "drone strike", "missile strike", "shelling",
            ],
            "weapons": [
                "weapons", "arms", "munitions", "warhead", "nuclear weapon",
                "chemical weapon", "biological weapon",
            ],
            "ceasefire": [
                "ceasefire", "truce", "armistice", "peace deal",
                "peace talks", "peace agreement", "de-escalation",
            ],
        },
    },
    "human": {
        "color": "#e67e22",
        "concepts": {
            "death": [
                "killed", "kills", "dead", "death", "died", "fatal", "fatality",
                "casualties", "body count", "death toll", "mourning",
                "funeral", "massacre", "slain", "lethal",
            ],
            "injury": [
                "injured", "wounded", "hurt", "hospitalized",
                "casualties", "trauma", "critical condition",
            ],
            "displacement": [
                "refugee", "displaced", "evacuation", "evacuated",
                "asylum", "flee", "fled", "shelter", "humanitarian crisis",
                "internally displaced",
            ],
            "migration": [
                "migration", "immigrant", "migrant", "border crossing",
                "deportation", "visa", "asylum seeker", "undocumented",
            ],
            "crime": [
                "crime", "criminal", "murder", "homicide", "robbery",
                "theft", "fraud", "trafficking", "cartel", "gang",
                "arrested", "suspect", "investigation",
            ],
            "human-rights": [
                "human rights", "civil rights", "oppression", "persecution",
                "discrimination", "genocide", "war crime", "atrocity",
                "torture", "arbitrary detention", "censorship",
            ],
            "protest": [
                "protest", "demonstration", "rally", "march", "uprising",
                "unrest", "riot", "civil disobedience", "strike action",
                "activist",
            ],
        },
    },
    "power": {
        "color": "#3498db",
        "concepts": {
            "politics": [
                "president", "prime minister", "minister", "parliament",
                "senate", "congress", "political party", "opposition",
                "government", "cabinet", "legislation", "policy",
                "bipartisan", "partisan",
            ],
            "election": [
                "election", "vote", "ballot", "polling", "candidate",
                "campaign", "referendum", "runoff", "inauguration",
                "electoral",
            ],
            "diplomacy": [
                "diplomatic", "diplomacy", "ambassador", "embassy",
                "summit", "treaty", "bilateral", "multilateral",
                "united nations", "foreign minister", "state department",
            ],
            "sanctions": [
                "sanctions", "embargo", "trade restriction", "blacklist",
                "asset freeze", "export ban",
            ],
            "military": [
                "military", "troops", "soldiers", "armed forces", "navy",
                "army", "air force", "pentagon", "defense", "deployment",
                "conscription", "veterans",
            ],
            "corruption": [
                "corruption", "bribery", "embezzlement", "scandal",
                "money laundering", "kickback", "cronyism",
            ],
            "justice": [
                "court", "trial", "verdict", "sentence", "judge",
                "prosecution", "lawsuit", "indictment", "acquittal",
                "supreme court", "tribunal", "extradition",
            ],
        },
    },
    "economy": {
        "color": "#2ecc71",
        "concepts": {
            "markets": [
                "stock market", "wall street", "nasdaq", "dow jones",
                "shares", "investors", "trading", "bull market",
                "bear market", "ipo",
            ],
            "trade": [
                "trade", "tariff", "import", "export", "trade war",
                "trade deal", "free trade", "supply chain", "commerce",
            ],
            "inflation": [
                "inflation", "cost of living", "consumer prices",
                "interest rate", "central bank", "federal reserve",
                "monetary policy",
            ],
            "jobs": [
                "unemployment", "jobs", "layoffs", "hiring", "workforce",
                "labor market", "wages", "minimum wage",
            ],
            "energy": [
                "oil price", "gas price", "opec", "petroleum",
                "natural gas", "energy crisis", "fuel",
            ],
            "housing": [
                "housing", "real estate", "mortgage", "rent",
                "property market", "affordable housing", "homelessness",
            ],
            "crypto": [
                "bitcoin", "cryptocurrency", "blockchain", "ethereum",
                "crypto", "digital currency",
            ],
        },
    },
    "planet": {
        "color": "#16a085",
        "concepts": {
            "climate": [
                "climate change", "global warming", "emissions", "carbon",
                "greenhouse", "paris agreement", "net zero", "fossil fuel",
                "renewable", "sustainability",
            ],
            "weather": [
                "weather", "temperature", "heatwave", "cold snap",
                "record heat", "record cold", "monsoon", "wet", "dry",
                "forecast", "summer", "winter",
                "weather warning", "severe weather",
            ],
            "disaster": [
                "earthquake", "tsunami", "volcano", "eruption",
                "hurricane", "typhoon", "cyclone", "tornado",
                "flood", "flooding", "landslide", "avalanche",
            ],
            "wildfire": [
                "wildfire", "bushfire", "forest fire", "blaze",
                "fire season", "arson",
            ],
            "pollution": [
                "pollution", "contamination", "toxic", "oil spill",
                "plastic", "waste", "smog", "air quality",
                "air quality index", "aqi", "pm2.5", "pm10",
            ],
            "wildlife": [
                "endangered", "extinction", "biodiversity", "conservation",
                "deforestation", "habitat", "species", "poaching",
            ],
        },
    },
    "health": {
        "color": "#9b59b6",
        "concepts": {
            "disease": [
                "disease", "virus", "infection", "outbreak", "epidemic",
                "pandemic", "contagious", "pathogen",
            ],
            "vaccine": [
                "vaccine", "vaccination", "immunization", "booster",
                "clinical trial",
            ],
            "mental-health": [
                "mental health", "depression", "anxiety", "suicide",
                "therapy", "psychological", "wellbeing",
            ],
            "hospital": [
                "hospital", "medical", "surgery", "patient", "doctor",
                "nurse", "healthcare", "emergency room",
            ],
            "drug": [
                "drug", "pharmaceutical", "medication", "overdose",
                "opioid", "fentanyl", "prescription",
            ],
            "cancer": [
                "cancer", "tumor", "oncology", "chemotherapy",
                "carcinogen", "malignant",
            ],
        },
    },
    "tech": {
        "color": "#1abc9c",
        "concepts": {
            "AI": [
                "artificial intelligence", "machine learning", "deep learning",
                "chatbot", "generative ai", "large language model", "neural network",
                "openai", "chatgpt",
            ],
            "cyber": [
                "cybersecurity", "hacking", "data breach", "ransomware",
                "cyberattack", "phishing", "malware", "cybercrime",
            ],
            "space": [
                "nasa", "spacex", "satellite", "orbit", "astronaut",
                "rocket launch", "mars", "moon landing", "space station",
                "asteroid",
            ],
            "internet": [
                "social media", "facebook", "twitter", "tiktok", "instagram",
                "youtube", "online", "streaming", "disinformation",
                "content moderation",
            ],
            "robotics": [
                "robot", "robotics", "automation", "autonomous vehicle",
                "self-driving", "drone",
            ],
        },
    },
    "culture": {
        "color": "#f39c12",
        "concepts": {
            "sports": [
                "football", "soccer", "basketball", "tennis", "cricket",
                "olympic", "championship", "tournament", "league",
                "world cup", "athlete", "medal", "marathon", "rugby",
                "baseball", "golf", "formula one",
            ],
            "entertainment": [
                "film", "movie", "cinema", "actor", "actress", "oscar",
                "grammy", "emmy", "celebrity", "tv show", "series",
                "concert", "festival", "album", "music", "musician",
                "singer", "band", "box office", "streaming",
            ],
            "religion": [
                "church", "mosque", "temple", "pope", "imam", "rabbi",
                "religious", "faith", "prayer", "pilgrimage",
                "christian", "muslim", "hindu", "buddhist", "jewish",
            ],
            "education": [
                "university", "school", "student", "teacher", "education",
                "academic", "scholarship", "curriculum", "graduation",
            ],
            "science": [
                "research", "study", "scientist", "discovery", "experiment",
                "laboratory", "peer-reviewed", "journal", "breakthrough",
            ],
        },
    },
    "uplifting": {
        "color": "#f1c40f",
        "concepts": {
            "community": [
                "volunteer", "charity", "donation", "fundraiser", "nonprofit",
                "philanthropy", "goodwill", "humanitarian aid", "food bank",
                "community service", "giving back", "mentor", "kindness",
            ],
            "achievement": [
                "record-breaking", "milestone", "award-winning", "triumph",
                "heroic", "historic first", "world record", "groundbreaking",
                "pioneering", "honored", "celebrates", "inaugurated",
            ],
            "rescue": [
                "rescued", "survivor", "survived", "recovery", "rebuilt",
                "restoration", "reunion", "found alive", "saved", "miracle",
                "reunited", "comeback",
            ],
            "cooperation": [
                "partnership", "collaboration", "agreement", "alliance",
                "joint venture", "unity", "solidarity", "mutual aid",
                "bipartisan effort", "coalition",
            ],
        },
    },
}

# Build flat concept -> keywords mapping and compile patterns
_CONCEPT_PATTERNS: dict[str, re.Pattern] = {}
_CONCEPT_DOMAIN: dict[str, str] = {}
_CONCEPT_COLORS: dict[str, str] = {}

for domain_name, domain_info in CONCEPT_DOMAINS.items():
    color = domain_info["color"]
    for concept_name, keywords in domain_info["concepts"].items():
        # Sort by length (longest first) for greedy matching
        sorted_kw = sorted(keywords, key=len, reverse=True)
        pattern = r"\b(" + "|".join(re.escape(kw) for kw in sorted_kw) + r")\b"
        _CONCEPT_PATTERNS[concept_name] = re.compile(pattern, re.IGNORECASE)
        _CONCEPT_DOMAIN[concept_name] = domain_name
        _CONCEPT_COLORS[concept_name] = color


def tag_concepts(title: str, summary: str = "") -> list[dict]:
    """Tag a story with all matching concepts.

    Returns list of dicts: [{name, domain, color, score, matches}, ...]
    sorted by score (number of keyword matches) descending.
    """
    text = f"{title} {summary}"

    results = []
    for concept, pattern in _CONCEPT_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            results.append({
                "name": concept,
                "domain": _CONCEPT_DOMAIN[concept],
                "color": _CONCEPT_COLORS[concept],
                "score": len(matches),
                "matches": list(set(m.lower() for m in matches)),
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def get_primary_category(concepts: list[dict]) -> str:
    """Get the single best category for backwards compatibility.

    Returns the domain of the highest-scoring concept, or 'general'.
    """
    if not concepts:
        return "general"
    return concepts[0]["domain"]


def get_all_concept_names() -> list[dict]:
    """Return all known concepts with their domains and colors."""
    result = []
    for domain_name, domain_info in CONCEPT_DOMAINS.items():
        for concept_name in domain_info["concepts"]:
            result.append({
                "name": concept_name,
                "domain": domain_name,
                "color": domain_info["color"],
            })
    return result


# Backwards-compatible single-category function
def categorize(title: str, summary: str = "") -> str:
    """Categorize a story (single label, backwards compatible)."""
    concepts = tag_concepts(title, summary)
    return get_primary_category(concepts)
