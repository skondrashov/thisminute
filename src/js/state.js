export var state = {
  map: null,
  geojsonData: { type: "FeatureCollection", features: [] },
  cloudData: { type: "FeatureCollection", features: [] },
  lastFetchTime: null,
  // Filter state
  activeConcepts: /* @__PURE__ */ new Set(),
  excludedConcepts: /* @__PURE__ */ new Set(),
  activeSources: /* @__PURE__ */ new Set(),
  excludedSources: /* @__PURE__ */ new Set(),
  activeOrigins: /* @__PURE__ */ new Set(["rss", "gdelt", "usgs", "noaa", "eonet", "gdacs", "reliefweb", "who", "launches", "openaq", "travel", "firms", "meteoalarm", "acled", "jma"]),
  brightSideMode: false,
  curiousMode: false,
  filterDrawerOpen: false,
  mapHidden: false,
  activeFeedPanel: null,
  networkAnimId: null,
  spaceAnimId: null,
  conceptCounts: {},
  conceptDomainMap: {},
  allConceptMeta: {},
  feedTagData: { source_tags: {}, tag_sources: {} },
  _feedTagsReady: null,
  // New story tracking
  newStoryIds: /* @__PURE__ */ new Set(),
  pendingNewCount: 0,
  _lastDataUpdate: null,
  _pulseAnimId: null,
  _pulsePhase: 0,
  // Events/views state
  currentView: "narratives",
  eventsData: [],
  presetOverview: null,
  narrativesData: [],
  expandedEventId: null,
  expandedEventStories: [],
  activeNarrativeId: null,
  narrativeSortMode: "volume",
  eventSortMode: "volume",
  storySortMode: "new",
  _pendingSituationId: null,
  _pendingMapView: null,
  activeLocationFilter: null,
  // Theme
  lightMode: false,
  // initialized in main.js from localStorage
  // Visited story tracking
  _visitedStories: /* @__PURE__ */ new Set(),
  // UI state
  _popupDismissing: false,
  hoverTooltipEl: null,
  _filterState: null,
  _trendingConcepts: /* @__PURE__ */ new Set(),
  // Presets
  allPresets: {},
  activePresetId: "all",
  presetModified: false,
  _pendingPresetId: null,
  presetPrefs: {},
  // Sources
  sourceCounts: [],
  // Narratives
  _narrativeDeltas: {},
  _newNarrativeIds: /* @__PURE__ */ new Set(),
  // Map labels
  _lastEventGeo: { type: "FeatureCollection", features: [] },
  // Animations
  // Feedback
  _feedbackCooldownUntil: 0,
  _feedbackSessionCount: 0
};
export function _markPopupDismiss() {
  state._popupDismissing = true;
  requestAnimationFrame(function() { state._popupDismissing = false; });
}
export var DOMAIN_COLORS = {
  violence: "#e74c3c",
  human: "#e67e22",
  power: "#3498db",
  economy: "#2ecc71",
  planet: "#16a085",
  health: "#9b59b6",
  tech: "#1abc9c",
  culture: "#f39c12",
  uplifting: "#f1c40f"
};
export function _hexToRGB(hex) {
  return [parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16), parseInt(hex.slice(5, 7), 16)];
}
export function _rgbToHex(r, g, b) {
  var toHex = function(v) { return Math.round(Math.min(255, Math.max(0, v))).toString(16).padStart(2, "0"); };
  return "#" + toHex(r) + toHex(g) + toHex(b);
}
export var _domainRGB = {};
for (var _dc in DOMAIN_COLORS) _domainRGB[_dc] = _hexToRGB(DOMAIN_COLORS[_dc]);
export var _fallbackRGB = _hexToRGB("#484f58");
export var _BLEND_BASE_DARK = [255, 255, 255];
export var _BLEND_BASE_LIGHT = [110, 118, 129];
export function _featureDomain(f) {
  var concepts = f.properties.concepts;
  if (typeof concepts === "string") try { concepts = JSON.parse(concepts); } catch (e) { concepts = []; }
  if (Array.isArray(concepts)) {
    for (var i = 0; i < concepts.length; i++) {
      var lower = concepts[i].toLowerCase();
      for (var r = 0; r < TOPIC_DOMAIN_RULES.length; r++) {
        for (var k = 0; k < TOPIC_DOMAIN_RULES[r].keywords.length; k++) {
          if (lower.includes(TOPIC_DOMAIN_RULES[r].keywords[k])) return TOPIC_DOMAIN_RULES[r].domain;
        }
      }
    }
  }
  return "general";
}
export var _HEAT_STOPS = [
  [0, [88, 166, 255]],
  [0.25, [0, 210, 210]],
  [0.5, [255, 255, 0]],
  [0.75, [255, 140, 0]],
  [1, [255, 50, 30]]
];
export function _heatColor(ratio) {
  for (var s = 1; s < _HEAT_STOPS.length; s++) {
    if (ratio <= _HEAT_STOPS[s][0]) {
      var t = (ratio - _HEAT_STOPS[s - 1][0]) / (_HEAT_STOPS[s][0] - _HEAT_STOPS[s - 1][0]);
      var a = _HEAT_STOPS[s - 1][1], b = _HEAT_STOPS[s][1];
      return _rgbToHex(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t);
    }
  }
  return _rgbToHex(255, 50, 30);
}
export function _blendLocationColors(features) {
  var rawBase = state.lightMode ? _BLEND_BASE_LIGHT : _BLEND_BASE_DARK;
  var theme = state.dotColorTheme || "domain";
  var monoColor = state.lightMode ? "#57606a" : "#ffffff";
  /* Preset color tint — applied as a final pass on domain/classic themes */
  var activePreset = state.allPresets[state.activePresetId];
  var presetRGB = activePreset && activePreset.color ? _hexToRGB(activePreset.color) : null;
  var base = rawBase;
  var classicColor = presetRGB ? _rgbToHex(presetRGB[0], presetRGB[1], presetRGB[2]) : (state.lightMode ? "#0969da" : "#58a6ff");
  try {
    var byCoord = {};
    for (var i = 0; i < features.length; i++) {
      var f = features[i];
      if (!f.geometry || !f.geometry.coordinates) continue;
      f.properties._domain = _featureDomain(f);
      var key = f.geometry.coordinates[0] + "," + f.geometry.coordinates[1];
      if (!byCoord[key]) byCoord[key] = [];
      byCoord[key].push(f);
    }
    var maxGroupSize = 1;
    if (theme === "heat") {
      for (var kh in byCoord) {
        if (byCoord[kh].length > maxGroupSize) maxGroupSize = byCoord[kh].length;
      }
    }
    for (var k in byCoord) {
      var group = byCoord[k];
      var blended;
      if (theme === "classic") {
        blended = classicColor;
      } else if (theme === "mono") {
        blended = monoColor;
      } else if (theme === "heat") {
        var heatRatio = maxGroupSize > 1 ? (group.length - 1) / (maxGroupSize - 1) : 0;
        blended = _heatColor(heatRatio);
      } else {
        /* domain or neon */
        var domainCounts = {}, total = 0;
        var maxDomain = "general", maxCount = 0;
        for (var j = 0; j < group.length; j++) {
          var dom = group[j].properties._domain;
          domainCounts[dom] = (domainCounts[dom] || 0) + 1;
          total++;
          if (domainCounts[dom] > maxCount) {
            maxCount = domainCounts[dom];
            maxDomain = dom;
          }
        }
        var domRGB = _domainRGB[maxDomain] || _fallbackRGB;
        if (theme === "neon") {
          blended = _rgbToHex(domRGB[0], domRGB[1], domRGB[2]);
        } else {
          /* domain (default) */
          var ratio = total > 0 ? maxCount / total : 0;
          blended = _rgbToHex(
            base[0] + (domRGB[0] - base[0]) * ratio,
            base[1] + (domRGB[1] - base[1]) * ratio,
            base[2] + (domRGB[2] - base[2]) * ratio
          );
        }
      }
      /* Apply preset color tint to final blended color (skip for "all" — show pure domain colors) */
      if (presetRGB && state.activePresetId !== "all" && (theme === "domain" || theme === "classic")) {
        var bRGB = _hexToRGB(blended);
        var wt = 0.22;
        blended = _rgbToHex(
          bRGB[0] + (presetRGB[0] - bRGB[0]) * wt,
          bRGB[1] + (presetRGB[1] - bRGB[1]) * wt,
          bRGB[2] + (presetRGB[2] - bRGB[2]) * wt
        );
      }
      for (var j2 = 0; j2 < group.length; j2++) {
        group[j2].properties.blended_color = blended;
      }
    }
  } catch (e) {
    console.error("_blendLocationColors failed:", e);
  }
  for (var ii = 0; ii < features.length; ii++) {
    if (!features[ii].properties.blended_color) {
      var dom2 = features[ii].properties._domain || "general";
      var fallback = DOMAIN_COLORS[dom2] || "#484f58";
      if (presetRGB && state.activePresetId !== "all" && (theme === "domain" || theme === "classic")) {
        var fRGB = _hexToRGB(fallback);
        fallback = _rgbToHex(
          fRGB[0] + (presetRGB[0] - fRGB[0]) * 0.22,
          fRGB[1] + (presetRGB[1] - fRGB[1]) * 0.22,
          fRGB[2] + (presetRGB[2] - fRGB[2]) * 0.22
        );
      }
      features[ii].properties.blended_color = fallback;
    }
  }
}
export var COUNTRY_NAME_MAP = {
  "United States": "United States of America",
  "Czech Republic": "Czechia",
  "Bosnia": "Bosnia and Herz.",
  "Ivory Coast": "C\xF4te d'Ivoire",
  "Dominican Republic": "Dominican Rep.",
  "North Macedonia": "Macedonia",
  "South Sudan": "S. Sudan",
  "South Africa": "South Africa",
  "Sri Lanka": "Sri Lanka",
  "Sierra Leone": "Sierra Leone",
  "New Zealand": "New Zealand",
  "El Salvador": "El Salvador",
  "Costa Rica": "Costa Rica",
  "Saudi Arabia": "Saudi Arabia",
  "United Arab Emirates": "United Arab Emirates",
  "United Kingdom": "United Kingdom",
  "North Korea": "North Korea",
  "South Korea": "South Korea"
};
export var POLL_INTERVAL = 6e4;
export var EVENTS_INTERVAL = 12e4;
export var NARRATIVES_INTERVAL = 3e5;
export var BRIGHT_SIDE_MIN_SCORE = 4;
export var CURIOUS_MIN_SCORE = 7;
// Topics that veto stories from Bright Side / Curious even if scores are high
export var _VETO_TOPICS = new Set([
  "war", "iran-war", "iraq-war", "civil-war", "airstrike", "airstrikes",
  "bombing", "missile-strike", "military-operation", "invasion",
  "terrorism", "terrorist-attack", "mass-shooting", "shooting",
  "murder", "homicide", "assassination", "genocide", "massacre",
  "death-toll", "casualties", "killed", "fatalities",
  "drug-trafficking", "drug-cartel", "kidnapping", "hostage"
]);
export function _hasVetoTopic(concepts) {
  for (var i = 0; i < concepts.length; i++) {
    if (_VETO_TOPICS.has(concepts[i])) return true;
  }
  return false;
}
export var _VISITED_KEY = "thisminute-visited";
export var _VISITED_MAX = 500;
export var TOPIC_DOMAIN_RULES = [
  { domain: "violence", color: "#e74c3c", keywords: ["war", "conflict", "strike", "attack", "military", "weapon", "bomb", "kill", "death", "shooting", "violence", "terror", "security", "missile", "drone", "naval"] },
  { domain: "human", color: "#e67e22", keywords: ["rights", "refugee", "humanitarian", "abuse", "discrimination", "gender", "immigration", "protest", "justice", "corruption", "crime", "prison", "child"] },
  { domain: "power", color: "#3498db", keywords: ["politic", "election", "government", "trump", "cabinet", "legislation", "congress", "parliament", "democrat", "republican", "diplomatic", "sanction", "tariff", "trade"] },
  { domain: "economy", color: "#2ecc71", keywords: ["econom", "market", "stock", "finance", "business", "oil", "energy", "industry", "labor", "employ", "inflation", "banking", "currency"] },
  { domain: "planet", color: "#16a085", keywords: ["climate", "environment", "weather", "earthquake", "flood", "wildfire", "ocean", "species", "conservation", "pollution", "disaster", "agriculture"] },
  { domain: "health", color: "#9b59b6", keywords: ["health", "medical", "disease", "vaccine", "hospital", "mental", "drug", "cancer", "pandemic", "surgery", "pharma"] },
  { domain: "tech", color: "#1abc9c", keywords: ["ai", "tech", "cyber", "software", "data", "robot", "space", "nasa", "satellite", "internet", "crypto", "blockchain", "quantum"] },
  { domain: "culture", color: "#f39c12", keywords: ["film", "music", "art", "book", "sport", "cricket", "football", "rugby", "olympic", "award", "festival", "entertainment", "media", "celebrity", "cup"] },
  { domain: "uplifting", color: "#f1c40f", keywords: ["rescue", "hero", "discovery", "breakthrough", "donation", "volunteer", "recovery", "milestone", "achievement", "innovation"] }
];
export var WORLD_PRESETS = {
  all: {
    label: "All Stories",
    color: "#1f6feb",
    builtIn: true,
    permanent: true,
    config: {
      activeConcepts: [],
      excludedConcepts: [],
      activeSources: [],
      excludedSources: [],
      activeOrigins: ["rss", "gdelt", "usgs", "noaa", "eonet", "gdacs", "reliefweb", "who", "launches", "openaq", "travel", "firms", "meteoalarm", "acled", "jma"],
      brightSideMode: false,

      timeHours: "",
      hideOpinion: false
    }
  },
  bright_side: {
    label: "Bright Side",
    color: "#c99700",
    builtIn: true,
    config: {
      activeConcepts: [],
      excludedConcepts: [],
      activeSources: [],
      excludedSources: [],
      activeOrigins: ["rss", "gdelt", "launches"],
      brightSideMode: true,

      timeHours: "",
      hideOpinion: false
    }
  },
  sports: {
    label: "Sports",
    color: "#218838",
    builtIn: true,
    config: {
      activeConcepts: [],
      excludedConcepts: [],
      activeSources: [],
      excludedSources: [],
      activeOrigins: ["rss", "gdelt", "usgs", "noaa", "eonet", "gdacs", "reliefweb", "who", "launches", "openaq", "travel", "firms", "meteoalarm", "acled", "jma"],
      brightSideMode: false,

      timeHours: "",
      hideOpinion: false
    },
    feedTags: ["sports"]
  },
  entertainment: {
    label: "Entertainment",
    color: "#9645de",
    builtIn: true,
    config: {
      activeConcepts: [],
      excludedConcepts: [],
      activeSources: [],
      excludedSources: [],
      activeOrigins: ["rss", "gdelt", "usgs", "noaa", "eonet", "gdacs", "reliefweb", "who", "launches", "openaq", "travel", "firms", "meteoalarm", "acled", "jma"],
      brightSideMode: false,

      timeHours: "",
      hideOpinion: false
    },
    feedTags: ["entertainment"]
  },
  curious: {
    label: "Curious",
    color: "#d97236",
    builtIn: true,
    config: {
      activeConcepts: [],
      excludedConcepts: [],
      activeSources: [],
      excludedSources: [],
      activeOrigins: ["rss", "gdelt", "usgs", "noaa", "eonet", "gdacs", "reliefweb", "who", "launches", "openaq", "travel", "firms", "meteoalarm", "acled", "jma"],
      brightSideMode: false,
      curiousMode: true,

      timeHours: "",
      hideOpinion: false
    }
  },
  science: {
    label: "Science",
    color: "#0891b2",
    builtIn: true,
    config: {
      activeConcepts: [],
      excludedConcepts: [],
      activeSources: [],
      excludedSources: [],
      activeOrigins: ["rss", "gdelt", "usgs", "noaa", "eonet", "gdacs", "reliefweb", "who", "launches", "openaq", "travel", "firms", "meteoalarm", "acled", "jma"],
      brightSideMode: false,

      timeHours: "",
      hideOpinion: false
    },
    feedTags: ["science"]
  },
  tech: {
    label: "Tech",
    color: "#ec4899",
    builtIn: true,
    config: {
      activeConcepts: [],
      excludedConcepts: [],
      activeSources: [],
      excludedSources: [],
      activeOrigins: ["rss", "gdelt", "usgs", "noaa", "eonet", "gdacs", "reliefweb", "who", "launches", "openaq", "travel", "firms", "meteoalarm", "acled", "jma"],
      brightSideMode: false,

      timeHours: "",
      hideOpinion: false
    },
    feedTags: ["tech"]
  },
  planet: {
    label: "Planet",
    color: "#4a80b0",
    builtIn: true,
    config: {
      activeConcepts: [],
      excludedConcepts: [],
      activeSources: [],
      excludedSources: [],
      activeOrigins: ["noaa", "eonet", "usgs", "gdacs", "firms", "meteoalarm", "jma"],
      brightSideMode: false,

      timeHours: "",
      hideOpinion: false
    }
  },
  conflict: {
    label: "Conflict",
    color: "#dc2626",
    builtIn: true,
    config: {
      activeConcepts: [],
      excludedConcepts: [],
      activeSources: [],
      excludedSources: [],
      activeOrigins: ["rss", "gdelt", "acled"],
      brightSideMode: false,

      timeHours: "",
      hideOpinion: false
    },
    keywords: ["war", "conflict", "military", "attack", "bombing", "airstrike", "weapons", "ceasefire", "protest", "shooting", "terrorism"]
  },
  travel: {
    label: "Travel",
    color: "#6d28d9",
    builtIn: true,
    config: {
      activeConcepts: [],
      excludedConcepts: [],
      activeSources: [],
      excludedSources: [],
      activeOrigins: ["rss", "travel", "noaa", "gdacs", "who", "meteoalarm", "acled", "jma"],
      brightSideMode: false,

      timeHours: "",
      hideOpinion: false
    }
  },
  power: {
    label: "Power",
    color: "#6b7280",
    builtIn: true,
    config: {
      activeConcepts: [],
      excludedConcepts: [],
      activeSources: [],
      excludedSources: [],
      activeOrigins: ["rss", "gdelt", "acled", "travel"],
      brightSideMode: false,

      timeHours: "",
      hideOpinion: false
    },
    keywords: ["politics", "election", "government", "legislation", "congress", "parliament", "diplomacy", "sanctions", "corruption", "justice", "court"]
  },
  markets: {
    label: "Markets",
    color: "#0d7367",
    builtIn: true,
    config: {
      activeConcepts: [],
      excludedConcepts: [],
      activeSources: [],
      excludedSources: [],
      activeOrigins: ["rss", "gdelt"],
      brightSideMode: false,

      timeHours: "",
      hideOpinion: false
    },
    feedTags: ["business"]
  },
  health: {
    label: "Health",
    color: "#7c3aed",
    builtIn: true,
    config: {
      activeConcepts: [],
      excludedConcepts: [],
      activeSources: [],
      excludedSources: [],
      activeOrigins: ["rss", "who", "reliefweb"],
      brightSideMode: false,

      timeHours: "",
      hideOpinion: false
    },
    keywords: ["health", "disease", "vaccine", "hospital", "drug", "cancer", "pandemic", "surgery", "outbreak", "medical"]
  },
};
export var PRESET_ALIASES = {
  "positive": "bright_side",
  "weather": "planet",
  "crisis": "conflict",
  "geopolitics": "power",
  "news": "all"
};
export function _resolvePresetAlias(id) { return id && PRESET_ALIASES[id] || id; }
export var PRESET_ICONS = { all: "\u25C9", bright_side: "\u2728", sports: "\u26BD", entertainment: "\u{1F3AC}", science: "\u{1F52C}", tech: "\u{1F4BB}", curious: "\u{1F9E9}", planet: "\u{1F30D}", conflict: "\u2694\uFE0F", travel: "\u2708\uFE0F", power: "\u{1F3DB}\uFE0F", markets: "\u{1F4C8}", health: "\u{1F3E5}" };
export var NAME_EMOJI_MAP = [
  [/war|conflict|military|defense/i, "\u2694\uFE0F"],
  [/tech|ai|cyber|software|data/i, "\u{1F4BB}"],
  [/climate|environment|weather|earth/i, "\u{1F30D}"],
  [/health|medical|hospital/i, "\u{1F3E5}"],
  [/econom|market|stock|finance|business/i, "\u{1F4C8}"],
  [/politic|government|election|vote/i, "\u{1F3DB}\uFE0F"],
  [/space|nasa|rocket|orbit/i, "\u{1F680}"],
  [/sport|athlet|team|league/i, "\u{1F3C5}"],
  [/music|film|movie|entertain|art/i, "\u{1F3AD}"],
  [/food|cook|recipe|restaurant/i, "\u{1F355}"],
  [/travel|flight|vacation|tourism/i, "\u2708\uFE0F"],
  [/science|research|study|lab/i, "\u{1F52C}"],
  [/crime|law|legal|court|justice/i, "\u2696\uFE0F"],
  [/education|school|university|learn/i, "\u{1F393}"],
  [/crypto|bitcoin|blockchain/i, "\u{1FA99}"],
  [/energy|oil|solar|nuclear/i, "\u26A1"],
  [/asia|china|japan|korea|india/i, "\u{1F30F}"],
  [/europe|eu|euro/i, "\u{1F1EA}\u{1F1FA}"],
  [/football|nfl|soccer/i, "\u{1F3C8}"],
  [/basketball|nba/i, "\u{1F3C0}"],
  [/baseball|mlb/i, "\u26BE"]
];
export var CUSTOM_COLOR_PALETTE = [
  "#e06c75",
  "#61afef",
  "#98c379",
  "#c678dd",
  "#e5c07b",
  "#56b6c2",
  "#be5046",
  "#d19a66"
];
export var PRESET_DOMAIN_MAP = {
  bright_side: "positive",
  sports: "sports",
  entertainment: "entertainment",
  curious: "curious",
  conflict: "news",
  power: "news",
  health: "health",
  science: "science",
  tech: "science",
  markets: "business"
};
// Presets whose default tab is Stories (events) rather than Situations (narratives)
export var _STORIES_DEFAULT_PRESETS = new Set(["bright_side", "curious"]);
export function _getPresetDefaultView(presetId) {
  return _STORIES_DEFAULT_PRESETS.has(presetId) ? "events" : "narratives";
}
// Presets that are API-driven (structured data only) and should not show narrative situations
export var _DOMAINLESS_HIDE_SITUATIONS = new Set(["planet", "travel"]);
export var _DOMAIN_HIGHLIGHT_COLORS = {
  dark: { news: "#58a6ff", sports: "#3fb950", entertainment: "#bc8cff", positive: "#f5a623", curious: "#ff6f61", science: "#22d3ee", business: "#2dd4a8", health: "#a78bfa" },
  light: { news: "#0969da", sports: "#1a7f37", entertainment: "#8250df", positive: "#bf8700", curious: "#c9302c", science: "#0891b2", business: "#0d7367", health: "#7c3aed" }
};
