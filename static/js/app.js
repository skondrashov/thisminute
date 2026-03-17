(() => {
  // src/js/state.js
  var state = {
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
    globeManualOverride: null,
    currentProjection: "globe",
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
    registryData: [],
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
    hoverTooltipEl: null,
    _filterState: null,
    _trendingConcepts: /* @__PURE__ */ new Set(),
    // Presets
    allPresets: {},
    activePresetId: "bright_side",
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
    internetAnimFrame: null,
    // Feedback
    _feedbackCooldownUntil: 0,
    _feedbackSessionCount: 0
  };
  var DOMAIN_COLORS = {
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
  function _hexToRGB(hex) {
    return [parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16), parseInt(hex.slice(5, 7), 16)];
  }
  function _rgbToHex(r, g, b) {
    var toHex = function(v) { return Math.round(Math.min(255, Math.max(0, v))).toString(16).padStart(2, "0"); };
    return "#" + toHex(r) + toHex(g) + toHex(b);
  }
  var _domainRGB = {};
  for (var _dc in DOMAIN_COLORS) _domainRGB[_dc] = _hexToRGB(DOMAIN_COLORS[_dc]);
  var _fallbackRGB = _hexToRGB("#484f58");
  var _BLEND_BASE_DARK = [255, 255, 255];
  var _BLEND_BASE_LIGHT = [110, 118, 129];
  function _featureDomain(f) {
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
  var _HEAT_STOPS = [
    [0, [88, 166, 255]],
    [0.25, [0, 210, 210]],
    [0.5, [255, 255, 0]],
    [0.75, [255, 140, 0]],
    [1, [255, 50, 30]]
  ];
  function _heatColor(ratio) {
    for (var s = 1; s < _HEAT_STOPS.length; s++) {
      if (ratio <= _HEAT_STOPS[s][0]) {
        var t = (ratio - _HEAT_STOPS[s - 1][0]) / (_HEAT_STOPS[s][0] - _HEAT_STOPS[s - 1][0]);
        var a = _HEAT_STOPS[s - 1][1], b = _HEAT_STOPS[s][1];
        return _rgbToHex(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t);
      }
    }
    return _rgbToHex(255, 50, 30);
  }
  function _blendLocationColors(features) {
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
        /* Apply preset color tint to final blended color */
        if (presetRGB && (theme === "domain" || theme === "classic")) {
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
        if (presetRGB && (theme === "domain" || theme === "classic")) {
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
  var COUNTRY_NAME_MAP = {
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
  var POLL_INTERVAL = 6e4;
  var EVENTS_INTERVAL = 12e4;
  var NARRATIVES_INTERVAL = 3e5;
  var BRIGHT_SIDE_MIN_SCORE = 4;
  var CURIOUS_MIN_SCORE = 7;
  // Topics that veto stories from Bright Side / Curious even if scores are high
  var _VETO_TOPICS = new Set([
    "war", "iran-war", "iraq-war", "civil-war", "airstrike", "airstrikes",
    "bombing", "missile-strike", "military-operation", "invasion",
    "terrorism", "terrorist-attack", "mass-shooting", "shooting",
    "murder", "homicide", "assassination", "genocide", "massacre",
    "death-toll", "casualties", "killed", "fatalities",
    "drug-trafficking", "drug-cartel", "kidnapping", "hostage"
  ]);
  function _hasVetoTopic(concepts) {
    for (var i = 0; i < concepts.length; i++) {
      if (_VETO_TOPICS.has(concepts[i])) return true;
    }
    return false;
  }
  var _VISITED_KEY = "thisminute-visited";
  var _VISITED_MAX = 500;
  var TOPIC_DOMAIN_RULES = [
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
  var WORLD_PRESETS = {
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
        searchText: "",
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
        searchText: "",
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
        searchText: "",
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
        searchText: "",
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
        searchText: "",
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
        searchText: "",
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
        searchText: "",
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
        searchText: "",
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
        searchText: "",
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
        searchText: "",
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
        searchText: "",
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
        searchText: "",
        timeHours: "",
        hideOpinion: false
      },
      keywords: ["health", "disease", "vaccine", "hospital", "drug", "cancer", "pandemic", "surgery", "outbreak", "medical"]
    },
    all: {
      label: "All",
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
        searchText: "",
        timeHours: "",
        hideOpinion: false
      }
    }
  };
  var PRESET_ALIASES = {
    "positive": "bright_side",
    "weather": "planet",
    "crisis": "conflict",
    "geopolitics": "power",
    "news": "all"
  };
  function _resolvePresetAlias(id) { return id && PRESET_ALIASES[id] || id; }
  var PRESET_ICONS = { all: "\u25C9", bright_side: "\u2728", sports: "\u26BD", entertainment: "\u{1F3AC}", science: "\u{1F52C}", tech: "\u{1F4BB}", curious: "\u{1F9E9}", planet: "\u{1F30D}", conflict: "\u2694\uFE0F", travel: "\u2708\uFE0F", power: "\u{1F3DB}\uFE0F", markets: "\u{1F4C8}", health: "\u{1F3E5}" };
  var NAME_EMOJI_MAP = [
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
  var CUSTOM_COLOR_PALETTE = [
    "#e06c75",
    "#61afef",
    "#98c379",
    "#c678dd",
    "#e5c07b",
    "#56b6c2",
    "#be5046",
    "#d19a66"
  ];
  var PRESET_DOMAIN_MAP = {
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
  // Presets that are API-driven (structured data only) and should not show narrative situations
  var _DOMAINLESS_HIDE_SITUATIONS = new Set(["planet", "travel"]);
  var _DOMAIN_HIGHLIGHT_COLORS = {
    dark: { news: "#58a6ff", sports: "#3fb950", entertainment: "#bc8cff", positive: "#f5a623", curious: "#ff6f61", science: "#22d3ee", business: "#2dd4a8", health: "#a78bfa" },
    light: { news: "#0969da", sports: "#1a7f37", entertainment: "#8250df", positive: "#bf8700", curious: "#c9302c", science: "#0891b2", business: "#0d7367", health: "#7c3aed" }
  };

  // src/js/utils.js
  function escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
  function truncateRaw(text, maxLen) {
    if (!text) return "";
    return text.length <= maxLen ? text : text.slice(0, maxLen) + "...";
  }

  /** Shared clipboard-copy with checkmark animation. */
  function _copyToClipboard(btn, url, originalIcon) {
    originalIcon = originalIcon || "&#128279;";
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(() => {
        btn.textContent = "\u2713";
        if (btn.classList) btn.classList.add("copied");
        setTimeout(() => {
          btn.innerHTML = originalIcon;
          if (btn.classList) btn.classList.remove("copied");
        }, 1500);
      }).catch(() => {});
    }
  }

  /** Shared feedback-button wiring — call on any container with .feedback-btn elements. */
  function _wireFeedbackButtons(container) {
    container.querySelectorAll(".feedback-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        openFeedbackDialog({ type: btn.dataset.fbType, id: parseInt(btn.dataset.fbId), title: btn.dataset.fbTitle });
      });
    });
  }
  function formatTime(isoString) {
    if (!isoString) return "";
    try {
      const d = new Date(isoString);
      const now = /* @__PURE__ */ new Date();
      const diffMin = Math.floor((now - d) / 6e4);
      if (diffMin < 1) return "now";
      if (diffMin < 60) return `${diffMin}m`;
      const diffHr = Math.floor(diffMin / 60);
      if (diffHr < 24) return `${diffHr}h`;
      return `${Math.floor(diffHr / 24)}d`;
    } catch {
      return "";
    }
  }
  function formatFullTime(isoString) {
    if (!isoString) return "";
    try {
      const d = new Date(isoString);
      return d.toLocaleString(void 0, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
    } catch {
      return "";
    }
  }
  function _highlightText(escapedHtml, query) {
    if (!query || query.length < 2) return escapedHtml;
    const escaped = escapeHtml(query);
    const re = new RegExp(`(${escaped.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi");
    return escapedHtml.replace(re, "<mark>$1</mark>");
  }
  function _getFavicon(url) {
    if (!url) return "";
    try {
      const domain = new URL(url).hostname;
      return `<img class="source-favicon" src="https://www.google.com/s2/favicons?sz=16&domain=${domain}" alt="" width="14" height="14" onerror="this.remove()">`;
    } catch {
      return "";
    }
  }

  // src/js/animations.js
  function _initAnimCanvas() {
    const canvas = document.getElementById("info-panel-bg-canvas");
    if (!canvas) return null;
    const ctx = canvas.getContext("2d");
    const isLight = document.body.classList.contains("light-mode");
    const panel = document.getElementById("info-panel");
    const resize = () => { canvas.width = panel.offsetWidth; canvas.height = panel.offsetHeight; };
    resize();
    window.addEventListener("resize", resize);
    canvas._resizeHandler = resize;
    return { canvas, ctx, isLight };
  }
  function _stopAnim(stateKey) {
    if (state[stateKey]) { cancelAnimationFrame(state[stateKey]); state[stateKey] = null; }
    const canvas = document.getElementById("info-panel-bg-canvas");
    if (canvas) {
      if (canvas._resizeHandler) { window.removeEventListener("resize", canvas._resizeHandler); canvas._resizeHandler = null; }
      canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height);
    }
  }
  function startNetworkAnimation() {
    const env = _initAnimCanvas();
    if (!env) return;
    const { canvas, ctx, isLight } = env;
    const nodeCount = 35;
    const nodes = [];
    for (let i = 0; i < nodeCount; i++) {
      nodes.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.025,
        vy: (Math.random() - 0.5) * 0.025,
        r: 1.5 + Math.random() * 2,
        pulse: Math.random() * Math.PI * 2
      });
    }
    const mstEdges = [];
    const inTree = /* @__PURE__ */ new Set([0]);
    const cheapest = new Array(nodeCount);
    for (let j = 1; j < nodeCount; j++) {
      const dx = nodes[0].x - nodes[j].x;
      const dy = nodes[0].y - nodes[j].y;
      cheapest[j] = { cost: dx * dx + dy * dy, from: 0 };
    }
    while (inTree.size < nodeCount) {
      let best = -1, bestCost = Infinity;
      for (let j = 0; j < nodeCount; j++) {
        if (!inTree.has(j) && cheapest[j].cost < bestCost) {
          bestCost = cheapest[j].cost;
          best = j;
        }
      }
      inTree.add(best);
      mstEdges.push([cheapest[best].from, best]);
      for (let j = 0; j < nodeCount; j++) {
        if (!inTree.has(j)) {
          const dx = nodes[best].x - nodes[j].x;
          const dy = nodes[best].y - nodes[j].y;
          const c = dx * dx + dy * dy;
          if (c < cheapest[j].cost) cheapest[j] = { cost: c, from: best };
        }
      }
    }
    const maxDist = 120;
    const mstAlpha = isLight ? 0.08 : 0.12;
    function draw() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (const n of nodes) {
        n.x += n.vx;
        n.y += n.vy;
        n.pulse += 1e-3;
        if (n.x < 0 || n.x > canvas.width) n.vx *= -1;
        if (n.y < 0 || n.y > canvas.height) n.vy *= -1;
      }
      ctx.strokeStyle = `rgba(52, 152, 219, ${mstAlpha})`;
      ctx.lineWidth = 0.6;
      for (const [a, b] of mstEdges) {
        ctx.beginPath();
        ctx.moveTo(nodes[a].x, nodes[a].y);
        ctx.lineTo(nodes[b].x, nodes[b].y);
        ctx.stroke();
      }
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < maxDist) {
            const alpha = (1 - dist / maxDist) * (isLight ? 0.15 : 0.25);
            ctx.beginPath();
            ctx.moveTo(nodes[i].x, nodes[i].y);
            ctx.lineTo(nodes[j].x, nodes[j].y);
            ctx.strokeStyle = `rgba(52, 152, 219, ${alpha})`;
            ctx.lineWidth = 0.8;
            ctx.stroke();
          }
        }
      }
      for (const n of nodes) {
        const glow = 0.5 + 0.5 * Math.sin(n.pulse);
        const alpha = 0.1 + glow * 0.15;
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx.fillStyle = isLight ? `rgba(52, 152, 219, ${alpha * 0.8})` : `rgba(100, 180, 255, ${alpha})`;
        ctx.fill();
      }
      state.networkAnimId = requestAnimationFrame(draw);
    }
    state.networkAnimId = requestAnimationFrame(draw);
  }
  function stopNetworkAnimation() { _stopAnim("networkAnimId"); }
  function startSpaceAnimation() {
    const env = _initAnimCanvas();
    if (!env) return;
    const { canvas, ctx, isLight } = env;
    const starCount = 200;
    const stars = [];
    for (let i = 0; i < starCount; i++) {
      const r = 0.3 + Math.random() * 1.2;
      const doesTwinkle = Math.random() < 0.1;
      const hasCross = r > 1 && Math.random() < 0.25;
      stars.push({
        xf: Math.random(),
        yf: Math.random(),
        r,
        brightness: 0.08 + Math.random() * 0.25,
        doesTwinkle,
        twinkleTimer: doesTwinkle ? Math.random() * 600 : 0,
        twinkleFlicker: 0,
        twinkleDim: 1,
        // Faint brightness wander: slow sine with tiny amplitude
        wanderPhase: Math.random() * Math.PI * 2,
        wanderSpeed: 5e-4 + Math.random() * 2e-3,
        // very slow
        wanderAmp: 0.03 + Math.random() * 0.06,
        // ±3-9% brightness
        hue: Math.random() < 0.7 ? 220 : Math.random() < 0.5 ? 240 : 40,
        sat: Math.random() * 30,
        hasCross,
        crossLen: hasCross ? 3 + Math.random() * 5 : 0,
        crossAngle: Math.random() * Math.PI * 0.15
      });
    }
    const driftAngle = 105 * Math.PI / 180;
    const speed = 1 / (600 * 60);
    const dxPerFrame = Math.sin(driftAngle) * speed;
    const dyPerFrame = -Math.cos(driftAngle) * speed;
    let nebulaPhase = 0;
    function draw() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      nebulaPhase += 1e-3;
      if (!isLight) {
        const nebulaAlpha = 0.08 + 0.04 * Math.sin(nebulaPhase);
        const grad1 = ctx.createRadialGradient(
          canvas.width * 0.2,
          canvas.height * 0.3,
          0,
          canvas.width * 0.2,
          canvas.height * 0.3,
          canvas.width * 0.5
        );
        grad1.addColorStop(0, `rgba(40, 60, 140, ${nebulaAlpha})`);
        grad1.addColorStop(1, "transparent");
        ctx.fillStyle = grad1;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        const grad2 = ctx.createRadialGradient(
          canvas.width * 0.75,
          canvas.height * 0.7,
          0,
          canvas.width * 0.75,
          canvas.height * 0.7,
          canvas.width * 0.35
        );
        grad2.addColorStop(0, `rgba(100, 40, 80, ${nebulaAlpha * 0.6})`);
        grad2.addColorStop(1, "transparent");
        ctx.fillStyle = grad2;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
      }
      for (const s of stars) {
        s.xf += dxPerFrame;
        s.yf += dyPerFrame;
        if (s.xf > 1.05) s.xf -= 1.1;
        if (s.xf < -0.05) s.xf += 1.1;
        if (s.yf > 1.05) s.yf -= 1.1;
        if (s.yf < -0.05) s.yf += 1.1;
        s.wanderPhase += s.wanderSpeed;
        let dim = 1 + Math.sin(s.wanderPhase) * s.wanderAmp;
        if (s.doesTwinkle) {
          if (s.twinkleFlicker > 0) {
            s.twinkleFlicker--;
            dim *= s.twinkleDim;
          } else {
            s.twinkleTimer--;
            if (s.twinkleTimer <= 0) {
              s.twinkleFlicker = 3 + Math.floor(Math.random() * 8);
              s.twinkleDim = 0.3 + Math.random() * 0.4;
              s.twinkleTimer = 200 + Math.floor(Math.random() * 600);
              dim *= s.twinkleDim;
            }
          }
        }
        const alpha = s.brightness * dim;
        const x = s.xf * canvas.width;
        const y = s.yf * canvas.height;
        const l = 80 + s.brightness * 80;
        const color = isLight ? `rgba(40, 60, 100, ${alpha * 0.6})` : `hsla(${s.hue}, ${s.sat}%, ${l}%, ${alpha})`;
        ctx.beginPath();
        ctx.arc(x, y, s.r, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
        if (s.hasCross) {
          const spikeAlpha = alpha * 0.5;
          const spikeColor = isLight ? `rgba(40, 60, 100, ${spikeAlpha * 0.4})` : `hsla(${s.hue}, ${s.sat}%, ${l}%, ${spikeAlpha})`;
          ctx.save();
          ctx.translate(x, y);
          ctx.rotate(s.crossAngle);
          ctx.strokeStyle = spikeColor;
          ctx.lineWidth = 0.5;
          ctx.beginPath();
          ctx.moveTo(0, -s.crossLen);
          ctx.lineTo(0, s.crossLen);
          ctx.stroke();
          ctx.beginPath();
          ctx.moveTo(-s.crossLen, 0);
          ctx.lineTo(s.crossLen, 0);
          ctx.stroke();
          ctx.restore();
        }
      }
      state.spaceAnimId = requestAnimationFrame(draw);
    }
    state.spaceAnimId = requestAnimationFrame(draw);
  }
  function stopSpaceAnimation() { _stopAnim("spaceAnimId"); }

  // src/js/mobile.js
  var _isMobile = () => window.innerWidth <= 768;
  function setPaneHeight(h) {
    var vh = window.innerHeight;
    var clamped = Math.max(56, Math.min(vh * 0.9, h));
    document.body.style.setProperty("--pane-height", clamped + "px");
    var sidebar = document.getElementById("sidebar");
    sidebar.dataset.paneHeight = clamped;
    if (state.map) state.map.resize();
  }
  function setSheetState(sheetState) {
    var sidebar = document.getElementById("sidebar");
    var vh = window.innerHeight;
    var height;
    if (sheetState === "full") height = vh * 0.9;
    else if (sheetState === "half") height = vh * 0.5;
    else height = 56;
    sidebar.dataset.sheetState = sheetState || "closed";
    setPaneHeight(height);
    var preview = document.getElementById("map-preview");
    if (preview) preview.style.display = sheetState === "closed" ? "" : "none";
    var menuBtn = document.getElementById("mobile-menu-btn");
    if (menuBtn) menuBtn.innerHTML = sheetState === "closed" ? "&#9776;" : "&#9662;";
  }
  function toggleSheet() {
    const sidebar = document.getElementById("sidebar");
    const current = sidebar.dataset.sheetState || "closed";
    if (current === "closed") setSheetState("half");
    else setSheetState("closed");
  }
  function updateMobileBar() {
    if (!_isMobile()) return;
    const showingEl = document.getElementById("stat-showing");
    const mobileShowing = document.getElementById("mobile-stat-showing");
    if (showingEl && mobileShowing) {
      mobileShowing.textContent = showingEl.textContent;
    }
    const activeBtn = document.querySelector(".preset-btn.active");
    const nameEl = document.getElementById("mobile-preset-name");
    const dotEl = document.querySelector(".mobile-bar-preset-dot");
    if (activeBtn && nameEl) {
      const world = state.allPresets[activeBtn.dataset.world];
      nameEl.textContent = world ? world.label : activeBtn.textContent;
    }
    if (dotEl && activeBtn) {
      const presetId = activeBtn.dataset.world || "bright_side";
      const world = state.allPresets[presetId];
      dotEl.style.background = world ? world.color : "#c99700";
    }
    const filterDot = document.getElementById("mobile-filter-dot");
    if (filterDot && state._filterState) {
      filterDot.classList.toggle("active", !!state._filterState.hasFilters);
    }
  }
  function initMobileSheet() {
    if (!_isMobile()) return;
    document.body.style.setProperty("--pane-height", "56px");
    const sidebar = document.getElementById("sidebar");
    sidebar.dataset.paneHeight = 56;
    sidebar.dataset.sheetState = "closed";
    const mobileBar = document.getElementById("mobile-bar");
    const menuBtn = document.getElementById("mobile-menu-btn");
    const dragHandle = document.getElementById("drag-handle");
    function getHeights() {
      const vh = window.innerHeight;
      return { full: vh * 0.9, half: vh * 0.5, closed: 56 };
    }
    let touchStartY = 0;
    let startPaneHeight = 56;
    let currentHeight = 56;
    let isDragging = false;
    let dragActivated = false;
    let lastTouchY = 0;
    let lastTouchTime = 0;
    let velocity = 0;
    let dragOccurred = false;
    let rafPending = false;
    function requestMapResize() {
      if (rafPending) return;
      rafPending = true;
      requestAnimationFrame(() => { if (state.map) state.map.resize(); rafPending = false; });
    }
    function startDrag(clientY) {
      touchStartY = clientY;
      startPaneHeight = parseFloat(sidebar.dataset.paneHeight) || 56;
      currentHeight = startPaneHeight;
      isDragging = true;
      dragActivated = false;
      lastTouchY = clientY;
      lastTouchTime = performance.now();
      velocity = 0;
      dragOccurred = false;
    }
    function moveDrag(clientY) {
      if (!isDragging) return;
      const delta = clientY - touchStartY;
      if (!dragActivated && Math.abs(delta) > 5) {
        dragActivated = true;
        dragOccurred = true;
        document.body.classList.add("pane-dragging");
      }
      if (!dragActivated) return;
      const vh = window.innerHeight;
      currentHeight = Math.max(56, Math.min(vh * 0.9, startPaneHeight - delta));
      document.body.style.setProperty("--pane-height", currentHeight + "px");
      sidebar.dataset.paneHeight = currentHeight;
      requestMapResize();
      const now = performance.now();
      const dt = now - lastTouchTime;
      if (dt > 0) {
        const instantV = (clientY - lastTouchY) / dt;
        velocity = velocity * 0.4 + instantV * 0.6;
      }
      lastTouchY = clientY;
      lastTouchTime = now;
    }
    function endDrag() {
      if (!isDragging) return;
      isDragging = false;
      document.body.classList.remove("pane-dragging");
      if (!dragActivated) return;
      const heights = getHeights();
      const VELOCITY_THRESHOLD = 0.4;
      let targetState;
      if (Math.abs(velocity) > VELOCITY_THRESHOLD) {
        const current = sidebar.dataset.sheetState || "closed";
        if (velocity < 0) {
          targetState = current === "closed" ? "half" : "full";
        } else {
          targetState = current === "full" ? "half" : "closed";
        }
      } else {
        const distFull = Math.abs(currentHeight - heights.full);
        const distHalf = Math.abs(currentHeight - heights.half);
        const distClosed = Math.abs(currentHeight - heights.closed);
        if (distFull <= distHalf && distFull <= distClosed) targetState = "full";
        else if (distHalf <= distClosed) targetState = "half";
        else targetState = "closed";
      }
      setSheetState(targetState);
    }
    function cancelDrag() {
      isDragging = false;
      dragActivated = false;
      document.body.classList.remove("pane-dragging");
      setSheetState(sidebar.dataset.sheetState || "closed");
    }
    dragHandle.addEventListener("touchstart", (e) => {
      startDrag(e.touches[0].clientY);
    }, { passive: true });
    dragHandle.addEventListener("touchmove", (e) => {
      moveDrag(e.touches[0].clientY);
    }, { passive: true });
    dragHandle.addEventListener("touchend", endDrag);
    mobileBar.addEventListener("touchstart", (e) => {
      if (e.target === menuBtn || menuBtn.contains(e.target)) return;
      startDrag(e.touches[0].clientY);
    }, { passive: true });
    mobileBar.addEventListener("touchmove", (e) => {
      moveDrag(e.touches[0].clientY);
    }, { passive: true });
    mobileBar.addEventListener("touchend", () => {
      if (!dragOccurred) {
        cancelDrag();
        return;
      }
      endDrag();
    });
    mobileBar.addEventListener("click", (e) => {
      if (dragOccurred) {
        dragOccurred = false;
        return;
      }
      if (e.target === menuBtn || menuBtn.contains(e.target)) return;
      toggleSheet();
    });
    menuBtn.addEventListener("click", toggleSheet);
    const scrollables = [
      document.getElementById("narrative-list"),
      document.getElementById("event-list"),
      document.getElementById("story-list")
    ].filter(Boolean);
    scrollables.forEach((el) => {
      el.addEventListener("touchstart", (e) => {
        if (el.scrollTop <= 0) {
          startDrag(e.touches[0].clientY);
        }
      }, { passive: true });
      el.addEventListener("touchmove", (e) => {
        if (isDragging && currentHeight < startPaneHeight && el.scrollTop <= 0) {
          moveDrag(e.touches[0].clientY);
        } else if (isDragging) {
          cancelDrag();
        }
      }, { passive: true });
      el.addEventListener("touchend", () => {
        if (isDragging) endDrag();
      });
    });
    document.getElementById("map-container").addEventListener("click", () => {
      const current = sidebar.dataset.sheetState || "closed";
      if (current !== "closed") setSheetState("closed");
    });
  }
  function initMobileMapControls() {
    const mCtrlToggle = document.getElementById("mobile-ctrl-toggle");
    const mCtrlTray = document.getElementById("mobile-ctrl-tray");
    if (mCtrlToggle && mCtrlTray) {
      mCtrlToggle.addEventListener("click", (e) => {
        e.stopPropagation();
        mCtrlTray.classList.toggle("open");
      });
      document.addEventListener("click", (e) => {
        if (mCtrlTray.classList.contains("open") && !mCtrlTray.contains(e.target)) {
          mCtrlTray.classList.remove("open");
        }
      });
    }
    var mGlobe = document.getElementById("mobile-globe-btn");
    var mLabels = document.getElementById("mobile-labels-btn");
    var mTheme = document.getElementById("mobile-theme-btn");
    var mSpin = document.getElementById("mobile-spin-btn");
    var mReload = document.getElementById("mobile-reload-btn");
    if (mGlobe) mGlobe.addEventListener("click", toggleGlobe);
    if (mLabels) mLabels.addEventListener("click", toggleMapLabels);
    if (mTheme) mTheme.addEventListener("click", _toggleDotThemeMenu);
    if (mSpin) mSpin.addEventListener("click", () => { if (state.toggleAutoRotate) state.toggleAutoRotate(); });
    if (mReload) mReload.addEventListener("click", () => {
      mReload.classList.add("spinning");
      setTimeout(() => location.reload(), 300);
    });
  }
  function initInfoPanelSwipe(closeInfoPanel2) {
    if (!_isMobile()) return;
    const panel = document.getElementById("info-panel");
    const header = document.getElementById("info-panel-header");
    const stories = document.getElementById("info-panel-stories");
    let startY = 0, currentDelta = 0, isDragging = false, dragActivated = false;
    let velocity = 0, lastY = 0, lastTime = 0;
    function _start(clientY) {
      startY = clientY;
      currentDelta = 0;
      isDragging = true;
      dragActivated = false;
      lastY = clientY;
      lastTime = performance.now();
      velocity = 0;
    }
    function _move(clientY) {
      if (!isDragging) return;
      const delta = clientY - startY;
      if (!dragActivated && delta > 5) {
        dragActivated = true;
        panel.style.transition = "none";
        panel.style.willChange = "transform";
      }
      if (!dragActivated) return;
      currentDelta = Math.max(0, delta);
      panel.style.transform = `translateY(${currentDelta}px)`;
      const now = performance.now();
      const dt = now - lastTime;
      if (dt > 0) {
        velocity = velocity * 0.4 + (clientY - lastY) / dt * 0.6;
      }
      lastY = clientY;
      lastTime = now;
    }
    function _end() {
      if (!isDragging) return;
      isDragging = false;
      panel.style.willChange = "";
      if (!dragActivated) {
        panel.style.transition = "";
        panel.style.transform = "";
        return;
      }
      if (currentDelta > 80 || velocity > 0.4) {
        panel.style.transition = "transform 0.2s ease-in";
        panel.style.transform = "translateY(100%)";
        setTimeout(() => {
          closeInfoPanel2();
          panel.style.transition = "";
          panel.style.transform = "";
        }, 220);
      } else {
        panel.style.transition = "transform 0.2s ease-out";
        panel.style.transform = "translateY(0)";
        setTimeout(() => {
          panel.style.transition = "";
          panel.style.transform = "";
        }, 220);
      }
    }
    function _cancel() {
      isDragging = false;
      dragActivated = false;
      panel.style.willChange = "";
      panel.style.transition = "";
      panel.style.transform = "";
    }
    header.addEventListener("touchstart", (e) => _start(e.touches[0].clientY), { passive: true });
    header.addEventListener("touchmove", (e) => _move(e.touches[0].clientY), { passive: true });
    header.addEventListener("touchend", _end);
    stories.addEventListener("touchstart", (e) => {
      if (stories.scrollTop <= 0) _start(e.touches[0].clientY);
    }, { passive: true });
    stories.addEventListener("touchmove", (e) => {
      if (isDragging && currentDelta > 0 && stories.scrollTop <= 0) {
        _move(e.touches[0].clientY);
      } else if (isDragging) {
        _cancel();
      }
    }, { passive: true });
    stories.addEventListener("touchend", () => {
      if (isDragging) _end();
    });
  }

  // src/js/map-highlight.js
  function _showHoverHighlight(storyIds, domain) {
    if (!storyIds || !storyIds.length || !state.map.getSource("hover-highlight")) return;
    const idSet = new Set(storyIds);
    const features = state.geojsonData.features.filter((f) => idSet.has(f.properties.id));
    const palette = state.lightMode ? _DOMAIN_HIGHLIGHT_COLORS.light : _DOMAIN_HIGHLIGHT_COLORS.dark;
    const color = palette[domain] || palette.news;
    state.map.setPaintProperty("hover-highlight", "circle-color", color);
    state.map.setPaintProperty("hover-highlight", "circle-stroke-color", color);
    state.map.getSource("hover-highlight").setData({ type: "FeatureCollection", features });
  }
  function _clearHoverHighlight() {
    if (state.map.getSource("hover-highlight")) {
      state.map.getSource("hover-highlight").setData({ type: "FeatureCollection", features: [] });
    }
  }

  // src/js/map-labels.js
  function updateEventMapLabels(events, filteredIds) {
    if (!state.map.getSource("events-geo")) return;
    state._lastEventGeo = { type: "FeatureCollection", features: [] };
    state.map.getSource("events-geo").setData(state._lastEventGeo);
  }
  function updateCountryPolygons(clouds) {
    if (!state.map.getLayer("country-fill")) return;
    const activeCountries = /* @__PURE__ */ new Map();
    for (const f of clouds.features) {
      const tier = f.properties.tier;
      if (tier !== "small_country" && tier !== "large_country") continue;
      const locName = f.properties.country_name || f.properties.location_name;
      if (!locName) continue;
      const neName = COUNTRY_NAME_MAP[locName] || locName;
      if (!activeCountries.has(neName)) activeCountries.set(neName, { count: 0, categories: {} });
      const entry = activeCountries.get(neName);
      entry.count++;
      const dom = f.properties._domain || _featureDomain(f);
      entry.categories[dom] = (entry.categories[dom] || 0) + 1;
    }
    const countryNames = [...activeCountries.keys()];
    if (countryNames.length === 0) {
      state.map.setFilter("country-fill", ["in", ["get", "NAME"], ["literal", [""]]]);
      state.map.setFilter("country-outline", ["in", ["get", "NAME"], ["literal", [""]]]);
      return;
    }
    const filter = ["in", ["get", "NAME"], ["literal", countryNames]];
    state.map.setFilter("country-fill", filter);
    state.map.setFilter("country-outline", filter);
    const colorCases = ["match", ["get", "NAME"]];
    for (const [name, data] of activeCountries) {
      let maxCat = "general", maxCount = 0;
      for (const [cat, cnt] of Object.entries(data.categories)) {
        if (cnt > maxCount) {
          maxCat = cat;
          maxCount = cnt;
        }
      }
      colorCases.push(name, DOMAIN_COLORS[maxCat] || "#58a6ff");
    }
    colorCases.push("#58a6ff");
    state.map.setPaintProperty("country-fill", "fill-color", colorCases);
    state.map.setPaintProperty("country-outline", "line-color", colorCases);
  }
  function addMapLayers(m, srcPrefix) {
    const cloudSrc = srcPrefix + "stories-cloud";
    const countrySrc = srcPrefix + "countries";
    const eventsSrc = srcPrefix + "events-geo";
    m.addSource(cloudSrc, { type: "geojson", data: state.cloudData });
    m.addLayer({
      id: srcPrefix + "cloud-heat",
      type: "heatmap",
      source: cloudSrc,
      filter: [
        "all",
        ["!=", ["get", "tier"], "small_country"],
        ["!=", ["get", "tier"], "large_country"]
      ],
      paint: {
        "heatmap-weight": [
          "interpolate",
          ["linear"],
          ["get", "radius_km"],
          5,
          1,
          50,
          0.6,
          200,
          0.3,
          800,
          0.15
        ],
        "heatmap-intensity": [
          "interpolate",
          ["linear"],
          ["zoom"],
          0,
          0.6,
          3,
          0.8,
          6,
          1.2,
          10,
          1.5
        ],
        "heatmap-radius": [
          "interpolate",
          ["exponential", 2],
          ["zoom"],
          0,
          ["max", 4, ["*", ["get", "radius_km"], 0.015]],
          3,
          ["max", 8, ["*", ["get", "radius_km"], 0.12]],
          6,
          ["max", 15, ["*", ["get", "radius_km"], 1]],
          9,
          ["max", 25, ["*", ["get", "radius_km"], 6]]
        ],
        "heatmap-color": state.lightMode ? [
          "interpolate",
          ["linear"],
          ["heatmap-density"],
          0,
          "rgba(0, 0, 0, 0)",
          0.05,
          "rgba(9, 105, 218, 0.06)",
          0.15,
          "rgba(9, 105, 218, 0.14)",
          0.3,
          "rgba(9, 105, 218, 0.22)",
          0.5,
          "rgba(31, 111, 235, 0.30)",
          0.7,
          "rgba(31, 111, 235, 0.40)",
          1,
          "rgba(9, 105, 218, 0.55)"
        ] : [
          "interpolate",
          ["linear"],
          ["heatmap-density"],
          0,
          "rgba(0, 0, 0, 0)",
          0.05,
          "rgba(30, 80, 180, 0.08)",
          0.15,
          "rgba(50, 120, 220, 0.18)",
          0.3,
          "rgba(80, 160, 255, 0.30)",
          0.5,
          "rgba(100, 200, 240, 0.42)",
          0.7,
          "rgba(200, 220, 255, 0.55)",
          1,
          "rgba(255, 255, 255, 0.70)"
        ],
        "heatmap-opacity": [
          "interpolate",
          ["linear"],
          ["zoom"],
          0,
          0.9,
          10,
          0.7,
          14,
          0.4
        ]
      }
    });
    m.addLayer({
      id: srcPrefix + "cloud-points",
      type: "circle",
      source: cloudSrc,
      filter: ["==", ["get", "is_primary"], true],
      paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 0, 3, 6, 5, 10, 7],
        "circle-color": ["to-color", ["get", "blended_color"]],
        "circle-opacity": [
          "interpolate",
          ["linear"],
          ["get", "age_hours"],
          0,
          0.95,
          6,
          0.85,
          24,
          0.6,
          72,
          0.35
        ],
        "circle-stroke-width": 1,
        "circle-stroke-color": state.lightMode ? "rgba(0, 0, 0, 0.15)" : "rgba(255, 255, 255, 0.25)"
      }
    });
    m.addSource(srcPrefix + "proximity-highlight", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
    m.addLayer({
      id: srcPrefix + "proximity-highlight",
      type: "circle",
      source: srcPrefix + "proximity-highlight",
      paint: {
        "circle-radius": ["number", ["get", "radius"], 6],
        "circle-radius-transition": { duration: 100, delay: 0 },
        "circle-color": ["to-color", ["coalesce", ["get", "blended_color"], "#484f58"]],
        "circle-opacity": 0.9,
        "circle-opacity-transition": { duration: 150, delay: 0 },
        "circle-stroke-width": 1.5,
        "circle-stroke-color": state.lightMode ? "rgba(0, 0, 0, 0.3)" : "rgba(255, 255, 255, 0.5)"
      }
    });
    m.addSource(srcPrefix + "hover-highlight", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
    m.addLayer({
      id: srcPrefix + "hover-highlight",
      type: "circle",
      source: srcPrefix + "hover-highlight",
      paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 0, 5, 6, 8, 10, 12],
        "circle-color": state.lightMode ? "#0969da" : "#58a6ff",
        "circle-opacity": 0.6,
        "circle-stroke-width": 2,
        "circle-stroke-color": state.lightMode ? "#0969da" : "#58a6ff",
        "circle-stroke-opacity": 0.9
      }
    });
    m.addSource(srcPrefix + "pulse-source", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
    m.addLayer({
      id: srcPrefix + "pulse-ring",
      type: "circle",
      source: srcPrefix + "pulse-source",
      paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 0, 6, 6, 12, 10, 18],
        "circle-color": "transparent",
        "circle-stroke-width": 2,
        "circle-stroke-color": state.lightMode ? "#0969da" : "#58a6ff",
        "circle-stroke-opacity": 0.7
      }
    });
    m.addSource(countrySrc, { type: "geojson", data: "/static/data/countries-110m.json" });
    m.addLayer({
      id: srcPrefix + "country-fill",
      type: "fill",
      source: countrySrc,
      filter: ["in", ["get", "NAME"], ["literal", []]],
      paint: {
        "fill-color": "#58a6ff",
        "fill-opacity": state.lightMode ? 0.18 : 0.25
      }
    }, srcPrefix + "cloud-heat");
    m.addLayer({
      id: srcPrefix + "country-outline",
      type: "line",
      source: countrySrc,
      filter: ["in", ["get", "NAME"], ["literal", []]],
      paint: {
        "line-color": "#58a6ff",
        "line-width": 1.2,
        "line-opacity": state.lightMode ? 0.4 : 0.5
      }
    }, srcPrefix + "cloud-heat");
    m.addSource(eventsSrc, { type: "geojson", data: { type: "FeatureCollection", features: [] } });
    m.addLayer({
      id: srcPrefix + "event-labels",
      type: "symbol",
      source: eventsSrc,
      layout: {
        "text-field": ["get", "word"],
        "text-size": ["get", "size"],
        "text-font": ["Open Sans Bold"],
        "text-allow-overlap": false,
        "text-ignore-placement": false,
        "text-anchor": "center",
        "text-padding": 8,
        "text-max-width": 12,
        "text-rotate": ["get", "rotate"],
        "text-letter-spacing": 0.03
      },
      paint: {
        "text-color": state.lightMode ? "rgba(20,30,50,0.95)" : ["get", "color"],
        "text-halo-color": state.lightMode ? "rgba(255,255,255,0.9)" : "rgba(0,0,0,0.9)",
        "text-halo-width": 2,
        "text-opacity": ["interpolate", ["linear"], ["zoom"], 0, 0.55, 3, 0.85, 6, 1]
      }
    });
  }

  // src/js/stats.js
  function showNewBadge(count) {
    const badge = document.getElementById("new-badge");
    badge.textContent = `${count} new ${count === 1 ? "story" : "stories"}`;
    badge.classList.add("visible");
    if (document.hidden) document.title = `(${count}) thisminute`;
    clearTimeout(badge._hideTimer);
    badge._hideTimer = setTimeout(() => {
      badge.classList.remove("visible");
      state.pendingNewCount = 0;
      document.title = "thisminute \u2014 global news, live";
    }, 8e3);
  }
  function triggerPulse(storyIds) {
    if (!state.map || !storyIds.length) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const idSet = new Set(storyIds);
    const pulseFeatures = (state.cloudData.features || []).filter(
      (f) => f.properties.is_primary && idSet.has(f.properties.story_id)
    );
    if (!pulseFeatures.length) return;
    const src = state.map.getSource("pulse-source");
    if (!src) return;
    src.setData({ type: "FeatureCollection", features: pulseFeatures });
    if (state._pulseAnimId) clearInterval(state._pulseAnimId);
    state._pulsePhase = 0;
    state._pulseAnimId = setInterval(() => {
      state._pulsePhase += 0.05;
      if (state._pulsePhase >= 1) {
        clearInterval(state._pulseAnimId);
        state._pulseAnimId = null;
        src.setData({ type: "FeatureCollection", features: [] });
        return;
      }
      const ease = 1 - Math.pow(1 - state._pulsePhase, 2);
      const baseRadius = 6 + ease * 20;
      const opacity = 0.7 * (1 - ease);
      try {
        state.map.setPaintProperty("pulse-ring", "circle-stroke-opacity", opacity);
        state.map.setPaintProperty("pulse-ring", "circle-radius", [
          "interpolate",
          ["linear"],
          ["zoom"],
          0,
          baseRadius * 0.5,
          6,
          baseRadius,
          10,
          baseRadius * 1.5
        ]);
      } catch (_) {
      }
    }, 100);
  }
  function _animateCount(el, target) {
    if (!el) return;
    const current = parseInt(el.textContent.replace(/,/g, "")) || 0;
    if (current === target || isNaN(target)) {
      el.textContent = target.toLocaleString();
      return;
    }
    const diff = target - current;
    const steps = Math.min(Math.abs(diff), 20);
    const increment = diff / steps;
    let step = 0;
    const interval = setInterval(() => {
      step++;
      const val = step >= steps ? target : Math.round(current + increment * step);
      el.textContent = val.toLocaleString();
      if (step >= steps) clearInterval(interval);
    }, 30);
  }
  function updateFreshnessIndicator() {
    const el = document.getElementById("stat-freshness");
    if (!el || !state._lastDataUpdate) return;
    const sec = Math.floor((Date.now() - state._lastDataUpdate) / 1e3);
    if (sec < 10) {
      el.textContent = "live";
      el.classList.add("live");
      el.classList.remove("stale");
    } else if (sec < 60) {
      el.textContent = `${sec}s ago`;
      el.classList.remove("live", "stale");
    } else if (sec < 180) {
      el.textContent = `${Math.floor(sec / 60)}m ago`;
      el.classList.remove("live", "stale");
    } else {
      el.textContent = `${Math.floor(sec / 60)}m ago`;
      el.classList.remove("live");
      el.classList.add("stale");
    }
  }

  // src/js/store.js
  function _getPresetDomain(presetId) {
    return PRESET_DOMAIN_MAP[presetId] || null;
  }
  function computeFilteredState() {
    const searchText = (document.getElementById("search-box").value || "").trim().toLowerCase();
    const timeHours = parseFloat(document.getElementById("filter-time").value) || 0;
    const hideOpinion = document.getElementById("filter-opinion")?.checked || false;
    const now = Date.now();
    const originFiltering = state.activeOrigins.size < 15;
    const hasFilters = state.activeConcepts.size > 0 || state.excludedConcepts.size > 0 || state.activeSources.size > 0 || state.excludedSources.size > 0 || originFiltering || state.brightSideMode || state.curiousMode || searchText || timeHours || hideOpinion;
    const storyIds = hasFilters ? /* @__PURE__ */ new Set() : null;
    const features = [];
    const topicCounts = {};
    const sourceCountMap = {};
    const feedCounts = { space: 0, internet: 0 };
    for (const f of state.geojsonData.features) {
      const p = f.properties;
      let concepts = p.concepts;
      if (typeof concepts === "string") try {
        concepts = JSON.parse(concepts);
      } catch {
        concepts = [];
      }
      concepts = concepts || [];
      if (hasFilters) {
        if (timeHours > 0) {
          const storyTime = new Date(p.published_at || p.scraped_at).getTime();
          if (now - storyTime > timeHours * 36e5) continue;
        }
        if (hideOpinion && p.is_opinion) continue;
        if (state.activeSources.size > 0 && !state.activeSources.has(p.source)) continue;
        if (state.excludedSources.has(p.source)) continue;
        if (originFiltering && !state.activeOrigins.has(p.origin || "rss")) continue;
        if (searchText) {
          const kw = Array.isArray(p.search_keywords) ? p.search_keywords.join(" ") : "";
          const haystack = `${p.title || ""} ${p.summary || ""} ${p.location_name || ""} ${kw}`.toLowerCase();
          const terms = searchText.split(/\s+/).filter((t) => t.length > 0);
          if (!terms.every((term) => haystack.includes(term))) continue;
        }
        if (state.brightSideMode) {
          const score = p.bright_side_score;
          if (!score || parseInt(score) < BRIGHT_SIDE_MIN_SCORE) continue;
          if (_hasVetoTopic(concepts)) continue;
        }
        if (state.curiousMode) {
          const hiScore = p.human_interest_score;
          if (!hiScore || parseInt(hiScore) < CURIOUS_MIN_SCORE) continue;
          if (_hasVetoTopic(concepts)) continue;
        }
        if (state.excludedConcepts.size > 0) {
          if (concepts.length === 0) continue;
          let excluded = false;
          for (const ex of state.excludedConcepts) {
            if (concepts.includes(ex)) {
              excluded = true;
              break;
            }
          }
          if (excluded) continue;
        }
        if (state.activeConcepts.size > 0) {
          let matched = false;
          for (const inc of state.activeConcepts) {
            if (concepts.includes(inc)) {
              matched = true;
              break;
            }
          }
          if (!matched) continue;
        }
        storyIds.add(p.id);
      }
      features.push(f);
      for (const c of concepts) {
        topicCounts[c] = (topicCounts[c] || 0) + 1;
      }
      if (p.source) {
        sourceCountMap[p.source] = (sourceCountMap[p.source] || 0) + 1;
      }
      const locType = p.location_type || "terrestrial";
      if (locType === "space" || concepts.includes("space")) feedCounts.space++;
      if (locType === "internet" || concepts.includes("cyber") || concepts.includes("internet") || concepts.includes("AI")) feedCounts.internet++;
    }
    const clouds = storyIds ? { type: "FeatureCollection", features: state.cloudData.features.filter((f) => storyIds.has(f.properties.story_id)) } : state.cloudData;
    const contentFiltering = state.activeConcepts.size > 0 || state.excludedConcepts.size > 0 || state.activeSources.size > 0 || state.excludedSources.size > 0 || originFiltering || state.brightSideMode || state.curiousMode || searchText;
    const events = contentFiltering && storyIds ? state.eventsData.filter((ev) => ev.story_ids && ev.story_ids.some((id) => storyIds.has(id))) : [...state.eventsData];
    if (state.eventSortMode === "new") {
      events.sort((a, b) => new Date(b.last_updated || 0).getTime() - new Date(a.last_updated || 0).getTime());
    } else if (state.eventSortMode === "broadest") {
      events.sort((a, b) => (b.source_count || 0) - (a.source_count || 0) || (b.story_count || 0) - (a.story_count || 0));
    } else {
      events.sort((a, b) => (b.story_count || 0) - (a.story_count || 0));
    }
    const allStoryIds = new Set(state.geojsonData.features.map((f) => f.properties.id));
    let narratives = (state.narrativesData || []).map((n) => ({
      ...n,
      filteredCount: contentFiltering && storyIds && n.story_ids ? n.story_ids.filter((id) => storyIds.has(id)).length : n.story_ids ? n.story_ids.filter((id) => allStoryIds.has(id)).length || n.story_count : n.story_count
    }));
    const presetDomain = _getPresetDomain(state.activePresetId);
    if (_DOMAINLESS_HIDE_SITUATIONS.has(state.activePresetId)) {
      narratives = [];
    } else if (presetDomain) {
      narratives = narratives.filter((n) => (n.domain || "news") === presetDomain);
    }
    if (state.brightSideMode && !presetDomain) {
      narratives = narratives.filter((n) => (n.bright_side_count || 0) > 0);
    }
    if (searchText) {
      const searchTerms = searchText.split(/\s+/).filter((t) => t.length > 0);
      narratives = narratives.filter((n) => {
        const haystack = `${n.title || ""} ${n.description || ""} ${(n.theme_tags || []).join(" ")}`.toLowerCase();
        return searchTerms.every((term) => haystack.includes(term));
      });
    }
    if (contentFiltering && storyIds && !presetDomain) {
      narratives = narratives.filter((n) => n.filteredCount > 0);
    }
    if (state.narrativeSortMode === "new") {
      narratives.sort((a, b) => new Date(b.last_updated || 0).getTime() - new Date(a.last_updated || 0).getTime());
    } else if (state.narrativeSortMode === "broadest") {
      narratives.sort((a, b) => (b.source_count || 0) - (a.source_count || 0) || b.filteredCount - a.filteredCount);
    } else if (state.narrativeSortMode === "growing") {
      const recentCutoff = Date.now() - 6 * 60 * 60 * 1e3;
      const storyTimeMap = /* @__PURE__ */ new Map();
      for (const f of state.geojsonData.features) {
        const p = f.properties;
        storyTimeMap.set(p.id, new Date(p.published_at || p.scraped_at || 0).getTime());
      }
      narratives.forEach((n) => {
        n._recentCount = (n.story_ids || []).filter((id) => (storyTimeMap.get(id) || 0) > recentCutoff).length;
      });
      narratives.sort((a, b) => (b._recentCount || 0) - (a._recentCount || 0) || b.filteredCount - a.filteredCount);
    } else if (state.narrativeSortMode === "longest") {
      narratives.sort((a, b) => new Date(a.first_seen || 0).getTime() - new Date(b.first_seen || 0).getTime());
    } else {
      narratives.sort((a, b) => b.filteredCount - a.filteredCount);
    }
    const sortedSourceCounts = Object.entries(sourceCountMap).map(([source, count]) => ({ source, count })).sort((a, b) => b.count - a.count);
    return {
      storyIds,
      features,
      clouds,
      events,
      narratives,
      topicCounts,
      sourceCounts: sortedSourceCounts,
      feedCounts,
      stats: {
        showing: features.length,
        sources: Object.keys(sourceCountMap).length
      },
      hasFilters
    };
  }

  // src/js/main.js
  state.activeFeedPanel = null;
  state.networkAnimId = null;
  state.spaceAnimId = null;
  state._feedTagsReady = null;
  state._lastDataUpdate = null;
  state._pulseAnimId = null;
  state._pulsePhase = 0;
  state.currentView = "narratives";
  state.expandedEventStories = [];
  state.activeNarrativeId = null;
  state.narrativeSortMode = "volume";
  state.eventSortMode = "volume";
  state.storySortMode = "new";
  state._pendingSituationId = null;
  state._pendingMapView = null;
  state.activeLocationFilter = null;
  state.lightMode = localStorage.getItem("thisminute-theme") === "light";
  state.dotColorTheme = localStorage.getItem("tm_dot_theme") || "domain";
  function _markVisited(url) {
    if (!url || state._visitedStories.has(url)) return;
    state._visitedStories.add(url);
    if (state._visitedStories.size > _VISITED_MAX) {
      const arr = [...state._visitedStories];
      state._visitedStories = new Set(arr.slice(arr.length - _VISITED_MAX));
    }
    localStorage.setItem(_VISITED_KEY, JSON.stringify([...state._visitedStories]));
  }
  var _introSpinActive = false;
  function _startIntroSpin() {
    if (state.currentProjection !== "globe") return;
    _introSpinActive = true;
    // Target: user's saved position, or a pleasant default
    var target = state._pendingMapView;
    var targetLon = target ? target.lon : 20 + Math.random() * 40;
    var targetLat = target ? target.lat : 15 + Math.random() * 25;
    var targetZoom = target ? target.zoom : (_isFirstVisitForTour ? 1.8 : 2.2);
    if (target) state._pendingMapView = null; // consume it — we'll land there ourselves
    // Start: random longitude, calculate spin to arrive at target
    var startLon = targetLon - 400 - Math.random() * 200; // spin 400-600 degrees to reach target
    var startLat = 0;
    var startZoom = 0.05;
    // Overshoot zoom then settle (breathe effect)
    var midZoom = Math.min(targetZoom + 1.2, 4.5); // overshoot
    var endZoom = targetZoom;
    // Spin: calculate initial velocity and friction so we land near targetLon
    // With friction f, total distance = v0 / (1 - f). Solve for v0:
    var totalSpin = targetLon - startLon;
    var spinFriction = 0.982;
    var spinVelocity = totalSpin * (1 - spinFriction); // v0 = distance * (1 - friction)
    // Timing
    var zoomInDuration = 3000;
    var zoomOutDuration = 2000;
    var totalZoomDuration = zoomInDuration + zoomOutDuration;
    var zoomStart = performance.now();
    var lon = startLon;
    var lat = startLat;
    state.map.jumpTo({ center: [lon, lat], zoom: startZoom });
    function frame(now) {
      if (!_introSpinActive) return;
      var elapsed = now - zoomStart;
      var zoom;
      if (elapsed < zoomInDuration) {
        var t = elapsed / zoomInDuration;
        var ease = 1 - Math.pow(1 - t, 3.5);
        zoom = startZoom + (midZoom - startZoom) * ease;
      } else {
        var t2 = Math.min(1, (elapsed - zoomInDuration) / zoomOutDuration);
        var ease2 = t2 * t2 * (3 - 2 * t2); // smoothstep
        zoom = midZoom + (endZoom - midZoom) * ease2;
      }
      // Spin with friction — converges toward targetLon
      lon += spinVelocity;
      spinVelocity *= spinFriction;
      // Latitude eases toward target
      var latT = Math.min(1, elapsed / (zoomInDuration * 0.8));
      var latEase = 1 - Math.pow(1 - latT, 4);
      lat = startLat + (targetLat - startLat) * latEase;
      state.map.jumpTo({ center: [lon, lat], zoom: zoom });
      var zoomDone = elapsed >= totalZoomDuration;
      if (!zoomDone || spinVelocity > 0.005) {
        requestAnimationFrame(frame);
      } else {
        // Snap to exact target at the end
        state.map.jumpTo({ center: [targetLon, targetLat], zoom: endZoom });
        _introSpinActive = false;
      }
    }
    requestAnimationFrame(frame);
    var stopEvents = ["click", "mousedown", "touchstart", "wheel"];
    function stopSpin() {
      _introSpinActive = false;
      stopEvents.forEach(function(ev) { document.removeEventListener(ev, stopSpin, true); });
    }
    stopEvents.forEach(function(ev) { document.addEventListener(ev, stopSpin, true); });
  }
  function initMap() {
    state.map = new maplibregl.Map({
      container: "map",
      style: state.lightMode ? "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json" : "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
      center: [20, 30],
      zoom: 1.0,
      minZoom: 0,
      maxZoom: 18
    });
    state.map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    state.map.on("style.load", () => {
      state.map.setProjection({ type: state.currentProjection });
      _startIntroSpin();
    });
    const _prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let _autoRotate = !_prefersReducedMotion;
    let _rotateId = null;
    function startAutoRotate() {
      if (_rotateId || !_autoRotate || _introSpinActive) return;
      _rotateId = setInterval(() => {
        if (!_autoRotate || state.currentProjection !== "globe" || _introSpinActive) {
          stopAutoRotate();
          return;
        }
        const center = state.map.getCenter();
        state.map.setCenter([center.lng + 0.05, center.lat], { duration: 0 });
      }, 50);
    }
    function stopAutoRotate() {
      _autoRotate = false;
      if (_rotateId) {
        clearInterval(_rotateId);
        _rotateId = null;
      }
      _updateSpinBtn();
    }
    function toggleAutoRotate() {
      if (_autoRotate) {
        stopAutoRotate();
      } else {
        _autoRotate = true;
        startAutoRotate();
      }
      _updateSpinBtn();
    }
    function _updateSpinBtn() {
      document.querySelectorAll(".spin-toggle-btn").forEach(function(b) {
        b.classList.toggle("active", _autoRotate);
      });
    }
    state.toggleAutoRotate = toggleAutoRotate;
    state.map.on("mousedown", stopAutoRotate);
    state.map.on("touchstart", stopAutoRotate);
    state.map.on("wheel", stopAutoRotate);
    state.map.once("load", () => {
      startAutoRotate();
      setTimeout(stopAutoRotate, 2e4);
    });
    state.map.on("zoomend", () => {
      if (state.globeManualOverride !== null) return;
      const zoom = state.map.getZoom();
      if (zoom >= 5 && state.currentProjection === "globe") {
        applyProjection("mercator");
      } else if (zoom < 1.5 && state.currentProjection === "mercator") {
        applyProjection("globe");
      }
    });
    let _moveTimer = null;
    state.map.on("moveend", () => {
      clearTimeout(_moveTimer);
      _moveTimer = setTimeout(saveStateToURL, 500);
    });
    state.map.on("load", onMapLoad);
  }
  function applyProjection(type) {
    state.currentProjection = type;
    state.map.setProjection({ type });
    updateGlobeButton();
  }
  state.mapLabelsVisible = false;
  function setMapLabelsVisible(visible) {
    state.mapLabelsVisible = visible;
    const vis = visible ? "visible" : "none";
    for (const layer of state.map.getStyle().layers) {
      if (layer.type === "symbol" && /label|place|country|city|town|state|capital/i.test(layer.id)) {
        if (layer.id === "event-labels") continue;
        state.map.setLayoutProperty(layer.id, "visibility", vis);
      }
    }
    const btn = document.getElementById("labels-toggle");
    if (btn) btn.classList.toggle("active", visible);
  }
  function toggleMapLabels() {
    setMapLabelsVisible(!state.mapLabelsVisible);
  }
  function toggleGlobe() {
    if (state.mapHidden) {
      setMapVisible(true);
      state.globeManualOverride = "globe";
      applyProjection("globe");
    } else if (state.currentProjection === "globe") {
      state.globeManualOverride = "mercator";
      applyProjection("mercator");
    } else {
      setMapVisible(false);
    }
  }
  function setMapVisible(visible) {
    state.mapHidden = !visible;
    const mapContainer = document.getElementById("map-container");
    if (!visible) {
      const rect = mapContainer.getBoundingClientRect();
      mapContainer.style.position = "absolute";
      mapContainer.style.top = rect.top + "px";
      mapContainer.style.right = "0";
      mapContainer.style.width = rect.width + "px";
      mapContainer.style.height = rect.height + "px";
      mapContainer.style.transition = "opacity 0.4s ease";
      document.body.classList.add("map-hidden");
      if (_isMobile()) setSheetState("full");
      requestAnimationFrame(() => {
        mapContainer.style.opacity = "0";
      });
      setTimeout(() => {
        mapContainer.style.position = "";
        mapContainer.style.top = "";
        mapContainer.style.right = "";
        mapContainer.style.width = "";
        mapContainer.style.height = "";
        mapContainer.style.transition = "";
        mapContainer.style.opacity = "";
      }, 550);
    } else {
      mapContainer.style.opacity = "0";
      mapContainer.style.transition = "opacity 0.4s ease";
      document.body.classList.remove("map-hidden");
      requestAnimationFrame(() => {
        mapContainer.style.opacity = "";
      });
      setTimeout(() => {
        mapContainer.style.transition = "";
        if (state.map) state.map.resize();
      }, 550);
    }
    updateGlobeButton();
  }
  function resetGlobeAuto() {
    if (state.mapHidden) setMapVisible(true);
    state.globeManualOverride = null;
    const zoom = state.map.getZoom();
    applyProjection(zoom < 5 ? "globe" : "mercator");
  }
  function updateGlobeButton() {
    const btn = document.getElementById("globe-toggle");
    if (state.mapHidden) {
      btn.innerHTML = "&#127758;";
      btn.title = "Show globe (g)";
      btn.classList.remove("flat-mode");
      btn.classList.add("no-map-mode");
      return;
    }
    btn.classList.remove("no-map-mode");
    const isGlobe = state.currentProjection === "globe";
    btn.innerHTML = isGlobe ? "&#9649;" : "&#10005;";
    btn.classList.toggle("flat-mode", !isGlobe);
    btn.title = isGlobe ? "Switch to flat map (g)" : "Hide map (g)";
  }
  function showLoadingBar() {
    const bar = document.getElementById("loading-bar");
    if (bar) bar.classList.remove("hidden");
  }
  function hideLoadingBar() {
    const bar = document.getElementById("loading-bar");
    if (!bar) return;
    bar.classList.add("hidden");
    setTimeout(() => bar.remove(), 600);
  }
  async function onMapLoad() {
    addMapLayers(state.map, "");
    addMapInteractions(state.map, "");
    setMapLabelsVisible(false);
    showLoadingBar();
    const quickStoriesP = loadAll(300);
    const conceptsP = loadConcepts();
    const sourcesP = loadSources();
    const eventsP = loadEvents();
    const overviewP = loadPresetOverview();
    const narrativesP = loadNarratives();
    await Promise.allSettled([quickStoriesP, conceptsP, sourcesP, eventsP, overviewP, narrativesP]);
    hideLoadingBar();
    if (state._pendingMapView && state.map) {
      _introSpinActive = false;
      state.map.jumpTo({ center: [state._pendingMapView.lon, state._pendingMapView.lat], zoom: state._pendingMapView.zoom });
      state._pendingMapView = null;
    }
    // Don't kill intro spin here — let it finish naturally or stop on user interaction
    startPresetTour();
    if (!_presetTourActive) {
      showOnboardingHint();
      if (_isMobile() && !localStorage.getItem("thisminute-onboarded")) {
        setTimeout(() => {
          setSheetState("half");
          setTimeout(() => setSheetState("closed"), 1500);
        }, 2e3);
      }
    }
    loadRemainingStories();
  }
  function showOnboardingHint() {
    if (localStorage.getItem("thisminute-onboarded")) return;
    const hint = document.createElement("div");
    hint.id = "onboarding-hint";
    hint.innerHTML = _isMobile() ? "Tap a situation to explore &middot; Swipe to browse &middot; Try different presets above" : "Click a situation to explore &middot; Use <kbd>j</kbd>/<kbd>k</kbd> to navigate &middot; <kbd>?</kbd> for shortcuts";
    document.getElementById("sidebar").appendChild(hint);
    const dismiss = () => {
      hint.classList.add("dismissed");
      setTimeout(() => hint.remove(), 300);
      localStorage.setItem("thisminute-onboarded", "1");
      document.removeEventListener("click", dismiss);
    };
    setTimeout(() => document.addEventListener("click", dismiss), 1e3);
    setTimeout(dismiss, 15e3);
  }
  function getHoverTooltip() {
    if (!state.hoverTooltipEl) {
      state.hoverTooltipEl = document.createElement("div");
      state.hoverTooltipEl.id = "hover-tooltip";
      document.body.appendChild(state.hoverTooltipEl);
    }
    return state.hoverTooltipEl;
  }
  function showHoverTooltip(point, features) {
    const tooltip = getHoverTooltip();
    const seen = /* @__PURE__ */ new Set();
    const all = [];
    for (const f of features) {
      const sid = f.properties.story_id;
      if (!seen.has(sid)) {
        seen.add(sid);
        all.push(f);
      }
    }
    _sortInfoStories(all, state.storySortMode);
    const unique = all.slice(0, 5);
    const lines = unique.map((f) => {
      const p = f.properties;
      const color = DOMAIN_COLORS[p.category] || "#484f58";
      const time = formatTime(p.published_at || p.scraped_at);
      const meta = [];
      if (p.source) meta.push(escapeHtml(p.source));
      if (time) meta.push(time);
      if (p.location_name) meta.push(escapeHtml(p.location_name));
      const metaHtml = meta.length ? ` <span class="hover-meta">${meta.join(" \xB7 ")}</span>` : "";
      return `<div class="hover-story"><span class="hover-dot" style="background:${color}"></span>${escapeHtml(truncateRaw(p.title, 55))}${metaHtml}</div>`;
    });
    if (all.length > 5) {
      lines.push(`<div class="hover-more">+${all.length - 5} more</div>`);
    }
    tooltip.innerHTML = lines.join("");
    tooltip.classList.add("visible");
    tooltip.style.left = point.x + 16 + "px";
    tooltip.style.top = point.y - 10 + "px";
    const rect = tooltip.getBoundingClientRect();
    if (rect.right > window.innerWidth - 10) tooltip.style.left = point.x - rect.width - 16 + "px";
    if (rect.bottom > window.innerHeight - 10) tooltip.style.top = point.y - rect.height - 10 + "px";
  }
  function hideHoverTooltip() {
    if (state.hoverTooltipEl) state.hoverTooltipEl.classList.remove("visible");
  }
  function _sortInfoStories(unique, sortMode) {
    if (sortMode === "old") {
      unique.sort((a, b) => {
        const ta = new Date(a.properties.published_at || a.properties.scraped_at || 0).getTime();
        const tb = new Date(b.properties.published_at || b.properties.scraped_at || 0).getTime();
        return ta - tb;
      });
    } else if (sortMode === "sources") {
      unique.sort((a, b) => {
        const sa = (a.properties.source || "").toLowerCase();
        const sb = (b.properties.source || "").toLowerCase();
        return sa < sb ? -1 : sa > sb ? 1 : 0;
      });
    } else {
      unique.sort((a, b) => {
        const ta = new Date(b.properties.published_at || b.properties.scraped_at || 0).getTime();
        const tb = new Date(a.properties.published_at || a.properties.scraped_at || 0).getTime();
        return ta - tb;
      });
    }
  }
  function _renderInfoStories(unique, headerHtml, events) {
    const panelStories = document.getElementById("info-panel-stories");
    const searchQ = (document.getElementById("search-box").value || "").trim();
    function _renderCard(f) {
      const p = f.properties;
      let concepts = p.concepts;
      if (typeof concepts === "string") try {
        concepts = JSON.parse(concepts);
      } catch {
        concepts = [];
      }
      const tags = (concepts || []).slice(0, 3).map((c) => {
        const domain = state.conceptDomainMap[c] || "general";
        const color = DOMAIN_COLORS[domain] || "#484f58";
        return `<span class="story-concept-tag clickable" style="background:${color}" data-concept="${escapeHtml(c)}">${c}</span>`;
      }).join(" ");
      const timeIso = p.published_at || p.scraped_at;
      const time = formatTime(timeIso);
      const fullTime = formatFullTime(timeIso);
      const rawSummary = p.summary ? escapeHtml(truncateRaw(p.summary, 200)) : "";
      const displayTitle = p.translated_title || p.title;
      const titleHtml = _highlightText(escapeHtml(displayTitle), searchQ);
      const originalLine = p.translated_title ? `<div class="info-card-original">${_highlightText(escapeHtml(p.title), searchQ)}</div>` : "";
      const summaryHtml = _highlightText(rawSummary, searchQ);
      const [lon, lat] = f.geometry.coordinates;
      const img = p.image_url ? `<img class="info-card-img" src="${escapeHtml(p.image_url)}" loading="lazy" alt="" onload="this.classList.add('loaded')" onerror="this.remove()">` : "";
      const favicon = _getFavicon(p.url);
      const visited = state._visitedStories.has(p.url) ? " visited" : "";
      return `<div class="info-card${img ? " has-image" : ""}${visited}" data-story-id="${p.story_id || p.id}" data-lon="${lon}" data-lat="${lat}">
                ${img}
                <div class="info-card-body">
                    <div class="info-card-title">${titleHtml}</div>
                    ${originalLine}
                    <div class="info-card-meta">
                        ${favicon}<span class="story-source clickable" data-source="${escapeHtml(p.source)}">${escapeHtml(p.source)}</span>
                        ${tags}
                        <span class="story-time" data-time="${escapeHtml(timeIso || "")}" title="${escapeHtml(fullTime)}">${time}</span>
                    </div>
                    ${summaryHtml ? `<div class="info-card-summary">${summaryHtml}</div>` : ""}
                    <div class="info-card-actions">
                        <a class="info-card-link" href="${escapeHtml(p.url)}" target="_blank" rel="noopener">Read full story</a>
                        <button class="info-card-copy" data-url="${escapeHtml(p.url)}" title="Copy link">&#128279;</button>
                        <button class="info-card-feedback feedback-btn" data-fb-type="story" data-fb-id="${p.id}" data-fb-title="${escapeHtml(p.title)}" title="Report story">&#9873;</button>
                    </div>
                </div>
            </div>`;
    }
    let html;
    if (events && events.length > 0 && state.storySortMode === "new") {
      const storyMap = /* @__PURE__ */ new Map();
      for (const f of unique) {
        const sid = f.properties.story_id || f.properties.id;
        storyMap.set(sid, f);
      }
      const rendered = /* @__PURE__ */ new Set();
      const parts = [];
      for (const ev of events) {
        const evStories = (ev.story_ids || []).map((sid) => storyMap.get(sid)).filter(Boolean);
        if (evStories.length === 0) continue;
        evStories.sort((a, b) => {
          const ta = new Date(b.properties.published_at || b.properties.scraped_at || 0).getTime();
          const tb = new Date(a.properties.published_at || a.properties.scraped_at || 0).getTime();
          return ta - tb;
        });
        const evTime = ev.last_updated ? formatTime(ev.last_updated) : "";
        parts.push(`<div class="info-event-group-header">
                <span class="info-event-group-title">${escapeHtml(ev.title)}</span>
                <span class="info-event-group-count">${evStories.length}</span>
                ${evTime ? `<span class="info-event-group-time" data-time="${escapeHtml(ev.last_updated)}">${evTime}</span>` : ""}
            </div>`);
        for (const f of evStories) {
          parts.push(_renderCard(f));
          rendered.add(f.properties.story_id || f.properties.id);
        }
      }
      const unmatched = unique.filter((f) => !rendered.has(f.properties.story_id || f.properties.id));
      if (unmatched.length > 0) {
        if (rendered.size > 0) parts.push('<div class="info-event-group-header"><span class="info-event-group-title">Other</span></div>');
        for (const f of unmatched) parts.push(_renderCard(f));
      }
      html = parts.join("");
    } else {
      const useTimeGroups = state.storySortMode !== "sources";
      const now = /* @__PURE__ */ new Date();
      const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
      const yesterdayStart = todayStart - 864e5;
      let lastGroup = "";
      html = unique.map((f) => {
        let groupHeader = "";
        if (useTimeGroups && unique.length > 3) {
          const timeIso = f.properties.published_at || f.properties.scraped_at;
          const storyTime = new Date(timeIso || 0).getTime();
          const group = storyTime >= todayStart ? "Today" : storyTime >= yesterdayStart ? "Yesterday" : "Older";
          if (group !== lastGroup) {
            lastGroup = group;
            groupHeader = `<div class="info-panel-time-group">${group}</div>`;
          }
        }
        return groupHeader + _renderCard(f);
      }).join("");
    }
    panelStories.innerHTML = headerHtml + html;
    const mapBtn = panelStories.querySelector(".info-panel-map-btn");
    if (mapBtn) {
      mapBtn.addEventListener("click", () => _flyToFeatures(unique));
    }
    panelStories.querySelectorAll(".info-card").forEach((card) => {
      card.addEventListener("click", (e) => {
        if (e.target.classList.contains("info-card-link") || e.target.classList.contains("info-card-copy") || e.target.classList.contains("info-card-feedback")) return;
        if (e.target.classList.contains("story-concept-tag") && e.target.dataset.concept) {
          e.stopPropagation();
          const concept = e.target.dataset.concept;
          state.activeConcepts.clear();
          state.activeConcepts.add(concept);
          applyFilters();
          markPresetModified();
          return;
        }
        if (e.target.classList.contains("story-source") && e.target.dataset.source) {
          e.stopPropagation();
          state.activeSources.clear();
          state.activeSources.add(e.target.dataset.source);
          applyFilters();
          markPresetModified();
          return;
        }
        const lon = parseFloat(card.dataset.lon);
        const lat = parseFloat(card.dataset.lat);
        if (!isNaN(lon) && !isNaN(lat)) state.map.flyTo({ center: [lon, lat], zoom: 6, duration: 1200 });
        scrollToStory(parseInt(card.dataset.storyId));
      });
    });
    panelStories.querySelectorAll(".info-card-link").forEach((link) => {
      link.addEventListener("click", () => {
        _markVisited(link.href);
        link.closest(".info-card")?.classList.add("visited");
      });
    });
    panelStories.querySelectorAll(".info-card-copy").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        _copyToClipboard(btn, btn.dataset.url);
      });
    });
    _wireFeedbackButtons(panelStories);
  }
  function openInfoPanel(title, features, loading, opts) {
    const panel = document.getElementById("info-panel");
    const panelTitle = document.getElementById("info-panel-title");
    const panelStories = document.getElementById("info-panel-stories");
    panel.classList.remove("feed-themed");
    panel.removeAttribute("data-feed");
    panelTitle.textContent = title;
    let headerHtml = "";
    if (opts) {
      const parts = [];
      if (opts.sourceCount > 1) parts.push(`${opts.sourceCount} sources`);
      if (opts.storyCount) parts.push(`${opts.storyCount} stories`);
      if (features.length > 0) {
        const locCounts = {};
        for (const f of features) {
          const loc = f.properties ? f.properties.location_name : null;
          if (loc) locCounts[loc] = (locCounts[loc] || 0) + 1;
        }
        const topLocs = Object.entries(locCounts).sort((a, b) => b[1] - a[1]).slice(0, 3).map((e) => e[0]);
        if (topLocs.length > 0) parts.push(topLocs.join(", "));
      }
      const mapBtn = features.length > 0 ? '<button class="info-panel-map-btn" title="Zoom to stories on map">&#127758; Map</button>' : "";
      const metaLine = parts.length || mapBtn ? `<div class="info-panel-subtitle-meta">${parts.join(" \xB7 ")}${mapBtn}</div>` : "";
      const descLine = opts.description ? `<div class="info-panel-subtitle-desc">${escapeHtml(opts.description)}</div>` : "";
      if (metaLine || descLine) headerHtml = `<div class="info-panel-subtitle">${metaLine}${descLine}</div>`;
    }
    if (loading) {
      panelStories.innerHTML = headerHtml + '<div class="loading">Loading stories...</div>';
      panel.classList.add("visible");
      if (state.map && window.innerWidth > 768) {
        state.map.easeTo({ padding: { right: 420 }, duration: 400 });
      }
      return;
    }
    const seen = /* @__PURE__ */ new Set();
    const unique = [];
    for (const f of features) {
      const sid = f.properties.story_id || f.properties.id;
      if (!seen.has(sid)) {
        seen.add(sid);
        unique.push(f);
      }
    }
    const storySortLabels = { new: "\u21C5 New", old: "\u21C5 Old", sources: "\u21C5 Sources" };
    const storySortTitles = { new: "Sort stories: Newest first", old: "Sort stories: Oldest first", sources: "Sort stories: By source" };
    const events = opts?.events || [];
    function renderWithSort() {
      const sortBtnHtml = unique.length > 1 ? `<button class="info-sort-toggle sort-toggle" title="${storySortTitles[state.storySortMode]}">${storySortLabels[state.storySortMode]}</button>` : "";
      _sortInfoStories(unique, state.storySortMode);
      _renderInfoStories(unique, sortBtnHtml + headerHtml, events);
      const sortBtn = panelStories.querySelector(".info-sort-toggle");
      if (sortBtn) {
        sortBtn.addEventListener("click", () => {
          const modes = ["new", "old", "sources"];
          const idx = modes.indexOf(state.storySortMode);
          state.storySortMode = modes[(idx + 1) % modes.length];
          renderWithSort();
        });
      }
    }
    renderWithSort();
    panel.classList.add("visible");
    if (state.map && window.innerWidth > 768) {
      state.map.easeTo({ padding: { right: 420 }, duration: 400 });
    }
  }
  function closeInfoPanel() {
    stopNetworkAnimation();
    stopSpaceAnimation();
    const panel = document.getElementById("info-panel");
    panel.classList.remove("visible");
    panel.classList.remove("feed-themed");
    panel.removeAttribute("data-feed");
    if (state.activeFeedPanel) {
      state.activeFeedPanel = null;
      document.querySelectorAll(".feed-btn").forEach((b) => b.classList.remove("active"));
    }
    if (state.map && window.innerWidth > 768) {
      state.map.easeTo({ padding: { right: 0 }, duration: 400 });
    }
    clearLocationFilter();
  }
  function setLocationFilter(filter) {
    state.activeLocationFilter = filter;
    applyLocationVisuals();
  }
  function clearLocationFilter() {
    if (!state.activeLocationFilter) return;
    state.activeLocationFilter = null;
    applyLocationVisuals();
  }
  function applyLocationVisuals() {
    if (!state.map.getLayer("cloud-points")) return;
    if (!state.activeLocationFilter) {
      state.map.setPaintProperty("cloud-points", "circle-opacity", [
        "interpolate",
        ["linear"],
        ["get", "age_hours"],
        0,
        0.95,
        6,
        0.85,
        24,
        0.6,
        72,
        0.35
      ]);
      state.map.setPaintProperty(
        "cloud-heat",
        "heatmap-opacity",
        ["interpolate", ["linear"], ["zoom"], 0, 0.9, 10, 0.7, 14, 0.4]
      );
      state.map.setPaintProperty(
        "event-labels",
        "text-opacity",
        ["interpolate", ["linear"], ["zoom"], 0, 0.55, 3, 0.85, 6, 1]
      );
      state.map.setPaintProperty("country-fill", "fill-opacity", state.lightMode ? 0.18 : 0.25);
      state.map.setPaintProperty("country-outline", "line-opacity", state.lightMode ? 0.4 : 0.5);
      return;
    }
    if (state.activeLocationFilter.type === "country") {
      const targetName = state.activeLocationFilter.name;
      state.map.setPaintProperty(
        "country-fill",
        "fill-opacity",
        ["case", ["==", ["get", "NAME"], targetName], 0.3, 0.08]
      );
      state.map.setPaintProperty(
        "country-outline",
        "line-opacity",
        ["case", ["==", ["get", "NAME"], targetName], 0.7, 0.15]
      );
      state.map.setPaintProperty(
        "cloud-points",
        "circle-opacity",
        [
          "case",
          [
            "any",
            ["==", ["get", "country_name"], targetName],
            ["==", ["get", "location_name"], targetName],
            ...Object.entries(COUNTRY_NAME_MAP).filter(([_, ne]) => ne === targetName).flatMap(([orig, _]) => [
              ["==", ["get", "country_name"], orig],
              ["==", ["get", "location_name"], orig]
            ])
          ],
          0.9,
          0.25
        ]
      );
      state.map.setPaintProperty(
        "cloud-heat",
        "heatmap-opacity",
        ["interpolate", ["linear"], ["zoom"], 0, 0.2, 10, 0.15, 14, 0.08]
      );
      state.map.setPaintProperty("event-labels", "text-opacity", 0.35);
    } else if (state.activeLocationFilter.type === "point") {
      const locName = state.activeLocationFilter.name;
      state.map.setPaintProperty(
        "cloud-points",
        "circle-opacity",
        ["case", ["==", ["get", "location_name"], locName], 0.9, 0.25]
      );
      state.map.setPaintProperty(
        "cloud-heat",
        "heatmap-opacity",
        ["interpolate", ["linear"], ["zoom"], 0, 0.2, 10, 0.15, 14, 0.08]
      );
      state.map.setPaintProperty("event-labels", "text-opacity", 0.35);
      state.map.setPaintProperty("country-fill", "fill-opacity", 0.08);
      state.map.setPaintProperty("country-outline", "line-opacity", 0.15);
    }
  }
  function applyFilters() {
    try {
      const filtered = computeFilteredState();
      state._filterState = filtered;
      if (state.map.getSource("stories-cloud")) state.map.getSource("stories-cloud").setData(filtered.clouds);
      updateCountryPolygons(filtered.clouds);
      _animateCount(document.getElementById("stat-showing"), filtered.stats.showing);
      document.getElementById("stat-sources").textContent = filtered.stats.sources;
      const searchQ = (document.getElementById("search-box").value || "").trim();
      const searchCount = document.getElementById("search-count");
      if (searchQ && searchCount) {
        searchCount.textContent = `${filtered.stats.showing} results`;
        searchCount.classList.add("visible");
      } else if (searchCount) {
        searchCount.classList.remove("visible");
      }
      updateStoryList(filtered.features);
      try {
        updateEventList(filtered.events);
      } catch (evErr) {
        console.error("Event filter error:", evErr);
        updateEventList(state.eventsData);
      }
      try {
        updateNarrativeList(filtered.narratives);
      } catch (narrErr) {
        console.error("Narrative filter error:", narrErr);
      }
      updateEventMapLabels(state.eventsData, filtered.storyIds);
      document.querySelector('.view-btn[data-view="narratives"]').textContent = `Situations${filtered.narratives.length ? ` (${filtered.narratives.length})` : ""}`;
      document.querySelector('.view-btn[data-view="events"]').textContent = `Events${filtered.events.length ? ` (${filtered.events.length})` : ""}`;
      updateFeedButtonCounts(filtered.feedCounts);
      renderConceptChips(filtered.topicCounts);
      renderSourceChips(filtered.sourceCounts);
      updatePresetOverviewFilterState(filtered.hasFilters);
      renderActiveFilterPills();
      updateFilterStatus();
      updateMobileBar();
      saveStateToURL();
    } catch (err) {
      console.error("applyFilters error:", err);
    }
  }
  function renderActiveFilterPills() {
    const container = document.getElementById("active-filters");
    if (!container) return;
    const pills = [];
    for (const c of state.activeConcepts) {
      const domain = state.conceptDomainMap[c] || "general";
      const color = DOMAIN_COLORS[domain] || "#484f58";
      pills.push(`<span class="filter-pill" style="border-color:${color}" data-type="concept" data-value="${escapeHtml(c)}">${escapeHtml(c)} <span class="filter-pill-x">&times;</span></span>`);
    }
    for (const c of state.excludedConcepts) {
      pills.push(`<span class="filter-pill excluded-pill" data-type="exclude-concept" data-value="${escapeHtml(c)}">-${escapeHtml(c)} <span class="filter-pill-x">&times;</span></span>`);
    }
    for (const s of state.activeSources) {
      pills.push(`<span class="filter-pill source-pill" data-type="source" data-value="${escapeHtml(s)}">${escapeHtml(s)} <span class="filter-pill-x">&times;</span></span>`);
    }
    for (const s of state.excludedSources) {
      pills.push(`<span class="filter-pill excluded-pill" data-type="exclude-source" data-value="${escapeHtml(s)}">-${escapeHtml(s)} <span class="filter-pill-x">&times;</span></span>`);
    }
    container.innerHTML = pills.join("");
    container.querySelectorAll(".filter-pill").forEach((pill) => {
      pill.addEventListener("click", () => {
        const type = pill.dataset.type;
        const value = pill.dataset.value;
        if (type === "concept") state.activeConcepts.delete(value);
        if (type === "exclude-concept") state.excludedConcepts.delete(value);
        if (type === "source") state.activeSources.delete(value);
        if (type === "exclude-source") state.excludedSources.delete(value);
        applyFilters();
        markPresetModified();
      });
    });
  }
  var _TIME_LABELS = { "": "", "0.0167": "1m", "1": "1h", "3": "3h", "6": "6h", "12": "12h", "24": "24h", "48": "2d", "168": "7d" };
  var _TIME_BADGE_LABELS = { "": "All Time", "0.0167": "This Minute", "1": "Last Hour", "3": "Last 3 Hours", "6": "Last 6 Hours", "12": "Last 12 Hours", "24": "Last 24 Hours", "48": "Last 2 Days", "168": "Last 7 Days" };
  var _TIME_CYCLE = ["", "0.0167", "1", "3", "6", "12", "24", "48", "168"];
  function _updateTimeBadge() {
    var labelEl = document.getElementById("time-badge-label");
    if (!labelEl) return;
    var timeVal = document.getElementById("filter-time").value;
    var label = _TIME_BADGE_LABELS[timeVal] || "All Time";
    var fs = state._filterState;
    var countStr = fs ? fs.stats.showing.toLocaleString() + " stories" : "";
    labelEl.innerHTML = '<span class="tb-time">' + escapeHtml(label) + '</span>' + (countStr ? ' <span class="tb-count">\u00B7 ' + escapeHtml(countStr) + '</span>' : '');
    /* Update active state in menu */
    var menu = document.getElementById("time-badge-menu");
    if (menu) menu.querySelectorAll(".tb-option").forEach(function(opt) {
      opt.classList.toggle("active", opt.dataset.time === timeVal);
    });
  }
  function _initTimeBadge() {
    var badge = document.getElementById("time-badge");
    var menu = document.getElementById("time-badge-menu");
    if (!badge || !menu) return;
    /* Build menu options */
    for (var i = 0; i < _TIME_CYCLE.length; i++) {
      var val = _TIME_CYCLE[i];
      var opt = document.createElement("button");
      opt.className = "tb-option" + (val === "" ? " active" : "");
      opt.dataset.time = val;
      opt.textContent = _TIME_BADGE_LABELS[val] || val;
      opt.addEventListener("click", (function(v) {
        return function(e) {
          e.stopPropagation();
          var sel = document.getElementById("filter-time");
          sel.value = v;
          sel.dispatchEvent(new Event("change"));
          menu.classList.remove("open");
        };
      })(val));
      menu.appendChild(opt);
    }
    /* Toggle menu */
    badge.addEventListener("click", function(e) {
      e.stopPropagation();
      menu.classList.toggle("open");
    });
    /* Close on outside click */
    document.addEventListener("click", function() {
      menu.classList.remove("open");
    });
  }
  function updateFilterStatus() {
    _updateTimeBadge();
    var el = document.getElementById("filter-status");
    if (!el) return;
    var parts = [];
    var timeVal = document.getElementById("filter-time").value;
    if (timeVal) parts.push(_TIME_LABELS[timeVal] || timeVal + "h");
    var nFilters = state.activeConcepts.size + state.excludedConcepts.size + state.activeSources.size + state.excludedSources.size;
    var hideOp = document.getElementById("filter-opinion")?.checked;
    if (hideOp) nFilters++;
    var searchQ = (document.getElementById("search-box").value || "").trim();
    if (searchQ) parts.push("\u201C" + (searchQ.length > 20 ? searchQ.slice(0, 20) + "\u2026" : searchQ) + "\u201D");
    if (nFilters > 0) parts.push(nFilters + " filter" + (nFilters > 1 ? "s" : ""));
    var fs = state._filterState;
    if (fs) parts.push(fs.stats.showing.toLocaleString() + " stories");
    if (parts.length === 0) { el.classList.remove("visible"); return; }
    el.innerHTML = parts.map(function(t, i) { return (i > 0 ? '<span class="fs-dot"></span>' : "") + '<span class="fs-item">' + escapeHtml(t) + "</span>"; }).join("");
    el.classList.add("visible");
  }
  async function fetchCloudData() {
    try {
      const resp = await fetch("/api/stories/clouds");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      state.cloudData = await resp.json();
      const now = Date.now();
      for (const f of state.cloudData.features || []) {
        const t = f.properties.scraped_at ? new Date(f.properties.scraped_at).getTime() : 0;
        f.properties.age_hours = t ? (now - t) / 36e5 : 999;
      }
      _blendLocationColors(state.cloudData.features || []);
      applyFilters();
    } catch (err) {
      console.error("Failed to load cloud data:", err);
    }
  }
  async function fetchStories(since, limit) {
    const params = new URLSearchParams();
    if (since) params.set("since", since);
    if (limit) params.set("limit", String(limit));
    const resp = await fetch(`/api/stories?${params.toString()}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return await resp.json();
  }
  async function loadAll(limit) {
    try {
      const data = await fetchStories(null, limit);
      state.geojsonData = data;
      state.lastFetchTime = (/* @__PURE__ */ new Date()).toISOString();
      state._lastDataUpdate = Date.now();
      if (!limit) fetchCloudData();
      updateStats();
      applyFilters();
    } catch (err) {
      console.error("Failed to load stories:", err);
    }
  }
  async function loadRemainingStories() {
    try {
      const data = await fetchStories();
      state.geojsonData = data;
      state._lastDataUpdate = Date.now();
      fetchCloudData();
      updateStats();
      applyFilters();
    } catch (err) {
      console.error("Failed to load remaining stories:", err);
    }
  }
  async function pollUpdates() {
    if (!state.lastFetchTime) return;
    try {
      const data = await fetchStories(state.lastFetchTime);
      const newFeatures = data.features || [];
      if (newFeatures.length > 0) {
        const existingUrls = new Set(state.geojsonData.features.map((f) => f.properties.url));
        const genuinelyNew = newFeatures.filter((f) => !existingUrls.has(f.properties.url));
        if (genuinelyNew.length > 0) {
          genuinelyNew.forEach((f) => state.newStoryIds.add(f.properties.id));
          state.pendingNewCount += genuinelyNew.length;
          state.geojsonData.features = genuinelyNew.concat(state.geojsonData.features);
          loadConcepts();
          const ids = genuinelyNew.map((f) => f.properties.id);
          fetchCloudData().then(() => triggerPulse(ids));
          showNewBadge(state.pendingNewCount);
          setTimeout(() => {
            ids.forEach((id) => state.newStoryIds.delete(id));
            applyFilters();
          }, 3e4);
        }
      }
      state.lastFetchTime = (/* @__PURE__ */ new Date()).toISOString();
      state._lastDataUpdate = Date.now();
      updateStats();
    } catch (err) {
      console.error("Poll failed:", err);
    }
  }
  function classifyTopic(topic) {
    const lower = topic.toLowerCase();
    for (const rule of TOPIC_DOMAIN_RULES) {
      for (const kw of rule.keywords) {
        if (lower.includes(kw)) return { domain: rule.domain, color: rule.color };
      }
    }
    return { domain: "general", color: "#484f58" };
  }
  async function loadConcepts() {
    try {
      const [topicResp, trendResp] = await Promise.all([
        fetch("/api/topics"),
        fetch("/api/trending")
      ]);
      if (!topicResp.ok) throw new Error(`HTTP ${topicResp.status}`);
      const data = await topicResp.json();
      const topics = data.topics || [];
      state._trendingConcepts = /* @__PURE__ */ new Set();
      try {
        if (trendResp.ok) {
          const tData = await trendResp.json();
          for (const t of tData.trending || []) {
            if (t.spike >= 2) state._trendingConcepts.add(t.name);
          }
        }
      } catch (_) {
      }
      state.allConceptMeta = {};
      state.conceptDomainMap = {};
      state.conceptCounts = {};
      for (const t of topics) {
        const { domain, color } = classifyTopic(t.name);
        state.conceptDomainMap[t.name] = domain;
        state.conceptCounts[t.name] = t.count;
        if (!state.allConceptMeta[domain]) {
          state.allConceptMeta[domain] = { color, concepts: [] };
        }
        state.allConceptMeta[domain].concepts.push(t);
      }
      renderConceptChips();
      if (state._pendingPresetId) {
        const pending = state.allPresets[state._pendingPresetId];
        if (pending && pending.keywords && pending.keywords.length > 0) {
          const matched = _matchingConcepts(pending.keywords);
          matched.forEach((c) => state.activeConcepts.add(c));
          applyFilters();
        }
        state._pendingPresetId = null;
      }
    } catch (err) {
      console.error("Failed to load concepts:", err);
    }
  }
  function renderConceptChips(filteredCounts) {
    const container = document.getElementById("concept-chips");
    container.innerHTML = "";
    const counts = filteredCounts || state.conceptCounts;
    const getCount = (name) => counts[name] || 0;
    const domainEntries = Object.entries(state.allConceptMeta).sort((a, b) => {
      const totalA = a[1].concepts.reduce((s, c) => s + getCount(c.name), 0);
      const totalB = b[1].concepts.reduce((s, c) => s + getCount(c.name), 0);
      return totalB - totalA;
    });
    for (const [domain, info] of domainEntries) {
      const hasStories = info.concepts.some((c) => getCount(c.name) > 0);
      if (!hasStories) continue;
      const domainDiv = document.createElement("div");
      domainDiv.className = "concept-domain";
      const label = document.createElement("span");
      label.className = "concept-domain-label";
      label.style.color = info.color;
      label.textContent = domain;
      const domainConcepts = info.concepts.filter((c) => getCount(c.name) > 0).map((c) => c.name);
      const allIncluded = domainConcepts.length > 0 && domainConcepts.every((n) => state.activeConcepts.has(n));
      const allExcluded = domainConcepts.length > 0 && domainConcepts.every((n) => state.excludedConcepts.has(n));
      if (allIncluded) {
        label.classList.add("domain-active");
        label.style.background = info.color;
        label.style.color = "#fff";
      } else if (allExcluded) label.classList.add("domain-excluded");
      label.addEventListener("click", () => toggleDomain(domain));
      label.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        excludeDomain(domain);
      });
      label.style.cursor = "pointer";
      domainDiv.appendChild(label);
      const sorted = info.concepts.filter((c) => getCount(c.name) > 0).sort((a, b) => getCount(b.name) - getCount(a.name));
      for (const concept of sorted.slice(0, 15)) {
        const count = getCount(concept.name);
        const chip = document.createElement("span");
        chip.className = "concept-chip";
        chip.dataset.concept = concept.name;
        if (state.activeConcepts.has(concept.name)) {
          chip.classList.add("active");
          chip.style.background = info.color;
        } else if (state.excludedConcepts.has(concept.name)) chip.classList.add("excluded");
        else chip.classList.add("inactive");
        const trendIcon = state._trendingConcepts.has(concept.name) ? '<span class="chip-trending" title="Trending">&#9650;</span>' : "";
        chip.innerHTML = `${concept.name}${trendIcon}<span class="chip-count">${count}</span>`;
        chip.addEventListener("click", () => toggleConcept(concept.name));
        chip.addEventListener("contextmenu", (e) => {
          e.preventDefault();
          toggleExclude(concept.name);
        });
        domainDiv.appendChild(chip);
      }
      container.appendChild(domainDiv);
    }
  }
  function toggleConcept(name) {
    state.excludedConcepts.delete(name);
    if (state.activeConcepts.has(name)) state.activeConcepts.delete(name);
    else state.activeConcepts.add(name);
    markPresetModified();
    updateFilterDrawerToggle();
    applyFilters();
  }
  function toggleExclude(name) {
    state.activeConcepts.delete(name);
    if (state.excludedConcepts.has(name)) state.excludedConcepts.delete(name);
    else state.excludedConcepts.add(name);
    markPresetModified();
    updateFilterDrawerToggle();
    applyFilters();
  }
  function clearAllFilters() {
    document.getElementById("search-box").value = "";
    document.getElementById("filter-time").value = "";
    const opinionCheckbox = document.getElementById("filter-opinion");
    if (opinionCheckbox) opinionCheckbox.checked = false;
    if (state.activeNarrativeId) {
      state.activeNarrativeId = null;
      closeInfoPanel();
      _clearHoverHighlight();
      document.title = "thisminute \u2014 global news, live";
    }
    const defaultPresetId = _resolvePresetAlias(localStorage.getItem("tm_default_world"));
    const fallback = defaultPresetId && state.allPresets[defaultPresetId] ? defaultPresetId : "all";
    switchPreset(fallback);
  }
  function toggleDomain(domain) {
    const info = state.allConceptMeta[domain];
    if (!info) return;
    const names = info.concepts.filter((c) => c.count > 0).map((c) => c.name);
    const allIncluded = names.every((n) => state.activeConcepts.has(n));
    if (allIncluded) names.forEach((n) => state.activeConcepts.delete(n));
    else names.forEach((n) => {
      state.excludedConcepts.delete(n);
      state.activeConcepts.add(n);
    });
    markPresetModified();
    updateFilterDrawerToggle();
    applyFilters();
  }
  function excludeDomain(domain) {
    const info = state.allConceptMeta[domain];
    if (!info) return;
    const names = info.concepts.filter((c) => c.count > 0).map((c) => c.name);
    const allExcluded = names.every((n) => state.excludedConcepts.has(n));
    if (allExcluded) names.forEach((n) => state.excludedConcepts.delete(n));
    else names.forEach((n) => {
      state.activeConcepts.delete(n);
      state.excludedConcepts.add(n);
    });
    markPresetModified();
    updateFilterDrawerToggle();
    applyFilters();
  }
  function toggleFilterDrawer() {
    state.filterDrawerOpen = !state.filterDrawerOpen;
    const drawer = document.getElementById("filter-drawer");
    const btn = document.getElementById("filter-drawer-toggle");
    drawer.classList.toggle("visible", state.filterDrawerOpen);
    btn.classList.toggle("open", state.filterDrawerOpen);
    updateFilterDrawerToggle();
  }
  function toggleSearch() {
    const expand = document.getElementById("search-expand");
    const btn = document.getElementById("search-toggle");
    const box = document.getElementById("search-box");
    const isActive = expand.classList.toggle("active");
    btn.classList.toggle("active", isActive);
    if (isActive) {
      box.focus();
    } else {
      box.value = "";
      applyFilters();
    }
  }
  function updateFilterDrawerToggle() {
    const btn = document.getElementById("filter-drawer-toggle");
    const originFilterCount = state.activeOrigins.size < 15 ? 1 : 0;
    const activeCount = state.activeConcepts.size + state.excludedConcepts.size + originFilterCount;
    btn.classList.toggle("has-active", activeCount > 0);
    btn.textContent = activeCount > 0 ? `Refine (${activeCount})` : "Refine";
  }
  function updateSourcesIndicator() {
    const el = document.getElementById("stat-sources");
    const hasFilter = state.activeSources.size > 0 || state.excludedSources.size > 0;
    el.classList.toggle("has-source-filter", hasFilter);
  }
  function togglePresetOverview() {
    const bar = document.getElementById("preset-overview-bar");
    bar.classList.toggle("expanded");
  }
  function updatePresetOverviewFilterState(hasFilters) {
    const bar = document.getElementById("preset-overview-bar");
    bar.classList.toggle("has-filters", !!hasFilters);
  }
  state._pendingPresetId = null;
  var _editingPresetId = null;
  function _matchingConcepts(keywords) {
    const matched = /* @__PURE__ */ new Set();
    const allConcepts = Object.keys(state.conceptCounts);
    for (const concept of allConcepts) {
      const lower = concept.toLowerCase();
      for (const kw of keywords) {
        if (lower.includes(kw)) {
          matched.add(concept);
          break;
        }
      }
    }
    return matched;
  }
  function _getRemovedPresets() {
    try {
      return JSON.parse(localStorage.getItem("tm_removed_worlds") || "[]");
    } catch (e) {
      return [];
    }
  }
  function loadPresets() {
    const removed = _getRemovedPresets();
    state.allPresets = {};
    for (const [id, preset] of Object.entries(WORLD_PRESETS)) {
      if (!removed.includes(id)) state.allPresets[id] = preset;
    }
    try {
      const saved = JSON.parse(localStorage.getItem("tm_worlds") || "{}");
      for (const [id, world] of Object.entries(saved)) {
        if (!WORLD_PRESETS[id]) {
          state.allPresets[id] = world;
        }
      }
    } catch (e) {
      console.error("Failed to load saved presets:", e);
    }
    loadPresetPrefs();
    const defaultPresetId = _resolvePresetAlias(localStorage.getItem("tm_default_world"));
    if (defaultPresetId && state.allPresets[defaultPresetId]) {
      state.activePresetId = defaultPresetId;
    }
  }
  function savePresets() {
    const custom = {};
    for (const [id, world] of Object.entries(state.allPresets)) {
      if (!world.builtIn) custom[id] = world;
    }
    try {
      localStorage.setItem("tm_worlds", JSON.stringify(custom));
    } catch (e) {
      console.error("Failed to save presets:", e);
    }
  }
  function loadPresetPrefs() {
    try {
      state.presetPrefs = JSON.parse(localStorage.getItem("tm_world_prefs") || "{}");
    } catch (e) {
      state.presetPrefs = {};
    }
    let order = 0;
    for (const id of Object.keys(state.allPresets)) {
      if (!state.presetPrefs[id]) {
        state.presetPrefs[id] = { visible: true, order };
      }
      if (state.presetPrefs[id].order == null) state.presetPrefs[id].order = order;
      order++;
    }
    for (const id of Object.keys(state.presetPrefs)) {
      if (!state.allPresets[id]) delete state.presetPrefs[id];
    }
    // Apply tm_visible_worlds to presetPrefs visibility
    var visiblePresets = _loadVisiblePresets();
    if (visiblePresets) {
      for (var vid in state.presetPrefs) {
        if (WORLD_PRESETS[vid]) {
          state.presetPrefs[vid].visible = visiblePresets.indexOf(vid) !== -1;
        }
      }
    }
    savePresetPrefs();
  }
  function savePresetPrefs() {
    try {
      localStorage.setItem("tm_world_prefs", JSON.stringify(state.presetPrefs));
    } catch (e) {
      console.error("Failed to save preset prefs:", e);
    }
  }
  function _getVisiblePresetEntries() {
    return Object.entries(state.allPresets).filter(([id]) => state.presetPrefs[id]?.visible !== false).sort((a, b) => (state.presetPrefs[a[0]]?.order ?? 99) - (state.presetPrefs[b[0]]?.order ?? 99));
  }
  function _autoDetectIcon(name, world) {
    for (const [re, emoji] of NAME_EMOJI_MAP) {
      if (re.test(name)) return emoji;
    }
    if (world?.config?.brightSideMode) return "\u{1F31F}";
    if (world?.feedTags?.some((t) => t === "sports")) return "\u{1F3C6}";
    return null;
  }
  function _getAbbreviation(label) {
    const words = label.trim().split(/\s+/);
    if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase();
    return label.substring(0, 2).toUpperCase();
  }
  function _autoPickColor(id) {
    let hash = 0;
    for (let i = 0; i < id.length; i++) hash = (hash << 5) - hash + id.charCodeAt(i) | 0;
    return CUSTOM_COLOR_PALETTE[Math.abs(hash) % CUSTOM_COLOR_PALETTE.length];
  }
  function _describeConfig(config, feedTags) {
    const parts = [];
    if (feedTags?.length) parts.push(feedTags.join(", ") + " feeds");
    if (config?.brightSideMode) parts.push("bright side");
    if (config?.curiousMode) parts.push("curious");
    if (config?.activeSources?.length) parts.push(config.activeSources.length + " sources");
    if (config?.excludedSources?.length) parts.push(config.excludedSources.length + " excluded");
    if (config?.activeConcepts?.length) parts.push(config.activeConcepts.length + " topics");
    if (config?.searchText) parts.push(`"${config.searchText}"`);
    if (config?.timeHours) parts.push(config.timeHours + "h");
    if (config?.hideOpinion) parts.push("no opinion");
    return parts.length ? parts.join(" \xB7 ") : "all stories";
  }
  function captureCurrentConfig() {
    return {
      activeConcepts: [...state.activeConcepts],
      excludedConcepts: [...state.excludedConcepts],
      activeSources: [...state.activeSources],
      excludedSources: [...state.excludedSources],
      activeOrigins: [...state.activeOrigins],
      brightSideMode: state.brightSideMode,
      curiousMode: state.curiousMode,
      searchText: document.getElementById("search-box").value.trim(),
      timeHours: document.getElementById("filter-time").value,
      hideOpinion: document.getElementById("filter-opinion")?.checked || false
    };
  }
  function applyPresetConfig(config, keywords, feedTags) {
    state.activeConcepts.clear();
    state.excludedConcepts.clear();
    state.activeSources.clear();
    state.excludedSources.clear();
    state.brightSideMode = false;
    state.curiousMode = false;
    state.activeNarrativeId = null;
    if (keywords && keywords.length > 0) {
      const matched = _matchingConcepts(keywords);
      matched.forEach((c) => state.activeConcepts.add(c));
    } else {
      (config.activeConcepts || []).forEach((c) => state.activeConcepts.add(c));
    }
    (config.excludedConcepts || []).forEach((c) => state.excludedConcepts.add(c));
    if (feedTags && feedTags.length > 0) {
      sourcesForTags(feedTags).forEach((s) => state.activeSources.add(s));
    }
    (config.activeSources || []).forEach((s) => state.activeSources.add(s));
    (config.excludedSources || []).forEach((s) => state.excludedSources.add(s));
    state.activeOrigins = new Set(config.activeOrigins || ["rss", "gdelt", "usgs", "noaa", "eonet", "gdacs", "reliefweb", "who", "launches", "openaq", "travel", "firms", "meteoalarm", "acled", "jma"]);
    state.brightSideMode = !!config.brightSideMode;
    state.curiousMode = !!config.curiousMode;
    document.querySelectorAll(".origin-btn").forEach((btn) => {
      btn.classList.toggle("active", state.activeOrigins.has(btn.dataset.origin));
    });
    updateFilterDrawerToggle();
    updateSourcesIndicator();
  }
  async function switchPreset(presetId) {
    const world = state.allPresets[presetId];
    if (!world) return;
    if (state.activePresetId === presetId && !state.presetModified) return;
    if (world.feedTags && world.feedTags.length > 0 && state._feedTagsReady) {
      await state._feedTagsReady;
    }
    if (state.activeNarrativeId) {
      const newDomain = PRESET_DOMAIN_MAP[presetId];
      const activeNarr = state.narrativesData.find((n) => n.id === state.activeNarrativeId);
      if (activeNarr && newDomain && (activeNarr.domain || "news") !== newDomain) {
        state.activeNarrativeId = null;
        closeInfoPanel();
        _clearHoverHighlight();
        document.title = "thisminute \u2014 global news, live";
      }
    }
    if (world.permanent) {
      document.getElementById("search-box").value = "";
      document.getElementById("filter-time").value = "";
      const opinionCheckbox = document.getElementById("filter-opinion");
      if (opinionCheckbox) opinionCheckbox.checked = false;
      if (state.activeNarrativeId) {
        state.activeNarrativeId = null;
        closeInfoPanel();
        _clearHoverHighlight();
        document.title = "thisminute \u2014 global news, live";
      }
      state.activeLocationFilter = null;
    }
    const effectiveConfig = world.builtIn && state.presetPrefs[presetId]?.configOverride || world.config;
    applyPresetConfig(effectiveConfig, world.keywords, world.feedTags);
    state.activePresetId = presetId;
    state.presetModified = false;
    _blendLocationColors(state.cloudData.features || []);
    _updateLegendColors();
    updatePresetsBar();
    renderPresetOverview();
    applyFilters();
  }
  function markPresetModified() {
    if (!state.activePresetId) return;
    state.presetModified = true;
    updatePresetsBar();
  }
  function updatePresetConfig(presetId) {
    const world = state.allPresets[presetId];
    if (!world) return;
    const config = captureCurrentConfig();
    if (world.builtIn) {
      if (!state.presetPrefs[presetId]) state.presetPrefs[presetId] = { visible: true, order: 0 };
      state.presetPrefs[presetId].configOverride = config;
      savePresetPrefs();
    } else {
      world.config = config;
      savePresets();
    }
    state.presetModified = false;
    updatePresetsBar();
  }
  function resetPresetConfig(presetId) {
    const pref = state.presetPrefs[presetId];
    if (pref?.configOverride) {
      delete pref.configOverride;
      savePresetPrefs();
      switchPreset(presetId);
    }
  }
  function generatePresetURL(presetId) {
    const world = state.allPresets[presetId];
    if (!world) return window.location.href;
    const base = window.location.origin + window.location.pathname;
    if (world.builtIn) {
      const pref = state.presetPrefs[presetId];
      if (pref?.configOverride) {
        return base + "#" + _configToParams(pref.configOverride).toString();
      }
      return base + "#world=" + presetId;
    }
    const effectiveConfig = world.config;
    return base + "#" + _configToParams(effectiveConfig).toString();
  }
  function _configToParams(config) {
    const params = new URLSearchParams();
    if (config.activeConcepts?.length) params.set("in", config.activeConcepts.join(","));
    if (config.excludedConcepts?.length) params.set("ex", config.excludedConcepts.join(","));
    if (config.activeSources?.length) params.set("src", config.activeSources.join(","));
    if (config.excludedSources?.length) params.set("xsrc", config.excludedSources.join(","));
    if (config.activeOrigins?.length && (config.activeOrigins.length < 15 || !config.activeOrigins.includes("rss") || !config.activeOrigins.includes("gdelt") || !config.activeOrigins.includes("usgs") || !config.activeOrigins.includes("noaa") || !config.activeOrigins.includes("eonet") || !config.activeOrigins.includes("gdacs") || !config.activeOrigins.includes("reliefweb") || !config.activeOrigins.includes("who") || !config.activeOrigins.includes("launches") || !config.activeOrigins.includes("openaq") || !config.activeOrigins.includes("travel") || !config.activeOrigins.includes("firms") || !config.activeOrigins.includes("meteoalarm") || !config.activeOrigins.includes("acled") || !config.activeOrigins.includes("jma"))) {
      params.set("origin", config.activeOrigins.join(","));
    }
    if (config.brightSideMode) params.set("bs", "1");
    if (config.curiousMode) params.set("cur", "1");
    if (config.searchText) params.set("q", config.searchText);
    if (config.timeHours) params.set("t", config.timeHours);
    if (config.hideOpinion) params.set("op", "0");
    return params;
  }
  function updatePresetsBarOverflow() {
    const wrapper = document.querySelector(".presets-bar-wrapper");
    const bar = document.getElementById("presets-bar");
    if (!wrapper || !bar) return;
    const sl = bar.scrollLeft;
    const sw = bar.scrollWidth;
    const cw = bar.clientWidth;
    wrapper.classList.toggle("scroll-left", sl > 4);
    wrapper.classList.toggle("scroll-right", sl + cw < sw - 4);
  }
  function updatePresetsBar() {
    const domainCounts = {};
    for (const n of state.narrativesData || []) {
      const d = n.domain || "news";
      domainCounts[d] = (domainCounts[d] || 0) + 1;
    }
    document.querySelectorAll(".preset-btn").forEach((btn) => {
      const presetId = btn.dataset.world;
      const world = state.allPresets[presetId];
      const isActive = presetId === state.activePresetId;
      btn.classList.toggle("active", isActive);
      btn.classList.toggle("modified", isActive && state.presetModified);
      if (isActive && world && !world.builtIn) {
        btn.style.setProperty("--custom-preset-color", world.color);
        btn.classList.add("custom-color");
      } else {
        btn.style.removeProperty("--custom-preset-color");
        btn.classList.remove("custom-color");
      }
      const domain = PRESET_DOMAIN_MAP[presetId];
      const count = domain ? domainCounts[domain] || 0 : 0;
      const label = world?.label || presetId;
      const shortLabel = PRESET_SHORT_LABELS[presetId] || label;
      const icon = PRESET_ICONS[presetId] || state.presetPrefs[presetId]?.icon;
      let html = "";
      if (icon) {
        html = `<span class="preset-btn-icon">${icon}</span><span class="preset-btn-label">${escapeHtml(shortLabel)}</span>`;
      } else {
        html = `<span class="preset-btn-label">${escapeHtml(shortLabel)}</span>`;
      }
      if (count > 0) {
        html += ` <span class="preset-btn-count">${count}</span>`;
      }
      btn.innerHTML = html;
      btn.title = label;
    });
  }
  function saveCurrentAsPreset(name) {
    const id = "custom_" + Date.now();
    const config = captureCurrentConfig();
    const world = {
      label: name,
      color: _autoPickColor(id),
      builtIn: false,
      config
    };
    state.allPresets[id] = world;
    const maxOrder = Math.max(0, ...Object.values(state.presetPrefs).map((p) => p.order ?? 0));
    state.presetPrefs[id] = {
      visible: true,
      order: maxOrder + 1,
      icon: _autoDetectIcon(name, world)
    };
    savePresets();
    savePresetPrefs();
    state.activePresetId = id;
    state.presetModified = false;
    renderPresetsBar();
    saveStateToURL();
  }
  function deletePreset(presetId) {
    const world = state.allPresets[presetId];
    if (!world || world.permanent) return;
    if (world.builtIn) {
      const removed = _getRemovedPresets();
      if (!removed.includes(presetId)) removed.push(presetId);
      localStorage.setItem("tm_removed_worlds", JSON.stringify(removed));
    }
    delete state.allPresets[presetId];
    delete state.presetPrefs[presetId];
    savePresets();
    savePresetPrefs();
    if (localStorage.getItem("tm_default_world") === presetId) {
      localStorage.removeItem("tm_default_world");
    }
    renderPresetsBar();
    if (state.activePresetId === presetId) {
      switchPreset("all");
    }
  }
  var PRESET_SHORT_LABELS = { entertainment: "Ent." };
  function renderPresetsBar() {
    const bar = document.getElementById("presets-bar");
    const shareBtn = document.getElementById("preset-share-btn");
    bar.querySelectorAll(".preset-btn").forEach((b) => b.remove());
    const visibleEntries = _getVisiblePresetEntries();
    for (const [id, world] of visibleEntries) {
      const btn = document.createElement("button");
      btn.className = "preset-btn";
      btn.dataset.world = id;
      btn.dataset.color = world.color;
      const icon = PRESET_ICONS[id] || state.presetPrefs[id]?.icon;
      const shortLabel = PRESET_SHORT_LABELS[id] || world.label;
      if (icon) {
        btn.innerHTML = `<span class="preset-btn-icon">${icon}</span><span class="preset-btn-label">${escapeHtml(shortLabel)}</span>`;
      } else {
        btn.innerHTML = `<span class="preset-btn-label">${escapeHtml(shortLabel)}</span>`;
      }
      btn.title = world.label;
      btn.addEventListener("click", () => {
        stopPresetTour();
        switchPreset(id);
      });
      bar.insertBefore(btn, shareBtn);
    }
    updatePresetsBar();
    updatePresetsBarOverflow();
  }
  // === Preset Tour: Auto-cycling presets for first-time visitors ===
  var PRESET_TOUR_SEQUENCE = ["bright_side", "sports", "curious", "entertainment", "conflict", "travel"];
  var PRESET_TOUR_INTERVAL = 5000;
  var _presetTourTimer = null;
  var _presetTourIdx = 0;
  var _presetTourActive = false;
  var _isFirstVisitForTour = false;
  function captureFirstVisitFlag() {
    _isFirstVisitForTour = !localStorage.getItem("tm_world_tour_seen") && !localStorage.getItem("tm_last_visit") && !localStorage.getItem("tm_default_world") && !window.location.hash;
  }
  function replayPresetTour() {
    if (_presetTourActive) stopPresetTour();
    if (_presetTourTimer) { clearInterval(_presetTourTimer); _presetTourTimer = null; }
    _isFirstVisitForTour = true;
    _presetTourActive = false;
    startPresetTour();
  }
  function startPresetTour() {
    if (_presetTourTimer) { clearInterval(_presetTourTimer); _presetTourTimer = null; }
    if (!_isFirstVisitForTour) return;
    _presetTourActive = true;
    _presetTourIdx = 0;
    _showTourPreset(_presetTourIdx);
    _presetTourTimer = setInterval(() => {
      _presetTourIdx++;
      if (_presetTourIdx >= PRESET_TOUR_SEQUENCE.length) {
        _presetTourIdx = 0;
      }
      _transitionTourPreset(_presetTourIdx);
    }, PRESET_TOUR_INTERVAL);
    var stopEvents = ["click", "scroll", "keydown", "touchstart", "wheel"];
    function onInteraction() {
      stopPresetTour();
      for (var ev of stopEvents) {
        document.removeEventListener(ev, onInteraction, true);
      }
    }
    for (var ev of stopEvents) {
      document.addEventListener(ev, onInteraction, true);
    }
  }
  function stopPresetTour() {
    if (!_presetTourActive) return;
    _presetTourActive = false;
    if (_presetTourTimer) {
      clearInterval(_presetTourTimer);
      _presetTourTimer = null;
    }
    localStorage.setItem("tm_world_tour_seen", "1");
    var overlay = document.getElementById("preset-tour-overlay");
    if (overlay) {
      overlay.classList.remove("visible");
      overlay.classList.add("fading");
    }
    // Show welcome questionnaire for first-time visitors after tour ends
    if (_shouldShowPresetPicker()) {
      setTimeout(() => _showWelcomeDialog(), 600);
    } else {
      // Fire deferred onboarding after tour ends
      showOnboardingHint();
      if (_isMobile() && !localStorage.getItem("thisminute-onboarded")) {
        setTimeout(() => {
          setSheetState("half");
          setTimeout(() => setSheetState("closed"), 1500);
        }, 2e3);
      }
    }
  }
  function _showTourPreset(idx) {
    var presetId = PRESET_TOUR_SEQUENCE[idx];
    var world = state.allPresets[presetId];
    if (!world) return;
    var icon = PRESET_ICONS[presetId] || "";
    var overlay = document.getElementById("preset-tour-overlay");
    if (!overlay) return;
    var tourIcon = overlay.querySelector(".tour-icon");
    var tourName = overlay.querySelector(".tour-name");
    if (tourIcon) tourIcon.textContent = icon;
    if (tourName) tourName.textContent = world.label;
    overlay.classList.add("visible");
    overlay.classList.remove("fading");
    switchPreset(presetId);
  }
  function _transitionTourPreset(idx) {
    var overlay = document.getElementById("preset-tour-overlay");
    if (!overlay) return;
    overlay.classList.add("fading");
    overlay.classList.remove("visible");
    setTimeout(() => {
      if (!_presetTourActive) return;
      _showTourPreset(idx);
    }, 400);
  }

  // === Preset Picker: First-visit preset selector ===
  var PRESET_PICKER_DESCRIPTIONS = {
    bright_side: "Uplifting and feel-good stories",
    sports: "Live scores, transfers, tournaments",
    entertainment: "Film, music, celebrity, awards",
    curious: "Quirky and human-interest stories",
    science: "Research, discoveries, space",
    tech: "AI, cyber, software, startups",
    planet: "Earthquakes, storms, climate, wildfires",
    conflict: "Wars, attacks, protests, crises",
    travel: "Advisories, tourism, destinations",
    power: "Elections, diplomacy, legislation",
    markets: "Stocks, finance, economy",
    health: "Disease, outbreaks, medical research",
    all: "Everything, unfiltered"
  };
  var _presetPickerSelection = null;
  var _pickerOverlayClickRef = null;
  function showPresetPicker() {
    var dialog = document.getElementById("preset-picker-dialog");
    var grid = document.getElementById("preset-picker-grid");
    if (!dialog || !grid) return;
    grid.innerHTML = "";
    // Start with current visible presets or all built-in presets
    var savedVisible = _loadVisiblePresets();
    var builtInIds = Object.keys(WORLD_PRESETS);
    _presetPickerSelection = {};
    for (var i = 0; i < builtInIds.length; i++) {
      var id = builtInIds[i];
      _presetPickerSelection[id] = savedVisible ? savedVisible.indexOf(id) !== -1 : true;
    }
    for (var j = 0; j < builtInIds.length; j++) {
      var wid = builtInIds[j];
      var world = WORLD_PRESETS[wid];
      if (!world) continue;
      var icon = PRESET_ICONS[wid] || "";
      var desc = PRESET_PICKER_DESCRIPTIONS[wid] || "";
      var card = document.createElement("div");
      card.className = "preset-picker-card" + (_presetPickerSelection[wid] ? " selected" : " deselected");
      card.dataset.world = wid;
      card.style.setProperty("--preset-picker-color", world.color);
      card.innerHTML = '<span class="preset-picker-card-icon">' + icon + "</span>" + '<div class="preset-picker-card-info">' + '<span class="preset-picker-card-name">' + escapeHtml(world.label) + "</span>" + '<span class="preset-picker-card-desc">' + escapeHtml(desc) + "</span>" + "</div>" + '<span class="preset-picker-check">\u2713</span>';
      card.addEventListener("click", _presetPickerToggle);
      grid.appendChild(card);
    }
    dialog.classList.add("visible");
    // Click outside the panel to confirm
    // Remove any stale listener before adding a new one
    if (_pickerOverlayClickRef) {
      dialog.removeEventListener("click", _pickerOverlayClickRef);
    }
    _pickerOverlayClickRef = function(e) {
      if (e.target === dialog) {
        confirmPresetPicker();
      }
    };
    dialog.addEventListener("click", _pickerOverlayClickRef);
  }
  function _presetPickerToggle(e) {
    var card = e.currentTarget;
    var wid = card.dataset.world;
    _presetPickerSelection[wid] = !_presetPickerSelection[wid];
    if (_presetPickerSelection[wid]) {
      card.classList.add("selected");
      card.classList.remove("deselected");
    } else {
      card.classList.remove("selected");
      card.classList.add("deselected");
    }
  }
  function closePresetPicker() {
    var dialog = document.getElementById("preset-picker-dialog");
    if (dialog) {
      dialog.classList.remove("visible");
      // Remove overlay click listener to prevent leak (Fix #2)
      if (_pickerOverlayClickRef) {
        dialog.removeEventListener("click", _pickerOverlayClickRef);
        _pickerOverlayClickRef = null;
      }
    }
  }
  function confirmPresetPicker() {
    if (!_presetPickerSelection) { closePresetPicker(); return; }
    var selected = [];
    var builtInIds = Object.keys(WORLD_PRESETS);
    var allSelected = true;
    for (var i = 0; i < builtInIds.length; i++) {
      var id = builtInIds[i];
      if (_presetPickerSelection[id]) {
        selected.push(id);
      } else {
        allSelected = false;
      }
    }
    // If none selected, treat as all selected (prevent empty bar)
    if (selected.length === 0) {
      selected = builtInIds.slice();
      allSelected = true;
    }
    if (allSelected) {
      // Remove the key entirely -- backwards compatible default
      localStorage.removeItem("tm_visible_worlds");
    } else {
      localStorage.setItem("tm_visible_worlds", JSON.stringify(selected));
    }
    // Apply visibility to presetPrefs
    _applyVisiblePresetsToPrefs();
    renderPresetsBar();
    // If current preset was hidden, switch to first visible or news
    if (state.activePresetId !== "all" && selected.indexOf(state.activePresetId) === -1) {
      switchPreset(selected[0] || "all");
    }
    closePresetPicker();
    _presetPickerSelection = null;
    // Deferred onboarding: show hint + mobile sheet peek on first visit (Fix #1)
    // This fires regardless of how the picker was dismissed (Done, Escape, or click-outside)
    if (_isFirstVisitForTour) {
      showOnboardingHint();
      if (_isMobile() && !localStorage.getItem("thisminute-onboarded")) {
        setTimeout(() => {
          setSheetState("half");
          setTimeout(() => setSheetState("closed"), 1500);
        }, 2e3);
      }
    }
  }
  function _loadVisiblePresets() {
    try {
      var raw = localStorage.getItem("tm_visible_worlds");
      if (!raw) return null;
      var arr = JSON.parse(raw);
      if (Array.isArray(arr) && arr.length > 0) return arr;
    } catch (e) {}
    return null;
  }
  function _applyVisiblePresetsToPrefs() {
    var visible = _loadVisiblePresets();
    for (var id in state.presetPrefs) {
      if (WORLD_PRESETS[id]) {
        state.presetPrefs[id].visible = visible ? visible.indexOf(id) !== -1 : true;
      }
    }
    savePresetPrefs();
  }
  function _syncVisiblePresetsFromPrefs() {
    // Sync presetPrefs visibility back to tm_visible_worlds
    var visible = [];
    var allVisible = true;
    var builtInIds = Object.keys(WORLD_PRESETS);
    for (var i = 0; i < builtInIds.length; i++) {
      var id = builtInIds[i];
      if (state.presetPrefs[id]?.visible !== false) {
        visible.push(id);
      } else {
        allVisible = false;
      }
    }
    if (allVisible) {
      localStorage.removeItem("tm_visible_worlds");
    } else {
      localStorage.setItem("tm_visible_worlds", JSON.stringify(visible));
    }
  }
  function _shouldShowPresetPicker() {
    // Show if first visit (tour just finished) AND no saved visible presets preference
    return _isFirstVisitForTour && !localStorage.getItem("tm_visible_worlds");
  }

  var _welcomeDialogInit = false;
  function _showWelcomeDialog() {
    var dialog = document.getElementById("welcome-dialog");
    if (!dialog) return;
    dialog.classList.add("visible");
    if (_welcomeDialogInit) return;
    _welcomeDialogInit = true;
    dialog.querySelectorAll(".welcome-card").forEach(function(card) {
      card.addEventListener("click", function() {
        var presetId = card.dataset.world;
        dialog.classList.remove("visible");
        if (presetId && state.allPresets[presetId]) {
          switchPreset(presetId);
          localStorage.setItem("tm_default_world", presetId);
        }
        showOnboardingHint();
        if (_isMobile() && !localStorage.getItem("thisminute-onboarded")) {
          setTimeout(function() {
            setSheetState("half");
            setTimeout(function() { setSheetState("closed"); }, 1500);
          }, 2e3);
        }
      });
    });
    dialog.addEventListener("click", function(e) {
      if (e.target === dialog) {
        dialog.classList.remove("visible");
        showOnboardingHint();
      }
    });
  }

  function togglePresetsPanel() {
    const panel = document.getElementById("presets-panel");
    panel.classList.toggle("visible");
    if (panel.classList.contains("visible")) {
      renderPresetsPanelContents();
    }
  }
  function closePresetsPanel() {
    document.getElementById("presets-panel").classList.remove("visible");
  }
  function renderPresetsPanelContents() {
    const listContainer = document.getElementById("presets-panel-list");
    listContainer.innerHTML = "";
    const sorted = Object.entries(state.allPresets).sort((a, b) => (state.presetPrefs[a[0]]?.order ?? 99) - (state.presetPrefs[b[0]]?.order ?? 99));
    let lastBuiltIn = -1;
    sorted.forEach(([_, w], i) => {
      if (w.builtIn) lastBuiltIn = i;
    });
    const defaultPresetId = _resolvePresetAlias(localStorage.getItem("tm_default_world"));
    sorted.forEach(([id, world], idx) => {
      const pref = state.presetPrefs[id] || {};
      const isVisible = pref.visible !== false;
      const isActive = id === state.activePresetId;
      const isDefault = id === defaultPresetId;
      const hasOverride = world.builtIn && !!pref.configOverride;
      const item = document.createElement("div");
      item.className = "preset-panel-item" + (isActive ? " active-preset" : "") + (!isVisible ? " hidden-preset" : "");
      const eye = document.createElement("button");
      eye.className = "preset-panel-eye";
      eye.innerHTML = isVisible ? "&#x1F441;" : "&#x1F441;&#x200D;&#x1F5E8;";
      eye.title = isVisible ? "Hide from bar" : "Show in bar";
      eye.style.opacity = isVisible ? "0.7" : "0.3";
      eye.addEventListener("click", (e) => {
        e.stopPropagation();
        if (!state.presetPrefs[id]) state.presetPrefs[id] = { visible: true, order: idx };
        state.presetPrefs[id].visible = !isVisible;
        savePresetPrefs();
        _syncVisiblePresetsFromPrefs();
        renderPresetsBar();
        renderPresetsPanelContents();
      });
      item.appendChild(eye);
      const dot = document.createElement("span");
      dot.className = "preset-panel-color";
      dot.style.background = world.color;
      item.appendChild(dot);
      const icon = PRESET_ICONS[id] || pref.icon;
      const info = document.createElement("div");
      info.className = "preset-panel-info";
      const labelEl = document.createElement("span");
      labelEl.className = "preset-panel-label";
      labelEl.textContent = (icon ? icon + " " : "") + world.label;
      info.appendChild(labelEl);
      const desc = document.createElement("span");
      desc.className = "preset-panel-desc";
      const effectiveConfig = world.builtIn && pref.configOverride || world.config;
      desc.textContent = _describeConfig(effectiveConfig, world.feedTags);
      info.appendChild(desc);
      if (isActive && state.presetModified) {
        const updateBtn = document.createElement("button");
        updateBtn.className = "preset-panel-update";
        updateBtn.textContent = "Update";
        updateBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          updatePresetConfig(id);
          renderPresetsPanelContents();
        });
        info.appendChild(updateBtn);
      }
      if (hasOverride) {
        const resetBtn = document.createElement("button");
        resetBtn.className = "preset-panel-reset";
        resetBtn.textContent = "Reset";
        resetBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          resetPresetConfig(id);
          renderPresetsPanelContents();
        });
        info.appendChild(resetBtn);
      }
      item.appendChild(info);
      const star = document.createElement("button");
      star.className = "preset-panel-star" + (isDefault ? " active" : "");
      star.innerHTML = isDefault ? "&#x2605;" : "&#x2606;";
      star.title = isDefault ? "Remove as default" : "Set as default";
      star.addEventListener("click", (e) => {
        e.stopPropagation();
        if (isDefault) {
          localStorage.removeItem("tm_default_world");
        } else {
          localStorage.setItem("tm_default_world", id);
        }
        renderPresetsPanelContents();
      });
      item.appendChild(star);
      const share = document.createElement("button");
      share.className = "preset-panel-share";
      share.innerHTML = "&#x1F517;";
      share.title = "Copy link";
      share.addEventListener("click", (e) => {
        e.stopPropagation();
        _copyToClipboard(share, generatePresetURL(id), "&#x1F517;");
      });
      item.appendChild(share);
      const arrows = document.createElement("span");
      arrows.className = "preset-panel-arrows";
      const upBtn = document.createElement("button");
      upBtn.innerHTML = "&#x25B2;";
      upBtn.title = "Move up";
      upBtn.disabled = idx === 0;
      upBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        if (idx === 0) return;
        const prevId = sorted[idx - 1][0];
        const tmp = state.presetPrefs[id].order;
        state.presetPrefs[id].order = state.presetPrefs[prevId].order;
        state.presetPrefs[prevId].order = tmp;
        savePresetPrefs();
        renderPresetsBar();
        renderPresetsPanelContents();
      });
      const downBtn = document.createElement("button");
      downBtn.innerHTML = "&#x25BC;";
      downBtn.title = "Move down";
      downBtn.disabled = idx === sorted.length - 1;
      downBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        if (idx === sorted.length - 1) return;
        const nextId = sorted[idx + 1][0];
        const tmp = state.presetPrefs[id].order;
        state.presetPrefs[id].order = state.presetPrefs[nextId].order;
        state.presetPrefs[nextId].order = tmp;
        savePresetPrefs();
        renderPresetsBar();
        renderPresetsPanelContents();
      });
      arrows.appendChild(upBtn);
      arrows.appendChild(downBtn);
      item.appendChild(arrows);
      if (!world.builtIn) {
        const edit = document.createElement("button");
        edit.className = "preset-panel-edit";
        edit.innerHTML = "&#x270E;";
        edit.title = "Rename";
        edit.addEventListener("click", (e) => {
          e.stopPropagation();
          showSavePresetDialog(id);
        });
        item.appendChild(edit);
      }
      if (!world.permanent) {
        const del = document.createElement("button");
        del.className = "preset-panel-delete";
        del.innerHTML = "&times;";
        del.addEventListener("click", (e) => {
          e.stopPropagation();
          deletePreset(id);
          renderPresetsPanelContents();
        });
        item.appendChild(del);
      }
      item.addEventListener("click", () => {
        switchPreset(id);
        closePresetsPanel();
      });
      listContainer.appendChild(item);
      if (idx === lastBuiltIn && lastBuiltIn < sorted.length - 1) {
        const sep = document.createElement("div");
        sep.className = "preset-panel-separator";
        listContainer.appendChild(sep);
      }
    });
    const removed = _getRemovedPresets();
    if (removed.length > 0) {
      const restore = document.createElement("button");
      restore.className = "preset-panel-restore";
      restore.textContent = "Restore default presets";
      restore.addEventListener("click", (e) => {
        e.stopPropagation();
        localStorage.removeItem("tm_removed_worlds");
        loadPresets();
        renderPresetsBar();
        renderPresetsPanelContents();
      });
      listContainer.appendChild(restore);
    }
  }
  function showSavePresetDialog(editId) {
    closePresetsPanel();
    _editingPresetId = editId || null;
    const dialog = document.getElementById("preset-save-dialog");
    const input = document.getElementById("preset-save-name");
    const heading = dialog.querySelector("h3");
    const confirmBtn = document.getElementById("preset-save-confirm");
    if (_editingPresetId && state.allPresets[_editingPresetId]) {
      heading.textContent = "Rename Preset";
      input.value = state.allPresets[_editingPresetId].label;
      confirmBtn.textContent = "Rename";
    } else {
      heading.textContent = "Save Preset";
      input.value = "";
      confirmBtn.textContent = "Save";
    }
    dialog.classList.add("visible");
    input.focus();
    input.select();
  }
  function closeSavePresetDialog() {
    _editingPresetId = null;
    document.getElementById("preset-save-dialog").classList.remove("visible");
  }
  function confirmSavePreset() {
    const input = document.getElementById("preset-save-name");
    const name = input.value.trim();
    if (!name) return;
    const nameLower = name.toLowerCase();
    const isDuplicate = Object.entries(state.allPresets).some(
      ([wid, w]) => w.label.toLowerCase() === nameLower && wid !== _editingPresetId
    );
    if (isDuplicate) {
      input.classList.add("input-error");
      input.setAttribute("placeholder", "Name already exists");
      setTimeout(() => {
        input.classList.remove("input-error");
        input.setAttribute("placeholder", "My Preset");
      }, 2e3);
      return;
    }
    if (_editingPresetId && state.allPresets[_editingPresetId]) {
      const world = state.allPresets[_editingPresetId];
      world.label = name;
      if (state.presetPrefs[_editingPresetId]) {
        state.presetPrefs[_editingPresetId].icon = _autoDetectIcon(name, world);
      }
      savePresets();
      savePresetPrefs();
      renderPresetsBar();
    } else {
      saveCurrentAsPreset(name);
    }
    closeSavePresetDialog();
  }
  state.sourceCounts = [];
  async function loadSources() {
    try {
      const resp = await fetch("/api/sources");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      if (data.counts) state.sourceCounts = data.counts;
    } catch (err) {
      console.error("Failed to load sources:", err);
    }
  }
  function loadFeedTags() {
    state._feedTagsReady = (async () => {
      try {
        const resp = await fetch("/api/feed-tags");
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        state.feedTagData = await resp.json();
      } catch (err) {
        console.error("Failed to load feed tags:", err);
      }
    })();
    return state._feedTagsReady;
  }
  function sourcesForTags(tags) {
    const sources = /* @__PURE__ */ new Set();
    for (const tag of tags) {
      for (const src of state.feedTagData.tag_sources[tag] || []) {
        sources.add(src);
      }
    }
    return [...sources];
  }
  function renderSourceChips(filteredCounts) {
    const container = document.getElementById("source-chips");
    if (!container) return;
    const chips = filteredCounts || state.sourceCounts;
    if (!chips.length) {
      container.innerHTML = "";
      return;
    }
    container.innerHTML = chips.map((s) => {
      const isActive = state.activeSources.has(s.source);
      const isExcluded = state.excludedSources.has(s.source);
      const cls = isActive ? "active" : isExcluded ? "excluded" : "";
      return `<span class="source-chip ${cls}" data-source="${escapeHtml(s.source)}">${escapeHtml(s.source)}<span class="chip-count">${s.count}</span></span>`;
    }).join("");
    container.querySelectorAll(".source-chip").forEach((chip) => {
      chip.addEventListener("click", () => toggleSource(chip.dataset.source));
      chip.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        toggleExcludeSource(chip.dataset.source);
      });
    });
    const toggle = document.getElementById("source-chips-toggle");
    if (toggle) {
      requestAnimationFrame(() => {
        const overflows = container.scrollHeight > container.clientHeight + 4;
        toggle.classList.toggle("visible", overflows && !container.classList.contains("expanded"));
      });
    }
  }
  function toggleSource(name) {
    state.excludedSources.delete(name);
    if (state.activeSources.has(name)) state.activeSources.delete(name);
    else state.activeSources.add(name);
    markPresetModified();
    updateFilterDrawerToggle();
    updateSourcesIndicator();
    applyFilters();
  }
  function toggleExcludeSource(name) {
    state.activeSources.delete(name);
    if (state.excludedSources.has(name)) state.excludedSources.delete(name);
    else state.excludedSources.add(name);
    markPresetModified();
    updateFilterDrawerToggle();
    updateSourcesIndicator();
    applyFilters();
  }
  function setAllSources(mode) {
    state.activeSources.clear();
    state.excludedSources.clear();
    if (mode === "none") {
      const chips = state._filterState && state._filterState.sourceCounts.length ? state._filterState.sourceCounts : state.sourceCounts;
      for (const s of chips) state.excludedSources.add(s.source);
    }
    markPresetModified();
    updateFilterDrawerToggle();
    updateSourcesIndicator();
    applyFilters();
  }
  function setAllTopics(mode) {
    state.activeConcepts.clear();
    state.excludedConcepts.clear();
    if (mode === "none") {
      const counts = state._filterState && Object.keys(state._filterState.topicCounts).length > 0 ? state._filterState.topicCounts : state.conceptCounts;
      for (const name of Object.keys(counts)) {
        if (counts[name] > 0) state.excludedConcepts.add(name);
      }
    }
    markPresetModified();
    updateFilterDrawerToggle();
    applyFilters();
  }
  async function updateStats() {
    try {
      const [statsResp, sourcesResp] = await Promise.all([fetch("/api/stats"), fetch("/api/sources")]);
      if (statsResp.ok) {
        const stats = await statsResp.json();
        _animateCount(document.getElementById("stat-total"), stats.total_stories || 0);
        const velEl = document.getElementById("stat-velocity");
        if (velEl && stats.last_1h > 0) {
          velEl.textContent = `${stats.last_1h}/hr \xB7 `;
        }
      }
      if (sourcesResp.ok) {
        const sources = await sourcesResp.json();
        if (sources.counts) state.sourceCounts = sources.counts;
      }
    } catch (err) {
      console.error("Failed to load stats:", err);
    }
  }
  function updateStoryList(features) {
    const container = document.getElementById("story-list");
    if (!features || features.length === 0) {
      container.innerHTML = '<div class="loading">No stories match your filters<br><small style="color:#484f58">Try clearing some filters or switching presets</small></div>';
      return;
    }
    const now = Date.now();
    const searchQ = (document.getElementById("search-box").value || "").trim();
    const html = features.slice(0, 150).map((f) => {
      const p = f.properties;
      const coords = f.geometry && f.geometry.coordinates ? f.geometry.coordinates : [0, 0];
      const [lon, lat] = coords;
      let concepts = p.concepts;
      if (typeof concepts === "string") try {
        concepts = JSON.parse(concepts);
      } catch {
        concepts = [];
      }
      const tags = (concepts || []).slice(0, 3).map((c) => {
        const domain = state.conceptDomainMap[c] || "general";
        const color = DOMAIN_COLORS[domain] || "#484f58";
        return `<span class="story-concept-tag clickable" style="background:${color}" data-concept="${escapeHtml(c)}">${c}</span>`;
      }).join("");
      const timeIso = p.published_at || p.scraped_at;
      const time = formatTime(timeIso);
      const fullTime = formatFullTime(timeIso);
      const storyAge = (now - new Date(timeIso).getTime()) / 36e5;
      const freshClass = storyAge < 1 ? " fresh" : "";
      const summary = p.summary ? escapeHtml(p.summary).substring(0, 300) : "";
      const bsScore = p.bright_side_score ? parseInt(p.bright_side_score) : 0;
      const isBrightStory = state.brightSideMode && bsScore >= BRIGHT_SIDE_MIN_SCORE;
      const displayTitle = isBrightStory && p.bright_side_headline ? p.bright_side_headline : p.title;
      const bsCategoryTag = isBrightStory && p.bright_side_category ? `<span class="bs-category bs-cat-${p.bright_side_category}">${p.bright_side_category}</span>` : "";
      const bsScoreTag = isBrightStory ? `<span class="bs-score" title="Bright side score: ${bsScore}/10">${"\u2600".repeat(Math.min(Math.ceil(bsScore / 2), 5))}</span>` : "";
      const sentDot = isBrightStory ? "" : p.severity ? `<span class="severity-dot severity-${p.severity}"></span>` : p.sentiment === "negative" ? '<span class="severity-dot severity-4"></span>' : p.sentiment === "positive" ? '<span class="severity-dot severity-1"></span>' : "";
      const actionTag = p.primary_action ? `<span class="story-action">${escapeHtml(p.primary_action)}</span>` : "";
      const actorPills = (p.actors || []).slice(0, 4).map((a) => {
        const roleClass = a.role === "perpetrator" ? "actor-perp" : a.role === "victim" ? "actor-victim" : a.role === "authority" ? "actor-auth" : "actor-other";
        return `<span class="actor-pill ${roleClass}" title="${escapeHtml(a.role)}">${escapeHtml(a.name)}</span>`;
      }).join("");
      const visited = state._visitedStories.has(p.url) ? " visited" : "";
      return `
            <div class="story-item${freshClass}${isBrightStory ? " bright-story" : ""}${visited}" data-id="${p.id}" data-lat="${lat}" data-lon="${lon}">
                <div class="story-title">${sentDot}${bsScoreTag}${_highlightText(escapeHtml(displayTitle), searchQ)}</div>
                ${isBrightStory && displayTitle !== p.title ? `<div class="bs-original-title">${escapeHtml(p.title)}</div>` : ""}
                ${actorPills ? `<div class="story-actors">${actorPills}</div>` : ""}
                <div class="story-meta">
                    ${bsCategoryTag}
                    <span class="story-source">${escapeHtml(p.source)}</span>
                    ${actionTag}
                    ${tags}
                    ${p.location_name ? `<span class="story-location">${escapeHtml(p.location_name)}</span>` : ""}
                    <span class="story-time" data-time="${escapeHtml(timeIso || "")}" title="${escapeHtml(fullTime)}">${time}</span>
                </div>
                ${summary ? `<div class="story-detail">
                    ${p.image_url ? `<img class="story-detail-img" src="${escapeHtml(p.image_url)}" loading="lazy" alt="" onload="this.classList.add('loaded')" onerror="this.remove()">` : ""}
                    <div class="story-summary">${summary}</div>
                    <a class="story-link" href="${escapeHtml(p.url)}" target="_blank" rel="noopener">Read full story</a>
                </div>` : ""}
            </div>
        `;
    }).join("");
    container.innerHTML = html;
    container.querySelectorAll(".story-item").forEach((item) => {
      const lat = parseFloat(item.dataset.lat);
      const lon = parseFloat(item.dataset.lon);
      const storyId = parseInt(item.dataset.id);
      item.addEventListener("click", (e) => {
        if (e.target.classList.contains("story-link")) {
          _markVisited(e.target.href);
          item.classList.add("visited");
          return;
        }
        const wasExpanded = item.classList.contains("expanded");
        container.querySelectorAll(".story-item.active").forEach((i) => i.classList.remove("active", "expanded"));
        if (!wasExpanded) {
          item.classList.add("active", "expanded");
          if (!isNaN(lat) && !isNaN(lon)) {
            state.map.flyTo({ center: [lon, lat], zoom: 6, duration: 1200 });
          }
        }
      });
    });
  }
  function highlightStory(storyId) {
    document.querySelectorAll(".story-item.active, .story-item.highlighted").forEach((i) => i.classList.remove("active", "highlighted"));
    document.querySelectorAll(".feed-story-item.feed-item-active").forEach((i) => i.classList.remove("feed-item-active"));
    const sideItem = document.querySelector(`.story-item[data-id="${storyId}"]`);
    if (sideItem) {
      sideItem.classList.add("active", "highlighted");
      sideItem.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    const feedItem = document.querySelector(`.feed-story-item[data-id="${storyId}"]`);
    if (feedItem) {
      feedItem.classList.add("feed-item-active");
      feedItem.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    const feature = state.geojsonData.features.find((f) => f.properties.id === storyId);
    if (feature && feature.geometry) {
      const [lon, lat] = feature.geometry.coordinates;
      if (!isNaN(lat) && !isNaN(lon)) {
        state.map.flyTo({ center: [lon, lat], zoom: Math.max(state.map.getZoom(), 4), duration: 800 });
      }
    }
  }
  function scrollToStory(storyId) {
    highlightStory(storyId);
  }
  async function loadEvents() {
    try {
      const evResp = await fetch("/api/events?limit=50&min_stories=2");
      if (!evResp.ok) throw new Error(`Events HTTP ${evResp.status}`);
      const evData = await evResp.json();
      state.eventsData = evData.events || [];
      state.registryData = [];
      applyFilters();
    } catch (err) {
      console.error("Failed to load events:", err);
    }
  }
  function updateEventList(events) {
    const container = document.getElementById("event-list");
    const scrollTop = container.scrollTop;
    if (!events || events.length === 0) {
      container.innerHTML = '<div class="loading">No events detected yet</div>';
      return;
    }
    const searchQ = (document.getElementById("search-box").value || "").trim();
    const html = events.map((ev) => {
      const status = ev.status || "emerging";
      const concepts = (ev.concepts || []).slice(0, 4);
      const actors = (ev.key_actors || []).slice(0, 4);
      const time = formatTime(ev.last_updated);
      const fullTime = formatFullTime(ev.last_updated);
      const severity = ev.severity;
      const isExpanded = ev.id === state.expandedEventId;
      const conceptTags = concepts.map((c) => {
        const domain = state.conceptDomainMap[c] || "general";
        const color = DOMAIN_COLORS[domain] || "#484f58";
        return `<span class="story-concept-tag clickable" style="background:${color}" data-concept="${escapeHtml(c)}">${c}</span>`;
      }).join(" ");
      const actorPills = actors.map(
        (a) => `<span class="event-actor">${escapeHtml(a)}</span>`
      ).join(" ");
      const severityDot = severity ? `<span class="severity-dot severity-${severity}"></span>` : "";
      const loc = ev.primary_location ? `<span class="story-location">${escapeHtml(ev.primary_location)}</span>` : "";
      const srcCount = ev.source_count > 1 ? `<span class="event-source-count">${ev.source_count} sources</span>` : "";
      const evPreview = ev.description ? `<div class="event-preview">${escapeHtml(ev.description)}</div>` : "";
      return `
            <div class="event-item${isExpanded ? " expanded active" : ""}" data-event-id="${ev.id}" data-lat="${ev.primary_lat || ""}" data-lon="${ev.primary_lon || ""}">
                <div class="event-header">
                    ${severityDot}
                    <span class="event-status ${status}">${status}</span>
                    <span class="event-title">${_highlightText(escapeHtml(ev.title), searchQ)}</span>
                    <span class="event-story-count">${ev.story_count}</span>
                </div>
                ${evPreview}
                <div class="event-meta">
                    ${srcCount}
                    ${conceptTags}
                    ${actorPills}
                    ${loc}
                    <span class="story-time" data-time="${escapeHtml(ev.last_updated || "")}" title="${escapeHtml(fullTime)}">${time}</span>
                    <button class="feedback-btn" data-fb-type="event" data-fb-id="${ev.id}" data-fb-title="${escapeHtml(ev.title)}" title="Report issue">&#9873;</button>
                    <button class="event-share-btn" data-event-id="${ev.id}" title="Copy link to this event">&#128279;</button>
                </div>
                <div class="event-stories-container"><div class="event-stories-inner"></div></div>
            </div>
        `;
    }).join("");
    container.innerHTML = html;
    container.scrollTop = scrollTop;
    if (state.expandedEventId && state.expandedEventStories.length) {
      const item = container.querySelector(`.event-item[data-event-id="${state.expandedEventId}"]`);
      if (item) _renderEventStories(item, state.expandedEventStories, events.find((e) => e.id === state.expandedEventId));
    }
    _wireFeedbackButtons(container);
    container.querySelectorAll(".event-share-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const url = new URL(window.location.origin);
        url.searchParams.set("event", btn.dataset.eventId);
        _copyToClipboard(btn, url.toString());
      });
    });
    container.querySelectorAll(".event-item").forEach((item) => {
      item.addEventListener("click", (e) => {
        if (e.target.tagName === "A" || e.target.classList.contains("feedback-btn") || e.target.classList.contains("event-share-btn")) return;
        const eventId = parseInt(item.dataset.eventId);
        const wasExpanded = item.classList.contains("expanded");
        container.querySelectorAll(".event-item.expanded").forEach((i) => {
          i.classList.remove("expanded", "active");
          const inner = i.querySelector(".event-stories-inner");
          if (inner) inner.innerHTML = "";
          else i.querySelector(".event-stories-container").innerHTML = "";
        });
        if (wasExpanded) {
          state.expandedEventId = null;
          state.expandedEventStories = [];
          _clearEventHighlight();
          closeInfoPanel();
          return;
        }
        item.classList.add("expanded", "active");
        state.expandedEventId = eventId;
        const lat = parseFloat(item.dataset.lat);
        const lon = parseFloat(item.dataset.lon);
        const storiesInner = item.querySelector(".event-stories-inner") || item.querySelector(".event-stories-container");
        storiesInner.innerHTML = '<div class="loading">Loading stories...</div>';
        _fetchEventStories(eventId, item, events.find((e2) => e2.id === eventId), lat, lon);
      });
      if (!_isMobile()) {
        const eventId = parseInt(item.dataset.eventId);
        const ev = events.find((e) => e.id === eventId);
        if (ev && ev.story_ids && ev.story_ids.length) {
          item.addEventListener("mouseenter", () => _showHoverHighlight(ev.story_ids));
          item.addEventListener("mouseleave", () => {
            if (state.expandedEventId === eventId) return;
            _clearHoverHighlight();
          });
        }
      }
    });
  }
  async function _fetchEventStories(eventId, eventItem, eventObj, lat, lon) {
    try {
      const resp = await fetch(`/api/events/${eventId}`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      const stories = data.stories || [];
      state.expandedEventStories = stories;
      _renderEventStories(eventItem, stories, eventObj);
      _highlightEventOnMap(stories, lat, lon);
      openEventStoriesPanel(eventObj, stories);
      if (_isMobile()) setSheetState("closed");
    } catch (err) {
      const inner = eventItem.querySelector(".event-stories-inner");
      if (inner) inner.innerHTML = '<div class="loading">Failed to load stories</div>';
      console.error("Failed to fetch event stories:", err);
    }
  }
  function _renderEventStories(eventItem, stories, eventObj) {
    const container = eventItem.querySelector(".event-stories-inner") || eventItem.querySelector(".event-stories-container");
    if (!stories.length) {
      container.innerHTML = '<div class="loading">No stories</div>';
      return;
    }
    const desc = eventObj && eventObj.description ? `<div class="event-description-text">${escapeHtml(eventObj.description)}</div>` : "";
    const storyHtml = stories.slice(0, 8).map((s) => {
      const time = formatTime(s.scraped_at);
      const fullTime = formatFullTime(s.scraped_at);
      const bsScore = s.bright_side_score ? parseInt(s.bright_side_score) : 0;
      const isBright = state.brightSideMode && bsScore >= BRIGHT_SIDE_MIN_SCORE;
      const title = isBright && s.bright_side_headline ? s.bright_side_headline : s.title;
      const bsCat = isBright && s.bright_side_category ? `<span class="bs-category bs-cat-${s.bright_side_category}">${s.bright_side_category}</span>` : "";
      const evVisited = state._visitedStories.has(s.url) ? " visited" : "";
      return `<div class="event-story-item${isBright ? " bright-story" : ""}${evVisited}" data-story-id="${s.id}" data-lat="${s.lat || ""}" data-lon="${s.lon || ""}">
            <a href="${escapeHtml(s.url)}" target="_blank" rel="noopener" class="event-story-title">${escapeHtml(title)}</a>
            <div class="event-story-meta">
                ${bsCat}
                <span class="story-source">${escapeHtml(s.source)}</span>
                <span class="story-time" data-time="${escapeHtml(s.scraped_at || "")}" title="${escapeHtml(fullTime)}">${time}</span>
            </div>
        </div>`;
    }).join("");
    const moreCount = stories.length > 8 ? stories.length - 8 : 0;
    const moreHtml = moreCount > 0 ? `<div class="event-stories-more">+ ${moreCount} more stories</div>` : "";
    container.innerHTML = desc + storyHtml + moreHtml;
    container.querySelectorAll(".event-story-item").forEach((si) => {
      si.addEventListener("click", (e) => {
        if (e.target.tagName === "A") {
          _markVisited(e.target.href);
          si.classList.add("visited");
          return;
        }
        const sLat = parseFloat(si.dataset.lat);
        const sLon = parseFloat(si.dataset.lon);
        if (!isNaN(sLat) && !isNaN(sLon)) {
          state.map.flyTo({ center: [sLon, sLat], zoom: 7, duration: 800 });
        }
        const storyId = parseInt(si.dataset.storyId);
        if (storyId) highlightStory(storyId);
      });
    });
  }
  function _highlightEventOnMap(stories, lat, lon) {
    if (stories.length > 0) {
      const ids = stories.map((s) => s.id).filter(Boolean);
      if (ids.length > 0 && state.map.getLayer("cloud-points")) {
        state.map.setPaintProperty("cloud-points", "circle-opacity",
          ["case", ["in", ["get", "id"], ["literal", ids]], 0.95, 0.08]);
      }
      const lats = stories.filter((s) => s.lat).map((s) => s.lat);
      const lons = stories.filter((s) => s.lon).map((s) => s.lon);
      if (lats.length > 1) {
        const bounds = [[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]];
        state.map.fitBounds(bounds, { padding: _getMapPadding(60), duration: 1200, maxZoom: 8 });
      } else if (!isNaN(lat) && !isNaN(lon)) {
        state.map.flyTo({ center: [lon, lat], zoom: 5, duration: 1200 });
      }
    }
  }
  function _clearEventHighlight() {
    _clearHoverHighlight();
    if (state.map && state.map.getLayer("cloud-points")) {
      state.map.setPaintProperty("cloud-points", "circle-opacity",
        ["interpolate", ["linear"], ["get", "age_hours"], 0, 0.95, 6, 0.85, 24, 0.6, 72, 0.35]);
    }
  }
  async function loadNarratives() {
    try {
      const resp = await fetch("/api/narratives");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      state.narrativesData = data.narratives || [];
      try {
        const prev = JSON.parse(localStorage.getItem("tm_narr_counts") || "{}");
        state._narrativeDeltas = {};
        state._newNarrativeIds = /* @__PURE__ */ new Set();
        const prevIds = Object.keys(prev);
        for (const n of state.narrativesData) {
          if (prev[n.id] !== void 0 && n.story_count > prev[n.id]) {
            state._narrativeDeltas[n.id] = n.story_count - prev[n.id];
          }
          if (prevIds.length > 0 && prev[n.id] === void 0) {
            state._newNarrativeIds.add(n.id);
          }
        }
        const counts = {};
        for (const n of state.narrativesData) counts[n.id] = n.story_count;
        localStorage.setItem("tm_narr_counts", JSON.stringify(counts));
      } catch {
      }
      updatePresetsBar();
      if (state.geojsonData.features.length > 0) applyFilters();
      if (state._pendingSituationId && state.narrativesData.some((n) => n.id === state._pendingSituationId)) {
        state.activeNarrativeId = state._pendingSituationId;
        state._pendingSituationId = null;
        applyFilters();
        openNarrativeStoriesPanel(state.activeNarrativeId);
        const activeEl = document.querySelector(`.situation-item[data-narrative-id="${state.activeNarrativeId}"]`);
        if (activeEl) activeEl.scrollIntoView({ block: "nearest", behavior: "smooth" });
      }
    } catch (err) {
      console.error("Failed to load narratives:", err);
    }
  }
  function updateNarrativeList(narratives) {
    const container = document.getElementById("narrative-list");
    const scrollTop = container.scrollTop;
    const filtered = narratives || [];
    const hasFilters = state._filterState && state._filterState.hasFilters;
    if (filtered.length === 0) {
      container.innerHTML = state.brightSideMode ? '<div class="loading">No bright side situations found.</div>' : hasFilters ? '<div class="loading">No situations match the current filters.<br><small style="color:#484f58">Try broadening your search or clearing filters (c)</small></div>' : '<div class="loading">No situations detected yet. Situations emerge after the system has been running for a few hours.</div>';
      return;
    }
    const searchQ = (document.getElementById("search-box").value || "").trim();
    const html = filtered.map((n) => {
      const tags = (n.theme_tags || []).map(
        (t) => `<span class="narrative-tag">${escapeHtml(t)}</span>`
      ).join(" ");
      const time = formatTime(n.last_updated);
      const fullTime = formatFullTime(n.last_updated);
      const updatedAgo = n.last_updated ? (Date.now() - new Date(n.last_updated).getTime()) / 36e5 : 999;
      const newBadge = state._newNarrativeIds.has(n.id) ? '<span class="situation-new">new</span>' : "";
      const developingBadge = !newBadge && updatedAgo < 2 ? '<span class="situation-developing-dot"></span>' : "";
      const age = n.first_seen ? formatTime(n.first_seen) : "";
      const ageLabel = age ? `<span class="situation-age">tracking ${age}</span>` : "";
      const isActive = state.activeNarrativeId === n.id;
      const desc = n.description ? `<div class="situation-detail">${_highlightText(escapeHtml(n.description), searchQ)}</div>` : "";
      const preview = n.description ? `<div class="situation-preview">${_highlightText(escapeHtml(n.description), searchQ)}</div>` : "";
      const countLabel = `${n.filteredCount}`;
      const delta = state._narrativeDeltas[n.id];
      const deltaLabel = delta ? `<span class="situation-delta">+${delta}</span>` : "";
      const srcCount = n.source_count > 1 ? `<span class="event-source-count">${n.source_count} sources</span>` : "";
      const locs = [...new Set((n.events || []).map((ev) => ev.primary_location).filter(Boolean))].slice(0, 3);
      const locsLabel = locs.length ? `<span class="situation-locations">${locs.map((l) => escapeHtml(l)).join(" \xB7 ")}</span>` : "";
      const evSlice = (n.events || []).slice(0, 5);
      const maxEvCount = Math.max(1, ...evSlice.map((ev) => ev.story_count || 0));
      const eventsHtml = evSlice.map((ev) => {
        const evTime = ev.last_updated ? formatTime(ev.last_updated) : "";
        const pct = Math.round((ev.story_count || 0) / maxEvCount * 100);
        const evLat = ev.primary_lat || "";
        const evLon = ev.primary_lon || "";
        const locBtn = evLat ? `<button class="situation-event-locate" data-ev-lat="${evLat}" data-ev-lon="${evLon}" title="Fly to event location">&#9678;</button>` : "";
        return `<div class="situation-event-row">
                <span class="situation-event-bar" style="width:${pct}%"></span>
                <span class="situation-event-title">${escapeHtml(ev.title)}</span>
                ${evTime ? `<span class="situation-event-time" data-time="${ev.last_updated}">${evTime}</span>` : ""}
                <span class="situation-event-count">${ev.story_count}</span>
                ${locBtn}
            </div>`;
      }).join("");
      const eventsBlock = eventsHtml ? `<div class="situation-events-list">${eventsHtml}</div>` : "";
      return `
            <div class="event-item situation-item${isActive ? " active expanded" : ""}" data-narrative-id="${n.id}" data-domain="${n.domain || "news"}">
                <div class="event-header">
                    <span class="situation-chevron">\u25B8</span>
                    ${newBadge}${developingBadge}
                    <span class="event-title">${_highlightText(escapeHtml(n.title), searchQ)}</span>
                    <span class="event-story-count">${countLabel}</span>${deltaLabel}
                </div>
                ${locsLabel}
                ${preview}
                <div class="situation-body">
                    <div class="situation-body-inner">
                        ${desc}
                        ${eventsBlock}
                        <div class="event-meta">
                            ${srcCount}
                            ${tags}
                            ${ageLabel}
                            <span class="story-time" data-time="${escapeHtml(n.last_updated || "")}" title="${escapeHtml(fullTime)}">${time}</span>
                            <button class="feedback-btn" data-fb-type="narrative" data-fb-id="${n.id}" data-fb-title="${escapeHtml(n.title)}" title="Report issue">&#9873;</button>
                            <button class="situation-share-btn" data-sit-id="${n.id}" title="Copy link to this situation">&#128279;</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join("");
    container.innerHTML = html;
    container.scrollTop = scrollTop;
    container.querySelectorAll(".situation-share-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const url = new URL(window.location.origin);
        url.searchParams.set("sit", btn.dataset.sitId);
        _copyToClipboard(btn, url.toString());
      });
    });
    container.querySelectorAll(".situation-event-locate").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const lat = parseFloat(btn.dataset.evLat);
        const lon = parseFloat(btn.dataset.evLon);
        if (!isNaN(lat) && !isNaN(lon)) state.map.flyTo({ center: [lon, lat], zoom: 6, duration: 1200 });
      });
    });
    _wireFeedbackButtons(container);
    container.querySelectorAll(".situation-item").forEach((item) => {
      item.addEventListener("click", (e) => {
        if (e.target.tagName === "A" || e.target.classList.contains("situation-share-btn") || e.target.classList.contains("situation-event-locate") || e.target.classList.contains("feedback-btn")) return;
        const narrativeId = parseInt(item.dataset.narrativeId);
        if (state.activeNarrativeId === narrativeId) {
          state.activeNarrativeId = null;
          item.classList.remove("active", "expanded");
          closeInfoPanel();
          _clearHoverHighlight();
          document.title = "thisminute \u2014 global news, live";
        } else {
          container.querySelectorAll(".situation-item").forEach((i) => {
            i.classList.remove("active", "expanded");
          });
          state.activeNarrativeId = narrativeId;
          item.classList.add("active", "expanded");
          openNarrativeStoriesPanel(narrativeId);
          if (_isMobile()) setSheetState("closed");
          const narr = state.narrativesData.find((n) => n.id === narrativeId);
          if (narr) {
            _showHoverHighlight(narr.story_ids, narr.domain);
            document.title = `${narr.title} \u2014 thisminute`;
          }
        }
        applyFilters();
      });
      if (!_isMobile()) {
        const narrativeId = parseInt(item.dataset.narrativeId);
        const narr = state.narrativesData.find((n) => n.id === narrativeId);
        if (narr && narr.story_ids) {
          item.addEventListener("mouseenter", () => _showHoverHighlight(narr.story_ids, narr.domain));
          item.addEventListener("mouseleave", () => {
            if (state.activeNarrativeId === narrativeId) return;
            if (state.activeNarrativeId) {
              const activeNarr = state.narrativesData.find((n) => n.id === state.activeNarrativeId);
              if (activeNarr) {
                _showHoverHighlight(activeNarr.story_ids, activeNarr.domain);
                return;
              }
            }
            _clearHoverHighlight();
          });
        }
      }
    });
  }
  function openEventStoriesPanel(eventObj, stories) {
    if (!eventObj || !stories.length) return;
    const features = stories.map((s) => {
      const fullFeature = state.geojsonData.features.find((f) => f.properties.id === s.id);
      if (fullFeature) return fullFeature;
      return {
        type: "Feature",
        geometry: { type: "Point", coordinates: [s.lon || 0, s.lat || 0] },
        properties: {
          story_id: s.id,
          id: s.id,
          title: s.title,
          url: s.url,
          source: s.source,
          summary: s.summary || "",
          scraped_at: s.scraped_at,
          published_at: s.published_at,
          concepts: s.concepts || [],
          category: s.category || "",
          image_url: s.image_url,
          bright_side_score: s.bright_side_score,
          bright_side_headline: s.bright_side_headline,
          bright_side_category: s.bright_side_category
        }
      };
    });
    openInfoPanel(eventObj.title, features);
  }
  function _navigateListItem(direction) {
    const activeView = document.querySelector(".view-btn.active");
    const isNarratives = !activeView || activeView.dataset.view === "narratives";
    const selector = isNarratives ? "#narrative-list .situation-item" : "#event-list .event-item";
    const items = [...document.querySelectorAll(selector)];
    if (items.length === 0) return;
    const activeItem = items.find((i) => i.classList.contains("active"));
    let nextIdx = 0;
    if (activeItem) {
      const curIdx = items.indexOf(activeItem);
      nextIdx = curIdx + direction;
      if (nextIdx < 0) nextIdx = 0;
      if (nextIdx >= items.length) nextIdx = items.length - 1;
      if (nextIdx === curIdx) return;
    }
    items[nextIdx].click();
    items[nextIdx].scrollIntoView({ block: "nearest", behavior: "smooth" });
  }
  function _getMapPadding(base) {
    const p = typeof base === "number" ? { top: base, bottom: base, left: base, right: base } : { ...base };
    const panelOpen = document.getElementById("info-panel")?.classList.contains("visible");
    if (panelOpen && window.innerWidth > 768) {
      p.right = Math.max(p.right || 0, 370);
    }
    return p;
  }
  function _flyToFeatures(features) {
    if (!features.length || !state.map) return;
    const coords = features.map((f) => f.geometry.coordinates).filter((c) => c[0] !== 0 || c[1] !== 0);
    if (coords.length === 0) return;
    // Don't fly to outliers — if less than 20% of features have coords, skip the flyTo
    // (avoids flying to Iran for a Harry Styles situation with 1 geocoded outlier)
    if (coords.length < features.length * 0.2 && coords.length <= 2) return;
    if (coords.length === 1) {
      state.map.flyTo({ center: coords[0], zoom: 5, duration: 1200 });
    } else {
      const lons = coords.map((c) => c[0]);
      const lats = coords.map((c) => c[1]);
      state.map.fitBounds(
        [[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]],
        { padding: _getMapPadding(60), duration: 1200, maxZoom: 8 }
      );
    }
  }
  async function openNarrativeStoriesPanel(narrativeId) {
    const narr = state.narrativesData.find((n) => n.id === narrativeId);
    if (!narr) return;
    const narrOpts = {
      description: narr.description,
      sourceCount: narr.source_count,
      storyCount: narr.story_count,
      events: narr.events || []
    };
    const storyIds = new Set(narr.story_ids || []);
    const localFeatures = state.geojsonData.features.filter((f) => storyIds.has(f.properties.id));
    if (localFeatures.length > 0) {
      openInfoPanel(narr.title, localFeatures, false, narrOpts);
      _flyToFeatures(localFeatures);
      return;
    }
    openInfoPanel(narr.title, [], true, narrOpts);
    try {
      const resp = await fetch(`/api/narratives/${narrativeId}`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      if (data.stories && data.stories.length > 0) {
        const features = data.stories.map((s) => ({
          type: "Feature",
          geometry: { type: "Point", coordinates: [s.lon || 0, s.lat || 0] },
          properties: s
        }));
        openInfoPanel(narr.title, features, false, narrOpts);
        _flyToFeatures(features);
      } else {
        openInfoPanel(narr.title, [], false, narrOpts);
      }
    } catch (err) {
      console.error("Failed to fetch narrative stories:", err);
      openInfoPanel(narr.title, []);
    }
  }
  function addMapInteractions(m, srcPrefix) {
    const pointsLayer = srcPrefix + "cloud-points";
    const countryLayer = srcPrefix + "country-fill";
    const cloudSrc = srcPrefix + "stories-cloud";
    const proxLayer = srcPrefix + "proximity-highlight";
    function _proxPad() {
      return Math.round(Math.min(120, 24 + m.getZoom() * 10));
    }
    function _openNearbyDots(point, fallbackFeatures) {
      const pad = _proxPad();
      const bbox = [[point.x - pad, point.y - pad], [point.x + pad, point.y + pad]];
      const nearby = [...m.queryRenderedFeatures(bbox, { layers: [pointsLayer] })];
      const stories = nearby.length > 0 ? nearby : fallbackFeatures || [];
      if (stories.length === 0) return false;
      _sortInfoStories(stories, state.storySortMode);
      const locName = stories[0].properties.location_name || "Stories";
      const [lon, lat] = stories[0].geometry.coordinates;
      setLocationFilter({ type: "point", lon, lat, name: locName, radius: 5 });
      openInfoPanel(locName, stories);
      return true;
    }
    m.on("click", (e) => {
      if (_isMobile()) return;
      if (e.defaultPrevented) return;
      if (state.currentProjection === "globe") {
        const lngLat = m.unproject(e.point);
        if (!lngLat || isNaN(lngLat.lng) || isNaN(lngLat.lat)) return;
      }
      if (_openNearbyDots(e.point)) return;
      const countryHit = m.queryRenderedFeatures(e.point, { layers: [countryLayer] });
      if (countryHit.length > 0) {
        const countryName = countryHit[0].properties.NAME;
        const allCloud = m.querySourceFeatures(cloudSrc);
        const countryStories = allCloud.filter((f) => {
          const cn = f.properties.country_name;
          const ln = f.properties.location_name;
          return (COUNTRY_NAME_MAP[cn] || cn) === countryName || (COUNTRY_NAME_MAP[ln] || ln) === countryName;
        });
        if (countryStories.length > 0) {
          setLocationFilter({ type: "country", name: countryName });
          openInfoPanel(countryName, countryStories);
          return;
        }
      }
      clearLocationFilter();
      closeInfoPanel();
    });
    const proxSrc = srcPrefix + "proximity-highlight";
    const _crossSvg = `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12'%3E%3Cline x1='6' y1='1' x2='6' y2='11' stroke='white' stroke-width='1.5'/%3E%3Cline x1='1' y1='6' x2='11' y2='6' stroke='white' stroke-width='1.5'/%3E%3Cline x1='6' y1='1' x2='6' y2='11' stroke='black' stroke-width='0.5'/%3E%3Cline x1='1' y1='6' x2='11' y2='6' stroke='black' stroke-width='0.5'/%3E%3C/svg%3E") 6 6, crosshair`;
    const _emptyGeo = { type: "FeatureCollection", features: [] };
    m.on("mousemove", (e) => {
      if (state.currentProjection === "globe") {
        const lngLat = m.unproject(e.point);
        if (!lngLat || isNaN(lngLat.lng) || isNaN(lngLat.lat)) {
          m.getCanvas().style.cursor = "";
          hideHoverTooltip();
          if (m.getSource(proxSrc)) m.getSource(proxSrc).setData(_emptyGeo);
          return;
        }
      }
      const dotFeatures = m.queryRenderedFeatures(e.point, { layers: [pointsLayer] });
      if (dotFeatures.length > 0) {
        m.getCanvas().style.cursor = _crossSvg;
        showHoverTooltip(e.point, dotFeatures);
        if (m.getSource(proxSrc)) m.getSource(proxSrc).setData(_emptyGeo);
        return;
      }
      const pad = _proxPad();
      const bbox = [[e.point.x - pad, e.point.y - pad], [e.point.x + pad, e.point.y + pad]];
      const nearby = m.queryRenderedFeatures(bbox, { layers: [pointsLayer] });
      if (nearby.length > 0) {
        m.getCanvas().style.cursor = _crossSvg;
        showHoverTooltip(e.point, nearby);
        if (m.getSource(proxSrc)) {
          const seen = /* @__PURE__ */ new Set();
          const features = [];
          const zoom = m.getZoom();
          for (const f of nearby) {
            const key = f.geometry.coordinates.join(",");
            if (seen.has(key)) continue;
            seen.add(key);
            const proj = m.project(f.geometry.coordinates);
            const dx = proj.x - e.point.x, dy = proj.y - e.point.y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            const ratio = Math.pow(Math.max(0, 1 - dist / pad), 2.5);
            const base = 3 + zoom * 0.4;
            const bonus = 8 + zoom * 0.5;
            const radius = Math.round((base + ratio * bonus) * 10) / 10;
            features.push({ type: "Feature", geometry: f.geometry, properties: { category: f.properties.category, blended_color: f.properties.blended_color, radius } });
          }
          m.getSource(proxSrc).setData({ type: "FeatureCollection", features });
        }
        return;
      }
      const countryHit = m.queryRenderedFeatures(e.point, { layers: [countryLayer] });
      if (countryHit.length > 0) {
        m.getCanvas().style.cursor = _crossSvg;
        if (m.getSource(proxSrc)) m.getSource(proxSrc).setData(_emptyGeo);
        hideHoverTooltip();
        return;
      }
      m.getCanvas().style.cursor = "";
      hideHoverTooltip();
      if (m.getSource(proxSrc)) m.getSource(proxSrc).setData(_emptyGeo);
    });
    const labelsLayer = srcPrefix + "event-labels";
    m.on("click", labelsLayer, (e) => {
      e.preventDefault();
      const evId = e.features[0].properties.event_id;
      const parentNarr = state.narrativesData.find(
        (n) => n.events && n.events.some((ev) => ev.id === evId)
      );
      if (parentNarr) {
        state.activeNarrativeId = parentNarr.id;
        openNarrativeStoriesPanel(parentNarr.id);
        _showHoverHighlight(parentNarr.story_ids, parentNarr.domain);
        document.title = `${parentNarr.title} \u2014 thisminute`;
        applyFilters();
        const sitEl = document.querySelector(`.situation-item[data-narrative-id="${parentNarr.id}"]`);
        if (sitEl) sitEl.scrollIntoView({ block: "nearest", behavior: "smooth" });
        return;
      }
      const regEv = state.registryData.find((r) => r.id === evId);
      if (regEv) {
        const allCloud = m.querySourceFeatures(cloudSrc);
        const matches = allCloud.filter((f) => f.properties.registry_event_id === evId);
        if (matches.length > 0) {
          openInfoPanel(regEv.map_label || regEv.registry_label, matches);
          setLocationFilter({ type: "point", lon: regEv.primary_lon, lat: regEv.primary_lat, name: regEv.map_label });
        }
      }
    });
    m.on("mouseenter", labelsLayer, () => {
      m.getCanvas().style.cursor = _crossSvg;
    });
    m.on("mouseleave", labelsLayer, () => {
      m.getCanvas().style.cursor = "";
    });
    m.on("mouseout", () => {
      hideHoverTooltip();
      if (m.getSource(proxSrc)) m.getSource(proxSrc).setData({ type: "FeatureCollection", features: [] });
    });
    if (_isMobile()) {
      let _updateReticlePreview = function() {
        const canvas = m.getCanvas();
        const cx = canvas.clientWidth / 2;
        const cy = canvas.clientHeight / 2;
        const center = { x: cx, y: cy };
        if (state.currentProjection === "globe") {
          const lngLat = m.unproject([cx, cy]);
          if (!lngLat || isNaN(lngLat.lng) || isNaN(lngLat.lat)) {
            _renderMobilePreviewEmpty();
            _reticleFeatures = [];
            return;
          }
        }
        const pad = _proxPad();
        const bbox = [[cx - pad, cy - pad], [cx + pad, cy + pad]];
        const nearby = [...m.queryRenderedFeatures(bbox, { layers: [pointsLayer] })];
        const seen = /* @__PURE__ */ new Set();
        const unique = [];
        for (const f of nearby) {
          const sid = f.properties.story_id;
          if (!seen.has(sid)) {
            seen.add(sid);
            unique.push(f);
          }
        }
        if (m.getSource(proxSrc)) {
          if (unique.length > 0) {
            const zoom = m.getZoom();
            const coordsSeen = /* @__PURE__ */ new Set();
            const proxFeatures = [];
            for (const f of unique) {
              const key = f.geometry.coordinates.join(",");
              if (coordsSeen.has(key)) continue;
              coordsSeen.add(key);
              const proj = m.project(f.geometry.coordinates);
              const dx = proj.x - cx, dy = proj.y - cy;
              const dist = Math.sqrt(dx * dx + dy * dy);
              const ratio = Math.pow(Math.max(0, 1 - dist / pad), 2.5);
              const base = 3 + zoom * 0.4;
              const bonus = 8 + zoom * 0.5;
              const radius = Math.round((base + ratio * bonus) * 10) / 10;
              proxFeatures.push({ type: "Feature", geometry: f.geometry, properties: { blended_color: f.properties.blended_color, radius } });
            }
            m.getSource(proxSrc).setData({ type: "FeatureCollection", features: proxFeatures });
          } else {
            m.getSource(proxSrc).setData(_emptyGeo);
          }
        }
        if (unique.length === 0) {
          const countryHit = m.queryRenderedFeatures([cx, cy], { layers: [countryLayer] });
          if (countryHit.length > 0) {
            const countryName = countryHit[0].properties.NAME;
            const allCloud = m.querySourceFeatures(cloudSrc);
            const countryStories = allCloud.filter((f) => {
              const cn = f.properties.country_name;
              const ln = f.properties.location_name;
              return (COUNTRY_NAME_MAP[cn] || cn) === countryName || (COUNTRY_NAME_MAP[ln] || ln) === countryName;
            });
            if (countryStories.length > 0) {
              _reticleFeatures = countryStories;
              _reticleName = countryName;
              _renderMobilePreview(countryName, countryStories);
              return;
            }
          }
          _renderMobilePreviewEmpty();
          _reticleFeatures = [];
          return;
        }
        _sortInfoStories(unique, state.storySortMode);
        _reticleFeatures = unique;
        const locName = unique[0].properties.location_name || "Stories";
        _reticleName = locName;
        _renderMobilePreview(locName, unique);
      }, _renderMobilePreview = function(title, features) {
        const first = features[0].properties;
        const color = DOMAIN_COLORS[first.category] || "#484f58";
        const count = features.length;
        const show = features.slice(0, 3);
        const lines = show.map((f) => {
          const p = f.properties;
          const c = DOMAIN_COLORS[p.category] || "#484f58";
          return `<div class="hover-story"><span class="hover-dot" style="background:${c}"></span>${escapeHtml(truncateRaw(p.title, 50))}</div>`;
        });
        if (count > 3) lines.push(`<div class="hover-more">+${count - 3} more</div>`);
        preview.innerHTML = `<div class="map-preview-title"><span class="map-preview-dot" style="background:${color}"></span>${escapeHtml(title)}</div><div class="map-preview-meta">${count} ${count === 1 ? "story" : "stories"}</div><div class="map-preview-stories">${lines.join("")}</div><div class="map-preview-tap">Tap to open</div>`;
      }, _renderMobilePreviewEmpty = function() {
        preview.innerHTML = '<div class="map-preview-empty">Move the globe to explore</div>';
      };
      const preview = document.getElementById("map-preview");
      let _reticleFeatures = [];
      let _reticleName = "";
      let _reticleTimer = null;
      m.on("move", () => {
        clearTimeout(_reticleTimer);
        _reticleTimer = setTimeout(_updateReticlePreview, 80);
      });
      m.on("idle", _updateReticlePreview);
      preview.addEventListener("click", () => {
        if (_reticleFeatures.length === 0) return;
        _sortInfoStories(_reticleFeatures, state.storySortMode);
        const first = _reticleFeatures[0];
        const [lon, lat] = first.geometry.coordinates;
        setLocationFilter({ type: "point", lon, lat, name: _reticleName, radius: 5 });
        openInfoPanel(_reticleName, _reticleFeatures);
        _renderMobilePreviewEmpty();
      });
      _renderMobilePreviewEmpty();
    }
    const feedContainer = document.getElementById("feed-buttons");
    function _updateFeedZoom() {
      const z = m.getZoom();
      const scale = z >= 3.5 ? 1 : 1 + (3.5 - Math.max(0, z)) / 3.5 * 0.6;
      feedContainer.style.transform = scale > 1 ? `scale(${scale.toFixed(3)})` : "";
      feedContainer.classList.toggle("zoom-close", z >= 6);
    }
    m.on("zoom", _updateFeedZoom);
    _updateFeedZoom();
  }
  function updateFeedButtonCounts(feedCounts) {
    document.querySelectorAll(".feed-btn").forEach((btn) => {
      const feedType = btn.dataset.feed;
      const count = feedCounts && feedCounts[feedType] || 0;
      const label = feedType === "space" ? "Space" : "Internet";
      const icon = feedType === "space" ? "\u2733" : "\u2683";
      btn.innerHTML = `${icon} ${label} <span class="feed-count">${count}</span>`;
      btn.classList.toggle("has-stories", count > 0);
    });
  }
  function toggleFeedPanel(feedType) {
    if (state.activeFeedPanel === feedType) {
      closeInfoPanel();
    } else {
      state.activeFeedPanel = feedType;
      document.querySelectorAll(".feed-btn").forEach((b) => b.classList.toggle("active", b.dataset.feed === feedType));
      populateFeedPanel(feedType);
    }
  }
  function populateFeedPanel(feedType) {
    const storyIds = state._filterState ? state._filterState.storyIds : null;
    const features = [];
    for (const f of state.geojsonData.features) {
      const p = f.properties;
      if (storyIds !== null && !storyIds.has(p.id)) continue;
      const locType = p.location_type || "terrestrial";
      if (locType === feedType) {
        features.push(f);
        continue;
      }
      let concepts = p.concepts;
      if (typeof concepts === "string") try {
        concepts = JSON.parse(concepts);
      } catch {
        concepts = [];
      }
      concepts = concepts || [];
      if (feedType === "space" && concepts.includes("space")) features.push(f);
      else if (feedType === "internet" && (concepts.includes("cyber") || concepts.includes("internet") || concepts.includes("AI"))) features.push(f);
    }
    const label = feedType === "space" ? "Space" : "Internet";
    openInfoPanel(`${label} (${features.length})`, features);
    const panel = document.getElementById("info-panel");
    panel.dataset.feed = feedType;
    panel.classList.add("feed-themed");
    stopNetworkAnimation();
    stopSpaceAnimation();
    if (feedType === "internet") startNetworkAnimation();
    if (feedType === "space") startSpaceAnimation();
  }
  function _updateSortToggleLabel() {
    const sel = document.getElementById("sort-toggle");
    if (!sel) return;
    const mode = state.currentView === "events" ? state.eventSortMode : state.narrativeSortMode;
    sel.value = mode;
  }
  function switchView(view) {
    state.currentView = view;
    const eventList = document.getElementById("event-list");
    const narrativeList = document.getElementById("narrative-list");
    document.querySelectorAll(".view-btn").forEach((btn) => {
      const isActive = btn.dataset.view === view;
      btn.classList.toggle("active", isActive);
      btn.setAttribute("aria-selected", isActive);
    });
    eventList.style.display = view === "events" ? "" : "none";
    narrativeList.style.display = view === "narratives" ? "" : "none";
    document.getElementById("sort-toggle").style.display = view === "narratives" || view === "events" ? "" : "none";
    _updateSortToggleLabel();
    const activeList = view === "events" ? eventList : narrativeList;
    activeList.scrollTop = 0;
    saveStateToURL();
  }
  async function loadPresetOverview() {
    try {
      const resp = await fetch("/api/world-overview");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      state.presetOverview = await resp.json();
      renderPresetOverview();
    } catch (err) {
      console.error("Failed to load preset overview:", err);
    }
  }
  function renderPresetOverview() {
    const bar = document.getElementById("preset-overview-bar");
    if (!state.presetOverview || !state.presetOverview.summary) {
      bar.classList.remove("visible");
      return;
    }
    const presetId = state.activePresetId || "all";
    const domain = _getPresetDomain(presetId);
    if (domain) {
      const domainNarrs = (state.narrativesData || []).filter((n) => (n.domain || "news") === domain);
      if (domainNarrs.length > 0) {
        const topNames = domainNarrs.slice(0, 3).map((n) => n.title).join(" \xB7 ");
        const extra = domainNarrs.length > 3 ? ` +${domainNarrs.length - 3} more` : "";
        bar.querySelector(".preset-overview-text").textContent = topNames + extra;
      } else {
        bar.querySelector(".preset-overview-text").textContent = "Situations will appear as stories accumulate";
      }
    } else if (presetId === "all" || !presetId) {
      bar.querySelector(".preset-overview-text").textContent = state.presetOverview.summary;
    } else {
      /* Presets without a narrative domain (planet, travel, etc.) — hide generic summary */
      bar.classList.remove("visible");
      return;
    }
    const label = bar.querySelector(".preset-overview-label");
    if (label) {
      var w = state.allPresets[presetId];
      label.style.color = w ? w.color : "#58a6ff";
    }
    bar.classList.add("visible");
  }
  function _presetShareCopied(btn) {
    btn.textContent = "\u2713";
    btn.classList.add("copied");
    btn.title = "Copied!";
    setTimeout(() => {
      btn.innerHTML = "&#x1F517;";
      btn.classList.remove("copied");
      btn.title = "Share this preset";
    }, 1500);
  }
  function _presetShareFallback(btn, url) {
    const ta = document.createElement("textarea");
    ta.value = url;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
      _presetShareCopied(btn);
    } catch (e) {
    }
    document.body.removeChild(ta);
  }
  function toggleTheme() {
    state.lightMode = !state.lightMode;
    document.body.classList.toggle("light-mode", state.lightMode);
    localStorage.setItem("thisminute-theme", state.lightMode ? "light" : "dark");
    const style = state.lightMode ? "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json" : "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";
    state.map.setStyle(style);
    state.map.once("style.load", () => {
      state.map.setProjection({ type: state.currentProjection });
      addMapLayers(state.map, "");
      addMapInteractions(state.map, "");
      setMapLabelsVisible(state.mapLabelsVisible);
      _blendLocationColors(state.cloudData.features || []);
      applyFilters();
    });
  }
  function applyInitialTheme() {
    if (state.lightMode) document.body.classList.add("light-mode");
  }
  var _DOT_THEMES = [
    { id: "domain", label: "Domain", desc: "Tinted by topic" },
    { id: "classic", label: "Classic", desc: "Uniform blue" },
    { id: "mono", label: "Mono", desc: "Single color" },
    { id: "heat", label: "Heat", desc: "Story density" },
    { id: "neon", label: "Neon", desc: "Vivid domains" }
  ];
  function setDotColorTheme(themeId) {
    state.dotColorTheme = themeId;
    localStorage.setItem("tm_dot_theme", themeId);
    _blendLocationColors(state.cloudData.features || []);
    applyFilters();
    _updateDotThemeMenu();
    _updateLegendForTheme();
  }
  function _toggleDotThemeMenu() {
    var menu = document.getElementById("dot-theme-menu");
    if (!menu) return;
    menu.classList.toggle("open");
  }
  function _updateDotThemeMenu() {
    var menu = document.getElementById("dot-theme-menu");
    if (!menu) return;
    var items = menu.querySelectorAll(".dot-theme-item");
    for (var i = 0; i < items.length; i++) {
      items[i].classList.toggle("active", items[i].dataset.theme === state.dotColorTheme);
    }
  }
  function _updateLegendColors() {
    var legendEl = document.getElementById("map-legend");
    if (!legendEl) return;
    var activePreset = state.allPresets[state.activePresetId];
    var presetRGB = activePreset && activePreset.color ? _hexToRGB(activePreset.color) : null;
    var theme = state.dotColorTheme || "domain";
    var wt = 0.35;
    legendEl.querySelectorAll(".legend-item").forEach(function(item) {
      var domain = item.dataset.domain;
      var dot = item.querySelector(".legend-dot");
      if (!dot || !domain) return;
      var domRGB = _domainRGB[domain] || _fallbackRGB;
      if (presetRGB && (theme === "domain" || theme === "classic")) {
        dot.style.background = _rgbToHex(
          domRGB[0] + (presetRGB[0] - domRGB[0]) * wt,
          domRGB[1] + (presetRGB[1] - domRGB[1]) * wt,
          domRGB[2] + (presetRGB[2] - domRGB[2]) * wt
        );
      } else {
        dot.style.background = DOMAIN_COLORS[domain] || "#484f58";
      }
    });
  }
  function _updateLegendForTheme() {
    var legendEl = document.getElementById("map-legend");
    var heatLegend = document.getElementById("heat-legend");
    if (!legendEl) return;
    var theme = state.dotColorTheme || "domain";
    if (theme === "heat") {
      legendEl.style.display = "none";
      if (heatLegend) heatLegend.style.display = "";
    } else if (theme === "classic" || theme === "mono") {
      legendEl.style.display = "none";
      if (heatLegend) heatLegend.style.display = "none";
    } else {
      /* domain or neon */
      legendEl.style.display = "";
      if (heatLegend) heatLegend.style.display = "none";
    }
  }
  function _buildDotThemeUI() {
    /* Theme button */
    var btn = document.getElementById("dot-theme-btn");
    if (!btn) return;
    btn.addEventListener("click", function(e) {
      e.stopPropagation();
      _toggleDotThemeMenu();
    });
    /* Menu items */
    var menu = document.getElementById("dot-theme-menu");
    if (!menu) return;
    for (var i = 0; i < _DOT_THEMES.length; i++) {
      var t = _DOT_THEMES[i];
      var item = document.createElement("div");
      item.className = "dot-theme-item" + (t.id === state.dotColorTheme ? " active" : "");
      item.dataset.theme = t.id;
      item.innerHTML = '<span class="dot-theme-check">&#10003;</span><span class="dot-theme-label">' + escapeHtml(t.label) + '</span><span class="dot-theme-desc">' + escapeHtml(t.desc) + '</span>';
      item.addEventListener("click", (function(tid) {
        return function(e) {
          e.stopPropagation();
          setDotColorTheme(tid);
          setTimeout(function() { _toggleDotThemeMenu(); }, 120);
        };
      })(t.id));
      menu.appendChild(item);
    }
    /* Close menu on outside click */
    document.addEventListener("click", function() {
      var m = document.getElementById("dot-theme-menu");
      if (m && m.classList.contains("open")) m.classList.remove("open");
    });
    /* Apply legend state on load */
    _updateLegendForTheme();
  }
  function saveStateToURL() {
    const params = new URLSearchParams();
    if (state.activePresetId && state.activePresetId !== "bright_side") params.set("world", state.activePresetId);
    const world = state.allPresets[state.activePresetId];
    const presetFeedTagSources = world && world.feedTags ? new Set(sourcesForTags(world.feedTags)) : null;
    if (state.activeConcepts.size > 0) params.set("in", [...state.activeConcepts].join(","));
    if (state.excludedConcepts.size > 0) params.set("ex", [...state.excludedConcepts].join(","));
    if (state.activeSources.size > 0) {
      if (!presetFeedTagSources || state.activeSources.size !== presetFeedTagSources.size || [...state.activeSources].some((s) => !presetFeedTagSources.has(s))) {
        params.set("src", [...state.activeSources].join(","));
      }
    }
    if (state.excludedSources.size > 0) params.set("xsrc", [...state.excludedSources].join(","));
    if (state.activeOrigins.size < 15) params.set("origin", [...state.activeOrigins].join(","));
    if (state.brightSideMode) params.set("bs", "1");
    if (state.curiousMode) params.set("cur", "1");
    if (state.activeNarrativeId) params.set("sit", state.activeNarrativeId);
    if (state.currentView && state.currentView !== "narratives") params.set("view", state.currentView);
    const search = document.getElementById("search-box").value.trim();
    if (search) params.set("q", search);
    const time = document.getElementById("filter-time").value;
    if (time) params.set("t", time);
    if (state.map) {
      const center = state.map.getCenter();
      const zoom = state.map.getZoom();
      if (zoom > 1.5) {
        params.set("lat", center.lat.toFixed(2));
        params.set("lon", center.lng.toFixed(2));
        params.set("z", zoom.toFixed(1));
      }
    }
    const hash = params.toString();
    history.replaceState(null, "", hash ? `#${hash}` : window.location.pathname);
  }
  function loadStateFromURL() {
    const hash = window.location.hash.slice(1);
    if (!hash) {
      const lastVisit = parseInt(localStorage.getItem("tm_last_visit") || "0");
      const hoursSinceVisit = lastVisit ? (Date.now() - lastVisit) / 36e5 : 999;
      localStorage.setItem("tm_last_visit", Date.now().toString());
      if (hoursSinceVisit > 168) {
        document.getElementById("filter-time").value = "";
      } else if (hoursSinceVisit > 24) {
        document.getElementById("filter-time").value = "168";
      } else {
        document.getElementById("filter-time").value = "24";
      }
      const defaultPresetId = _resolvePresetAlias(localStorage.getItem("tm_default_world")) || state.activePresetId;
      if (defaultPresetId && state.allPresets[defaultPresetId] && defaultPresetId !== "all") {
        const w = state.allPresets[defaultPresetId];
        if (w.feedTags && w.feedTags.length > 0) {
          applyPresetConfig(w.config);
          if (state._feedTagsReady) {
            state._feedTagsReady.then(() => {
              const effectiveConfig = w.builtIn && state.presetPrefs[defaultPresetId]?.configOverride || w.config;
              applyPresetConfig(effectiveConfig, w.keywords, w.feedTags);
              applyFilters();
            });
          }
        } else if (w.keywords && w.keywords.length > 0) {
          state._pendingPresetId = defaultPresetId;
          applyPresetConfig(w.config);
        } else {
          const effectiveConfig = w.builtIn && state.presetPrefs[defaultPresetId]?.configOverride || w.config;
          applyPresetConfig(effectiveConfig, w.keywords, w.feedTags);
        }
        updatePresetsBar();
      }
      return;
    }
    localStorage.setItem("tm_last_visit", Date.now().toString());
    const params = new URLSearchParams(hash);
    if (params.has("world")) {
      const presetId = _resolvePresetAlias(params.get("world"));
      if (state.allPresets[presetId]) {
        const w = state.allPresets[presetId];
        if (w.keywords && w.keywords.length > 0) {
          state._pendingPresetId = presetId;
          state.activePresetId = presetId;
          applyPresetConfig(w.config);
          state.presetModified = false;
          updatePresetsBar();
        } else if (w.feedTags && w.feedTags.length > 0) {
          state.activePresetId = presetId;
          applyPresetConfig(w.config);
          state.presetModified = false;
          updatePresetsBar();
          if (state._feedTagsReady) {
            state._feedTagsReady.then(() => {
              applyPresetConfig(w.config, w.keywords, w.feedTags);
              applyFilters();
            });
          }
        } else {
          applyPresetConfig(w.config, w.keywords, w.feedTags);
          state.activePresetId = presetId;
          state.presetModified = false;
          updatePresetsBar();
        }
      }
    }
    if (params.has("in")) {
      params.get("in").split(",").forEach((c) => state.activeConcepts.add(c.trim()));
      if (params.has("world")) state.presetModified = true;
    }
    if (params.has("ex")) {
      params.get("ex").split(",").forEach((c) => state.excludedConcepts.add(c.trim()));
      if (params.has("world")) state.presetModified = true;
    }
    if (params.has("src")) {
      params.get("src").split(",").forEach((s) => state.activeSources.add(s.trim()));
      if (params.has("world")) state.presetModified = true;
    }
    if (params.has("xsrc")) {
      params.get("xsrc").split(",").forEach((s) => state.excludedSources.add(s.trim()));
      if (params.has("world")) state.presetModified = true;
    }
    if (params.has("origin")) {
      state.activeOrigins = new Set(params.get("origin").split(",").map((s) => s.trim()));
      document.querySelectorAll(".origin-btn").forEach((btn) => {
        btn.classList.toggle("active", state.activeOrigins.has(btn.dataset.origin));
      });
      if (params.has("world")) state.presetModified = true;
    }
    if (params.has("bs")) {
      state.brightSideMode = true;
      if (params.has("world")) state.presetModified = true;
    }
    if (params.has("cur")) {
      state.curiousMode = true;
      if (params.has("world")) state.presetModified = true;
    }
    if (params.has("q")) {
      document.getElementById("search-box").value = params.get("q");
      if (params.has("world")) state.presetModified = true;
    }
    if (params.has("t")) {
      document.getElementById("filter-time").value = params.get("t");
      if (params.has("world")) state.presetModified = true;
    }
    if (params.has("sit")) {
      state._pendingSituationId = parseInt(params.get("sit"));
    }
    if (!state._pendingSituationId) {
      const qp = new URLSearchParams(window.location.search);
      if (qp.has("sit")) state._pendingSituationId = parseInt(qp.get("sit"));
    }
    if (params.has("view") && (params.get("view") === "events" || params.get("view") === "narratives")) {
      switchView(params.get("view"));
    }
    if (params.has("lat") && params.has("lon") && params.has("z")) {
      state._pendingMapView = {
        lat: parseFloat(params.get("lat")),
        lon: parseFloat(params.get("lon")),
        zoom: parseFloat(params.get("z"))
      };
    }
    if (state.presetModified) updatePresetsBar();
  }
  document.addEventListener("DOMContentLoaded", async () => {
    applyInitialTheme();
    initMobileSheet();
    initMobileMapControls();
    initInfoPanelSwipe(closeInfoPanel);
    loadFeedTags();
    loadPresets();
    renderPresetsBar();
    captureFirstVisitFlag();
    loadStateFromURL();
    initMap();
    let searchTimer = null;
    const searchBox = document.getElementById("search-box");
    const searchClear = document.getElementById("search-clear");
    searchBox.addEventListener("input", () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        applyFilters();
      }, 300);
      searchClear.classList.toggle("visible", !!searchBox.value.trim());
    });
    searchClear.addEventListener("click", () => {
      searchBox.value = "";
      searchClear.classList.remove("visible");
      applyFilters();
      searchBox.focus();
    });
    document.getElementById("filter-time").addEventListener("change", () => {
      applyFilters();
    });
    document.getElementById("filter-opinion").addEventListener("change", () => {
      applyFilters();
    });
    document.getElementById("filter-drawer-toggle").addEventListener("click", toggleFilterDrawer);
    document.getElementById("search-toggle").addEventListener("click", toggleSearch);
    searchBox.addEventListener("blur", () => {
      if (!searchBox.value.trim()) {
        document.getElementById("search-expand").classList.remove("active");
        document.getElementById("search-toggle").classList.remove("active");
        searchClear.classList.remove("visible");
      }
    });
    document.getElementById("btn-clear-all-filters").addEventListener("click", clearAllFilters);
    document.getElementById("btn-sources-all").addEventListener("click", () => setAllSources("all"));
    document.getElementById("btn-sources-none").addEventListener("click", () => setAllSources("none"));
    document.getElementById("source-search").addEventListener("input", (e) => {
      const q = e.target.value.toLowerCase().trim();
      document.querySelectorAll("#source-chips .source-chip").forEach((chip) => {
        chip.style.display = !q || chip.dataset.source.toLowerCase().includes(q) ? "" : "none";
      });
    });
    document.getElementById("source-chips-toggle").addEventListener("click", () => {
      const chips = document.getElementById("source-chips");
      const toggle = document.getElementById("source-chips-toggle");
      if (chips.classList.toggle("expanded")) {
        toggle.textContent = "Show less \u25B4";
      } else {
        toggle.textContent = "Show all \u25BE";
        toggle.classList.add("visible");
      }
    });
    document.querySelectorAll(".origin-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const origin = btn.dataset.origin;
        if (state.activeOrigins.has(origin)) {
          if (state.activeOrigins.size > 1) {
            state.activeOrigins.delete(origin);
            btn.classList.remove("active");
          }
        } else {
          state.activeOrigins.add(origin);
          btn.classList.add("active");
        }
        markPresetModified();
        updateFilterDrawerToggle();
        applyFilters();
      });
    });
    document.getElementById("btn-topics-all").addEventListener("click", () => setAllTopics("all"));
    document.getElementById("btn-topics-none").addEventListener("click", () => setAllTopics("none"));
    document.getElementById("preset-overview-bar").addEventListener("click", togglePresetOverview);
    document.getElementById("sidebar-toggle").addEventListener("click", toggleSidebar);
    document.getElementById("labels-toggle").addEventListener("click", toggleMapLabels);
    document.getElementById("globe-toggle").addEventListener("click", toggleGlobe);
    document.getElementById("globe-toggle").addEventListener("dblclick", resetGlobeAuto);
    document.querySelectorAll(".feed-btn").forEach((btn) => {
      btn.addEventListener("click", () => toggleFeedPanel(btn.dataset.feed));
    });
    const legendEl = document.getElementById("map-legend");
    for (const [cat, color] of Object.entries(DOMAIN_COLORS)) {
      const item = document.createElement("div");
      item.className = "legend-item";
      item.dataset.domain = cat;
      item.innerHTML = `<span class="legend-dot" style="background:${color}"></span>${cat.charAt(0).toUpperCase() + cat.slice(1)}`;
      item.style.cursor = "pointer";
      item.addEventListener("click", () => {
        const concepts = [];
        for (const [name, domain] of Object.entries(state.conceptDomainMap)) {
          if (domain === cat) concepts.push(name);
        }
        if (concepts.length === 0) return;
        state.activeConcepts.clear();
        concepts.forEach((c) => state.activeConcepts.add(c));
        applyFilters();
        markPresetModified();
      });
      item.addEventListener("mouseenter", () => {
        if (!state.map || !state.map.getLayer("cloud-points")) return;
        state.map.setPaintProperty("cloud-points", "circle-opacity",
          ["case", ["==", ["get", "category"], cat], 0.95, 0.15]);
      });
      item.addEventListener("mouseleave", () => {
        if (!state.map || !state.map.getLayer("cloud-points")) return;
        state.map.setPaintProperty("cloud-points", "circle-opacity",
          ["interpolate", ["linear"], ["get", "age_hours"], 0, 0.95, 6, 0.85, 24, 0.6, 72, 0.35]);
      });
      legendEl.appendChild(item);
    }
    const legendToggle = document.getElementById("legend-toggle");
    if (legendToggle) {
      legendToggle.addEventListener("click", () => {
        legendEl.classList.toggle("collapsed");
        legendToggle.innerHTML = legendEl.classList.contains("collapsed") ? "&#9632;" : "&#9662;";
      });
    }
    _buildDotThemeUI();
    _initTimeBadge();
    document.addEventListener("click", (e) => {
      const tag = e.target.closest(".story-concept-tag.clickable");
      if (!tag || !tag.dataset.concept) return;
      e.stopPropagation();
      state.activeConcepts.clear();
      state.activeConcepts.add(tag.dataset.concept);
      applyFilters();
      markPresetModified();
    });
    document.getElementById("theme-toggle").addEventListener("click", toggleTheme);
    document.getElementById("share-view-btn").addEventListener("click", () => {
      _copyToClipboard(document.getElementById("share-view-btn"), window.location.href);
    });
    document.getElementById("preset-share-btn").addEventListener("click", () => {
      const btn = document.getElementById("preset-share-btn");
      const url = window.location.href;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(() => {
          _presetShareCopied(btn);
        }).catch(() => {
          _presetShareFallback(btn, url);
        });
      } else {
        _presetShareFallback(btn, url);
      }
    });
    document.getElementById("menu-btn").addEventListener("click", (e) => {
      e.stopPropagation();
      document.getElementById("main-menu").classList.toggle("visible");
    });
    document.getElementById("menu-shortcuts").addEventListener("click", () => {
      document.getElementById("main-menu").classList.remove("visible");
      document.getElementById("shortcuts-overlay").classList.add("visible");
    });
    document.getElementById("menu-pick-presets").addEventListener("click", () => {
      document.getElementById("main-menu").classList.remove("visible");
      showPresetPicker();
    });
    document.getElementById("menu-feeds").addEventListener("click", () => {
      document.getElementById("main-menu").classList.remove("visible");
      openUserFeedsDialog();
    });
    document.getElementById("menu-replay-tour").addEventListener("click", () => {
      document.getElementById("main-menu").classList.remove("visible");
      replayPresetTour();
    });
    document.getElementById("menu-about").addEventListener("click", () => {
      document.getElementById("main-menu").classList.remove("visible");
      document.getElementById("about-dialog").classList.add("visible");
    });
    document.getElementById("menu-feedback").addEventListener("click", () => {
      document.getElementById("main-menu").classList.remove("visible");
      openFeedbackDialog(null);
    });
    document.addEventListener("click", (e) => {
      const menu = document.getElementById("main-menu");
      if (menu.classList.contains("visible") && !menu.contains(e.target) && e.target.id !== "menu-btn") {
        menu.classList.remove("visible");
      }
    });
    function _clearSourceSearch() {
      const input = document.getElementById("source-search");
      if (input) {
        input.value = "";
      }
      document.querySelectorAll("#source-chips .source-chip").forEach((c) => {
        c.style.display = "";
      });
    }
    document.getElementById("stat-sources").addEventListener("click", () => {
      const popup = document.getElementById("sources-popup");
      if (popup.classList.contains("visible")) {
        popup.classList.remove("visible");
        _clearSourceSearch();
        return;
      }
      _clearSourceSearch();
      renderSourceChips();
      popup.classList.add("visible");
    });
    document.getElementById("sources-popup-close").addEventListener("click", () => {
      document.getElementById("sources-popup").classList.remove("visible");
      _clearSourceSearch();
    });
    document.addEventListener("click", (e) => {
      const popup = document.getElementById("sources-popup");
      if (!popup.classList.contains("visible")) return;
      const trigger = document.getElementById("stat-sources");
      if (!popup.contains(e.target) && e.target !== trigger) {
        popup.classList.remove("visible");
        _clearSourceSearch();
      }
    });
    document.getElementById("presets-bar").addEventListener("scroll", updatePresetsBarOverflow);
    document.getElementById("presets-more-btn").addEventListener("click", togglePresetsPanel);
    document.getElementById("presets-panel-close").addEventListener("click", closePresetsPanel);
    document.getElementById("presets-save-btn").addEventListener("click", () => showSavePresetDialog());
    document.getElementById("preset-save-cancel").addEventListener("click", closeSavePresetDialog);
    document.getElementById("preset-save-confirm").addEventListener("click", confirmSavePreset);
    document.getElementById("preset-save-name").addEventListener("keydown", (e) => {
      if (e.key === "Enter") confirmSavePreset();
    });
    document.getElementById("preset-picker-done").addEventListener("click", () => {
      confirmPresetPicker();
    });
    document.getElementById("user-feeds-close").addEventListener("click", closeUserFeedsDialog);
    document.getElementById("user-feed-add-btn").addEventListener("click", _addUserFeed);
    document.getElementById("user-feed-url").addEventListener("keydown", (e) => {
      if (e.key === "Enter") _addUserFeed();
    });
    document.getElementById("user-feeds-dialog").addEventListener("click", (e) => {
      if (e.target.id === "user-feeds-dialog") closeUserFeedsDialog();
    });
    document.getElementById("feedback-cancel").addEventListener("click", closeFeedbackDialog);
    document.getElementById("feedback-submit").addEventListener("click", submitFeedback);
    document.querySelectorAll(".feedback-type-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".feedback-type-btn").forEach((b) => b.classList.remove("selected"));
        btn.classList.toggle("selected");
      });
    });
    document.getElementById("feedback-dialog").addEventListener("click", (e) => {
      if (e.target.id === "feedback-dialog") closeFeedbackDialog();
    });
    document.addEventListener("click", (e) => {
      const panel = document.getElementById("presets-panel");
      if (!panel.classList.contains("visible")) return;
      const moreBtn = document.getElementById("presets-more-btn");
      if (!panel.contains(e.target) && e.target !== moreBtn) {
        panel.classList.remove("visible");
      }
    });
    document.getElementById("new-badge").addEventListener("click", () => {
      document.getElementById("new-badge").classList.remove("visible");
      state.pendingNewCount = 0;
      const activeList = document.getElementById(state.currentView === "events" ? "event-list" : "narrative-list");
      if (activeList) activeList.scrollTop = 0;
    });
    document.getElementById("info-panel-close").addEventListener("click", closeInfoPanel);
    document.getElementById("shortcuts-overlay").addEventListener("click", (e) => {
      if (e.target.id === "shortcuts-overlay") e.target.classList.remove("visible");
    });
    document.addEventListener("keydown", (e) => {
      const _inTextInput = ["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement.tagName);
      if (e.key === "/" && !e.shiftKey && !_inTextInput) {
        e.preventDefault();
        document.getElementById("search-expand").classList.add("active");
        document.getElementById("search-toggle").classList.add("active");
        document.getElementById("search-box").focus();
      }
      if (e.key === "Escape") {
        const welcomeDialog = document.getElementById("welcome-dialog");
        if (welcomeDialog && welcomeDialog.classList.contains("visible")) {
          welcomeDialog.classList.remove("visible");
          showOnboardingHint();
          return;
        }
        const presetPickerDialog = document.getElementById("preset-picker-dialog");
        if (presetPickerDialog && presetPickerDialog.classList.contains("visible")) {
          confirmPresetPicker();
          return;
        }
        const aboutDialog = document.getElementById("about-dialog");
        if (aboutDialog && aboutDialog.classList.contains("visible")) {
          aboutDialog.classList.remove("visible");
          return;
        }
        const mainMenu = document.getElementById("main-menu");
        if (mainMenu.classList.contains("visible")) {
          mainMenu.classList.remove("visible");
          return;
        }
        const userFeedsDialog = document.getElementById("user-feeds-dialog");
        if (userFeedsDialog.classList.contains("visible")) {
          closeUserFeedsDialog();
          return;
        }
        const feedbackDialog = document.getElementById("feedback-dialog");
        if (feedbackDialog.classList.contains("visible")) {
          closeFeedbackDialog();
          return;
        }
        const presetsPanel = document.getElementById("presets-panel");
        if (presetsPanel.classList.contains("visible")) {
          presetsPanel.classList.remove("visible");
          return;
        }
        const saveDialog = document.getElementById("preset-save-dialog");
        if (saveDialog.classList.contains("visible")) {
          closeSavePresetDialog();
          return;
        }
        const dotThemeMenu = document.getElementById("dot-theme-menu");
        if (dotThemeMenu && dotThemeMenu.classList.contains("open")) {
          dotThemeMenu.classList.remove("open");
          return;
        }
        const sourcesPopup = document.getElementById("sources-popup");
        if (sourcesPopup.classList.contains("visible")) {
          sourcesPopup.classList.remove("visible");
          return;
        }
        const infoPanel = document.getElementById("info-panel");
        if (infoPanel.classList.contains("visible")) {
          closeInfoPanel();
          if (state.activeNarrativeId) {
            state.activeNarrativeId = null;
            document.querySelectorAll(".situation-item.active").forEach((i) => {
              i.classList.remove("active", "expanded");
            });
            _clearHoverHighlight();
            document.title = "thisminute \u2014 global news, live";
            applyFilters();
          }
          return;
        }
        const search = document.getElementById("search-box");
        if (document.activeElement === search) {
          search.value = "";
          search.blur();
          applyFilters();
        }
      }
      const overlay = document.getElementById("shortcuts-overlay");
      if (overlay.classList.contains("visible")) {
        overlay.classList.remove("visible");
        return;
      }
      if (!_inTextInput) {
        if (e.key === "s") toggleSidebar();
        if (e.key === "g") toggleGlobe();
        if (e.key === "l") toggleTheme();
        if (e.key === "m") toggleMapLabels();
        if (e.key === "w") {
          const visibleIds = _getVisiblePresetEntries().map(([id]) => id);
          if (visibleIds.length === 0) return;
          const currentIdx = visibleIds.indexOf(state.activePresetId);
          const nextIdx = (currentIdx + 1) % visibleIds.length;
          switchPreset(visibleIds[nextIdx]);
        }
        if (e.key === "e") {
          switchView(state.currentView === "events" ? "narratives" : "events");
        }
        if (e.key === "?" || e.key === "/" && e.shiftKey) {
          e.preventDefault();
          document.getElementById("shortcuts-overlay").classList.add("visible");
        }
        if (e.key === "j" || e.key === "k") {
          e.preventDefault();
          _navigateListItem(e.key === "j" ? 1 : -1);
        }
        if (e.key === "o" || e.key === "Enter") {
          const link = document.querySelector("#info-panel.visible .info-card-link");
          if (link) {
            window.open(link.href, "_blank", "noopener");
          }
        }
        if (e.key === "r") {
          loadAll();
          loadEvents();
          loadNarratives();
          const fresh = document.getElementById("stat-freshness");
          if (fresh) {
            fresh.textContent = "refreshing...";
            fresh.classList.add("live");
          }
        }
        if (e.key === "c") {
          clearAllFilters();
        }
      }
    });
    document.querySelectorAll(".view-btn").forEach((btn) => {
      btn.addEventListener("click", () => switchView(btn.dataset.view));
    });
    document.getElementById("sort-toggle").addEventListener("change", (e) => {
      if (state.currentView === "events") {
        state.eventSortMode = e.target.value;
      } else {
        state.narrativeSortMode = e.target.value;
      }
      applyFilters();
    });
    if (!state.activePresetId) switchPreset("all");
    setInterval(loadEvents, EVENTS_INTERVAL);
    setInterval(loadPresetOverview, EVENTS_INTERVAL);
    setInterval(loadNarratives, NARRATIVES_INTERVAL);
    setInterval(pollUpdates, POLL_INTERVAL);
    setInterval(updateFreshnessIndicator, 1e4);
    setInterval(() => {
      document.querySelectorAll("[data-time]:not(.tb-option)").forEach((el) => {
        const iso = el.dataset.time;
        if (iso) el.textContent = formatTime(iso);
      });
    }, 6e4);
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) {
        const narr = state.activeNarrativeId ? state.narrativesData.find((n) => n.id === state.activeNarrativeId) : null;
        document.title = narr ? `${narr.title} \u2014 thisminute` : "thisminute \u2014 global news, live";
      }
    });
  });
  function toggleSidebar() {
    const body = document.body;
    const btn = document.getElementById("sidebar-toggle");
    body.classList.toggle("sidebar-collapsed");
    btn.innerHTML = body.classList.contains("sidebar-collapsed") ? "&rsaquo;" : "&lsaquo;";
    setTimeout(() => state.map.resize(), 350);
  }
  var _feedbackTarget = null;
  function _getBrowserHash() {
    const raw = navigator.userAgent + screen.width + "x" + screen.height;
    let h = 0;
    for (let i = 0; i < raw.length; i++) {
      h = (h << 5) - h + raw.charCodeAt(i) | 0;
    }
    return Math.abs(h).toString(36);
  }
  function openFeedbackDialog(target) {
    _feedbackTarget = target;
    const dialog = document.getElementById("feedback-dialog");
    const title = document.getElementById("feedback-dialog-title");
    const typeOptions = document.getElementById("feedback-type-options");
    const message = document.getElementById("feedback-message");
    const hint = document.getElementById("feedback-hint");
    message.value = "";
    document.querySelectorAll(".feedback-type-btn").forEach((b) => b.classList.remove("selected"));
    if (!target) {
      title.textContent = "Send Feedback";
      typeOptions.style.display = "none";
      message.placeholder = "What's on your mind?";
      hint.textContent = "Your feedback helps us improve thisminute.";
    } else {
      const truncTitle = target.title && target.title.length > 50 ? target.title.slice(0, 50) + "\u2026" : target.title || "";
      title.textContent = "Report: " + truncTitle;
      typeOptions.style.display = "flex";
      message.placeholder = "What's wrong? (optional)";
      hint.textContent = "Your feedback helps improve clustering.";
    }
    dialog.classList.add("visible");
    const submitBtn = document.getElementById("feedback-submit");
    submitBtn.textContent = "Send";
    submitBtn.disabled = false;
  }
  function closeFeedbackDialog() {
    document.getElementById("feedback-dialog").classList.remove("visible");
    _feedbackTarget = null;
  }
  async function submitFeedback() {
    const now = Date.now();
    if (now < state._feedbackCooldownUntil) {
      const secs = Math.ceil((state._feedbackCooldownUntil - now) / 1e3);
      document.getElementById("feedback-hint").textContent = `Please wait ${secs}s before sending again.`;
      return;
    }
    if (state._feedbackSessionCount >= 10) {
      document.getElementById("feedback-hint").textContent = "Session feedback limit reached. Thank you!";
      return;
    }
    const selectedType = document.querySelector(".feedback-type-btn.selected");
    const feedbackType = _feedbackTarget ? selectedType ? selectedType.dataset.type : "general" : "general";
    const message = document.getElementById("feedback-message").value.trim();
    if (!_feedbackTarget && !message) {
      document.getElementById("feedback-hint").textContent = "Please enter a message.";
      return;
    }
    const submitBtn = document.getElementById("feedback-submit");
    submitBtn.disabled = true;
    submitBtn.textContent = "Sending...";
    try {
      const resp = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          feedback_type: feedbackType,
          target_type: _feedbackTarget ? _feedbackTarget.type : null,
          target_id: _feedbackTarget ? _feedbackTarget.id : null,
          target_title: _feedbackTarget ? _feedbackTarget.title : null,
          message,
          context: { world: state.activePresetId },
          browser_hash: _getBrowserHash()
        })
      });
      if (!resp.ok) throw new Error("Failed");
      state._feedbackCooldownUntil = Date.now() + 3e4;
      state._feedbackSessionCount++;
      submitBtn.textContent = "Sent!";
      setTimeout(() => closeFeedbackDialog(), 1e3);
    } catch (err) {
      document.getElementById("feedback-hint").textContent = "Failed to send. Try again.";
      submitBtn.disabled = false;
      submitBtn.textContent = "Send";
    }
  }
  /* ---- User Feeds ---- */
  function openUserFeedsDialog() {
    var dialog = document.getElementById("user-feeds-dialog");
    dialog.classList.add("visible");
    _loadUserFeeds();
  }
  function closeUserFeedsDialog() {
    document.getElementById("user-feeds-dialog").classList.remove("visible");
    document.getElementById("user-feed-url").value = "";
    document.getElementById("user-feed-url").classList.remove("input-error");
    var hint = document.getElementById("user-feeds-hint");
    hint.textContent = "Added feeds appear on the map within 15 minutes.";
    hint.style.color = "";
  }
  async function _loadUserFeeds() {
    var bh = _getBrowserHash();
    var list = document.getElementById("user-feeds-list");
    var counter = document.getElementById("user-feeds-count");
    try {
      var resp = await fetch("/api/user-feeds?hash=" + encodeURIComponent(bh));
      if (!resp.ok) throw new Error("Failed to load feeds");
      var feeds = await resp.json();
      counter.textContent = feeds.length + "/20";
      if (feeds.length === 0) {
        list.innerHTML = '<div class="user-feeds-empty">No feeds added yet. Paste an RSS URL below to get started.</div>';
        return;
      }
      list.innerHTML = "";
      feeds.forEach(function(feed) {
        var item = document.createElement("div");
        item.className = "user-feed-item";
        var statusClass = feed.last_error ? "error" : (feed.last_fetched ? "active" : "pending");
        var statusTitle = feed.last_error ? "Error: " + _escHtml(feed.last_error) : (feed.last_fetched ? "Active" : "Pending first fetch");
        var errorHtml = feed.last_error ? '<div class="user-feed-error-msg" title="' + _escHtml(feed.last_error).replace(/"/g, "&quot;") + '">' + _escHtml(feed.last_error) + '</div>' : "";
        item.innerHTML = '<div class="user-feed-info">' +
          '<div class="user-feed-title" title="' + _escHtml(feed.title || "").replace(/"/g, "&quot;") + '">' + _escHtml(feed.title || feed.url) + '</div>' +
          '<div class="user-feed-url" title="' + _escHtml(feed.url).replace(/"/g, "&quot;") + '">' + _escHtml(feed.url) + '</div>' +
          errorHtml +
          '</div>' +
          '<div class="user-feed-meta">' +
          '<span class="user-feed-tag">' + _escHtml(feed.feed_tag) + '</span>' +
          '<span class="user-feed-status ' + statusClass + '" title="' + statusTitle.replace(/"/g, "&quot;") + '"></span>' +
          '</div>' +
          '<button class="user-feed-delete" title="Remove feed">&times;</button>';
        var deleteBtn = item.querySelector(".user-feed-delete");
        deleteBtn.addEventListener("click", function() {
          _deleteUserFeed(feed.id);
        });
        list.appendChild(item);
      });
    } catch (err) {
      list.innerHTML = '<div class="user-feeds-empty">Failed to load feeds.</div>';
      counter.textContent = "";
    }
  }
  function _escHtml(str) {
    var d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
  }
  async function _addUserFeed() {
    var urlInput = document.getElementById("user-feed-url");
    var tagSelect = document.getElementById("user-feed-tag");
    var addBtn = document.getElementById("user-feed-add-btn");
    var hint = document.getElementById("user-feeds-hint");
    var url = urlInput.value.trim();
    if (!url) {
      urlInput.classList.add("input-error");
      setTimeout(function() { urlInput.classList.remove("input-error"); }, 600);
      return;
    }
    addBtn.disabled = true;
    addBtn.textContent = "Adding...";
    hint.textContent = "Validating feed...";
    hint.style.color = "";
    try {
      var resp = await fetch("/api/user-feeds", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: url,
          feed_tag: tagSelect.value,
          browser_hash: _getBrowserHash()
        })
      });
      var data = await resp.json();
      if (!resp.ok) {
        hint.textContent = data.error || "Failed to add feed.";
        hint.style.color = "#f85149";
        urlInput.classList.add("input-error");
        setTimeout(function() { urlInput.classList.remove("input-error"); }, 600);
        addBtn.disabled = false;
        addBtn.textContent = "Add";
        return;
      }
      urlInput.value = "";
      hint.textContent = "Feed added! Stories will appear within 15 minutes.";
      hint.style.color = "#3fb950";
      setTimeout(function() {
        hint.textContent = "Added feeds appear on the map within 15 minutes.";
        hint.style.color = "";
      }, 3000);
      _loadUserFeeds();
    } catch (err) {
      hint.textContent = "Network error. Please try again.";
      hint.style.color = "#f85149";
    }
    addBtn.disabled = false;
    addBtn.textContent = "Add";
  }
  async function _deleteUserFeed(feedId) {
    var bh = _getBrowserHash();
    var hint = document.getElementById("user-feeds-hint");
    try {
      var resp = await fetch("/api/user-feeds/" + feedId + "?hash=" + encodeURIComponent(bh), {
        method: "DELETE"
      });
      if (!resp.ok) {
        var data = await resp.json();
        hint.textContent = data.error || "Failed to remove feed.";
        hint.style.color = "#f85149";
        return;
      }
      _loadUserFeeds();
    } catch (err) {
      hint.textContent = "Network error. Please try again.";
      hint.style.color = "#f85149";
    }
  }
})();
