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
    activeOrigins: /* @__PURE__ */ new Set(["rss", "gdelt"]),
    brightSideMode: false,
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
    worldOverview: null,
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
    // Worlds
    allWorlds: {},
    activeWorldId: "news",
    worldModified: false,
    _pendingWorldId: null,
    worldPrefs: {},
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
  function _hexToHSL(hex) {
    const r = parseInt(hex.slice(1, 3), 16) / 255;
    const g = parseInt(hex.slice(3, 5), 16) / 255;
    const b = parseInt(hex.slice(5, 7), 16) / 255;
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    const l = (max + min) / 2;
    if (max === min) return [0, 0, l];
    const d = max - min;
    const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    let h;
    if (max === r) h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
    else if (max === g) h = ((b - r) / d + 2) / 6;
    else h = ((r - g) / d + 4) / 6;
    return [h * 360, s, l];
  }
  function _hslToHex(h, s, l) {
    h = ((h % 360) + 360) % 360;
    const c = (1 - Math.abs(2 * l - 1)) * s;
    const x = c * (1 - Math.abs((h / 60) % 2 - 1));
    const m = l - c / 2;
    let r, g, b;
    if (h < 60) { r = c; g = x; b = 0; }
    else if (h < 120) { r = x; g = c; b = 0; }
    else if (h < 180) { r = 0; g = c; b = x; }
    else if (h < 240) { r = 0; g = x; b = c; }
    else if (h < 300) { r = x; g = 0; b = c; }
    else { r = c; g = 0; b = x; }
    const toHex = (v) => Math.round(Math.min(255, Math.max(0, (v + m) * 255))).toString(16).padStart(2, "0");
    return "#" + toHex(r) + toHex(g) + toHex(b);
  }
  var _domainHSL = {};
  for (var _dc in DOMAIN_COLORS) _domainHSL[_dc] = _hexToHSL(DOMAIN_COLORS[_dc]);
  var _fallbackHSL = _hexToHSL("#484f58");
  function _blendLocationColors(features) {
    try {
      var byCoord = {};
      for (var i = 0; i < features.length; i++) {
        var f = features[i];
        if (!f.geometry || !f.geometry.coordinates) continue;
        var key = f.geometry.coordinates[0] + "," + f.geometry.coordinates[1];
        if (!byCoord[key]) byCoord[key] = [];
        byCoord[key].push(f);
      }
      for (var k in byCoord) {
        var group = byCoord[k];
        var catCounts = {}, total = 0;
        for (var j = 0; j < group.length; j++) {
          var cat = group[j].properties.category;
          catCounts[cat] = (catCounts[cat] || 0) + 1;
          total++;
        }
        var sinSum = 0, cosSum = 0, sSum = 0, lSum = 0;
        for (var c in catCounts) {
          var hsl = _domainHSL[c] || _fallbackHSL;
          var w = catCounts[c] / total;
          var hRad = hsl[0] * Math.PI / 180;
          sinSum += w * Math.sin(hRad);
          cosSum += w * Math.cos(hRad);
          sSum += w * hsl[1];
          lSum += w * hsl[2];
        }
        var avgH = Math.atan2(sinSum, cosSum) * 180 / Math.PI;
        var blended = _hslToHex(avgH, sSum, lSum);
        if (!/^#[0-9a-f]{6}$/i.test(blended)) blended = null;
        for (var j2 = 0; j2 < group.length; j2++) {
          if (blended) group[j2].properties.blended_color = blended;
        }
      }
    } catch (e) {
      console.error("_blendLocationColors failed:", e);
    }
    for (var ii = 0; ii < features.length; ii++) {
      if (!features[ii].properties.blended_color) {
        var cc = features[ii].properties.category;
        features[ii].properties.blended_color = DOMAIN_COLORS[cc] || "#484f58";
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
    news: {
      label: "News",
      color: "#1f6feb",
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
      }
    },
    sports: {
      label: "Sports",
      color: "#2ea043",
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
      feedTags: ["sports"]
    },
    entertainment: {
      label: "Entertainment",
      color: "#a855f7",
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
      feedTags: ["entertainment"]
    },
    positive: {
      label: "Positive",
      color: "#f5a623",
      builtIn: true,
      config: {
        activeConcepts: [],
        excludedConcepts: [],
        activeSources: [],
        excludedSources: [],
        activeOrigins: ["rss", "gdelt"],
        brightSideMode: true,
        searchText: "",
        timeHours: "",
        hideOpinion: false
      }
    }
  };
  var WORLD_ICONS = { all: "\u25C9", news: "\u{1F4F0}", sports: "\u26BD", entertainment: "\u{1F3AC}", positive: "\u2728" };
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
  var WORLD_DOMAIN_MAP = {
    news: "news",
    sports: "sports",
    entertainment: "entertainment",
    positive: "positive"
  };
  var _DOMAIN_HIGHLIGHT_COLORS = {
    dark: { news: "#58a6ff", sports: "#3fb950", entertainment: "#bc8cff", positive: "#f5a623" },
    light: { news: "#0969da", sports: "#1a7f37", entertainment: "#8250df", positive: "#bf8700" }
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
  function startNetworkAnimation() {
    const canvas = document.getElementById("info-panel-bg-canvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const isLight = document.body.classList.contains("light-mode");
    const panel = document.getElementById("info-panel");
    const resize = () => {
      canvas.width = panel.offsetWidth;
      canvas.height = panel.offsetHeight;
    };
    resize();
    window.addEventListener("resize", resize);
    canvas._resizeHandler = resize;
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
      ctx.strokeStyle = isLight ? `rgba(52, 152, 219, ${mstAlpha})` : `rgba(52, 152, 219, ${mstAlpha})`;
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
            ctx.strokeStyle = isLight ? `rgba(52, 152, 219, ${alpha})` : `rgba(52, 152, 219, ${alpha})`;
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
  function stopNetworkAnimation() {
    if (state.networkAnimId) {
      cancelAnimationFrame(state.networkAnimId);
      state.networkAnimId = null;
    }
    const canvas = document.getElementById("info-panel-bg-canvas");
    if (canvas) {
      if (canvas._resizeHandler) {
        window.removeEventListener("resize", canvas._resizeHandler);
        canvas._resizeHandler = null;
      }
      const ctx = canvas.getContext("2d");
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
  }
  function startSpaceAnimation() {
    const canvas = document.getElementById("info-panel-bg-canvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const isLight = document.body.classList.contains("light-mode");
    const panel = document.getElementById("info-panel");
    const resize = () => {
      canvas.width = panel.offsetWidth;
      canvas.height = panel.offsetHeight;
    };
    resize();
    window.addEventListener("resize", resize);
    canvas._resizeHandler = resize;
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
  function stopSpaceAnimation() {
    if (state.spaceAnimId) {
      cancelAnimationFrame(state.spaceAnimId);
      state.spaceAnimId = null;
    }
    const canvas = document.getElementById("info-panel-bg-canvas");
    if (canvas) {
      if (canvas._resizeHandler) {
        window.removeEventListener("resize", canvas._resizeHandler);
        canvas._resizeHandler = null;
      }
      const ctx = canvas.getContext("2d");
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
  }

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
    const activeBtn = document.querySelector(".world-btn.active");
    const nameEl = document.getElementById("mobile-world-name");
    const dotEl = document.querySelector(".mobile-bar-world-dot");
    if (activeBtn && nameEl) {
      const world = state.allWorlds[activeBtn.dataset.world];
      nameEl.textContent = world ? world.label : activeBtn.textContent;
    }
    if (dotEl && activeBtn) {
      const colors = { news: "#1f6feb", sports: "#2ea043", entertainment: "#a371f7", positive: "#f0883e" };
      const worldId = activeBtn.dataset.world || "news";
      dotEl.style.background = colors[worldId] || "#1f6feb";
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
    const refreshBtn = document.getElementById("mobile-refresh-btn");
    mobileBar.addEventListener("click", (e) => {
      if (dragOccurred) {
        dragOccurred = false;
        return;
      }
      if (e.target === menuBtn || menuBtn.contains(e.target)) return;
      if (e.target === refreshBtn || refreshBtn.contains(e.target)) return;
      toggleSheet();
    });
    menuBtn.addEventListener("click", toggleSheet);
    refreshBtn.addEventListener("click", () => {
      refreshBtn.classList.add("spinning");
      setTimeout(() => location.reload(), 300);
    });
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
    const mCtrlToggle = document.getElementById("mobile-ctrl-toggle");
    const mCtrlTray = document.getElementById("mobile-ctrl-tray");
    const mGlobe = document.getElementById("mobile-globe-btn");
    const mLabels = document.getElementById("mobile-labels-btn");
    const mSpin = document.getElementById("mobile-spin-btn");
    const mReload = document.getElementById("mobile-reload-btn");
    if (mCtrlToggle) mCtrlToggle.addEventListener("click", () => {
      mCtrlTray.classList.toggle("open");
    });
    if (mGlobe) mGlobe.addEventListener("click", toggleGlobe);
    if (mLabels) mLabels.addEventListener("click", toggleMapLabels);
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
      const cat = f.properties.category || "general";
      entry.categories[cat] = (entry.categories[cat] || 0) + 1;
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
        "circle-color": [
          "match",
          ["get", "category"],
          "violence",
          DOMAIN_COLORS.violence,
          "human",
          DOMAIN_COLORS.human,
          "power",
          DOMAIN_COLORS.power,
          "economy",
          DOMAIN_COLORS.economy,
          "planet",
          DOMAIN_COLORS.planet,
          "health",
          DOMAIN_COLORS.health,
          "tech",
          DOMAIN_COLORS.tech,
          "culture",
          DOMAIN_COLORS.culture,
          "uplifting",
          DOMAIN_COLORS.uplifting,
          "#484f58"
        ],
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
  function _getWorldDomain(worldId) {
    return WORLD_DOMAIN_MAP[worldId] || null;
  }
  function computeFilteredState() {
    const searchText = (document.getElementById("search-box").value || "").trim().toLowerCase();
    const timeHours = parseInt(document.getElementById("filter-time").value) || 0;
    const hideOpinion = document.getElementById("filter-opinion")?.checked || false;
    const now = Date.now();
    const originFiltering = state.activeOrigins.size < 2;
    const hasFilters = state.activeConcepts.size > 0 || state.excludedConcepts.size > 0 || state.activeSources.size > 0 || state.excludedSources.size > 0 || originFiltering || state.brightSideMode || searchText || timeHours || hideOpinion;
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
    const contentFiltering = state.activeConcepts.size > 0 || state.excludedConcepts.size > 0 || state.activeSources.size > 0 || state.excludedSources.size > 0 || originFiltering || state.brightSideMode || searchText;
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
    const worldDomain = _getWorldDomain(state.activeWorldId);
    if (worldDomain) {
      narratives = narratives.filter((n) => (n.domain || "news") === worldDomain);
    }
    if (state.brightSideMode && !worldDomain) {
      narratives = narratives.filter((n) => (n.bright_side_count || 0) > 0);
    }
    if (searchText) {
      const searchTerms = searchText.split(/\s+/).filter((t) => t.length > 0);
      narratives = narratives.filter((n) => {
        const haystack = `${n.title || ""} ${n.description || ""} ${(n.theme_tags || []).join(" ")}`.toLowerCase();
        return searchTerms.every((term) => haystack.includes(term));
      });
    }
    if (contentFiltering && storyIds && !worldDomain) {
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
  function _markVisited(url) {
    if (!url || state._visitedStories.has(url)) return;
    state._visitedStories.add(url);
    if (state._visitedStories.size > _VISITED_MAX) {
      const arr = [...state._visitedStories];
      state._visitedStories = new Set(arr.slice(arr.length - _VISITED_MAX));
    }
    localStorage.setItem(_VISITED_KEY, JSON.stringify([...state._visitedStories]));
  }
  function initMap() {
    state.map = new maplibregl.Map({
      container: "map",
      style: state.lightMode ? "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json" : "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
      center: [20, 30],
      zoom: 1.5,
      minZoom: 0,
      maxZoom: 18
    });
    state.map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    state.map.on("style.load", () => {
      state.map.setProjection({ type: state.currentProjection });
    });
    const _prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let _autoRotate = !_prefersReducedMotion;
    let _rotateId = null;
    function startAutoRotate() {
      if (_rotateId || !_autoRotate) return;
      _rotateId = setInterval(() => {
        if (!_autoRotate || state.currentProjection !== "globe") {
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
  function setLoadingStep(text) {
    const el = document.getElementById("loading-step");
    if (el) el.textContent = text;
  }
  function hideLoadingOverlay() {
    const overlay = document.getElementById("loading-overlay");
    if (!overlay) return;
    overlay.classList.add("hidden");
    setTimeout(() => overlay.remove(), 600);
  }
  async function onMapLoad() {
    addMapLayers(state.map, "");
    addMapInteractions(state.map, "");
    setMapLabelsVisible(false);
    setLoadingStep("Loading stories...");
    const storiesP = loadAll();
    const conceptsP = loadConcepts();
    const sourcesP = loadSources();
    const eventsP = loadEvents();
    const overviewP = loadWorldOverview();
    const narrativesP = loadNarratives();
    await storiesP.catch(() => {
    });
    let storyCount = state.geojsonData.features ? state.geojsonData.features.length : 0;
    if (storyCount === 0) {
      setLoadingStep("Retrying...");
      await new Promise((r) => setTimeout(r, 2e3));
      await loadAll().catch(() => {
      });
      storyCount = state.geojsonData.features ? state.geojsonData.features.length : 0;
    }
    setLoadingStep(storyCount > 0 ? `${storyCount.toLocaleString()} stories loaded` : "Could not load stories \u2014 try refreshing");
    await Promise.allSettled([conceptsP, sourcesP, eventsP, overviewP, narrativesP]);
    hideLoadingOverlay();
    if (state._pendingMapView && state.map) {
      state.map.jumpTo({ center: [state._pendingMapView.lon, state._pendingMapView.lat], zoom: state._pendingMapView.zoom });
      state._pendingMapView = null;
    }
    showOnboardingHint();
    if (_isMobile() && !localStorage.getItem("thisminute-onboarded")) {
      setTimeout(() => {
        setSheetState("half");
        setTimeout(() => setSheetState("closed"), 1500);
      }, 2e3);
    }
  }
  function showOnboardingHint() {
    if (localStorage.getItem("thisminute-onboarded")) return;
    const hint = document.createElement("div");
    hint.id = "onboarding-hint";
    hint.innerHTML = _isMobile() ? "Tap a situation to explore &middot; Swipe to browse &middot; Try different worlds above" : "Click a situation to explore &middot; Use <kbd>j</kbd>/<kbd>k</kbd> to navigate &middot; <kbd>?</kbd> for shortcuts";
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
      const titleHtml = _highlightText(escapeHtml(p.title), searchQ);
      const summaryHtml = _highlightText(rawSummary, searchQ);
      const [lon, lat] = f.geometry.coordinates;
      const img = p.image_url ? `<img class="info-card-img" src="${escapeHtml(p.image_url)}" loading="lazy" alt="" onload="this.classList.add('loaded')" onerror="this.remove()">` : "";
      const favicon = _getFavicon(p.url);
      const visited = state._visitedStories.has(p.url) ? " visited" : "";
      return `<div class="info-card${img ? " has-image" : ""}${visited}" data-story-id="${p.story_id || p.id}" data-lon="${lon}" data-lat="${lat}">
                ${img}
                <div class="info-card-body">
                    <div class="info-card-title">${titleHtml}</div>
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
          markWorldModified();
          return;
        }
        if (e.target.classList.contains("story-source") && e.target.dataset.source) {
          e.stopPropagation();
          state.activeSources.clear();
          state.activeSources.add(e.target.dataset.source);
          applyFilters();
          markWorldModified();
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
        navigator.clipboard.writeText(btn.dataset.url).then(() => {
          btn.textContent = "\u2713";
          setTimeout(() => {
            btn.innerHTML = "&#128279;";
          }, 1500);
        }).catch(() => {
        });
      });
    });
    panelStories.querySelectorAll(".info-card-feedback").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        openFeedbackDialog({ type: btn.dataset.fbType, id: parseInt(btn.dataset.fbId), title: btn.dataset.fbTitle });
      });
    });
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
        state.map.easeTo({ padding: { right: 370 }, duration: 300 });
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
      state.map.easeTo({ padding: { right: 370 }, duration: 300 });
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
      state.map.easeTo({ padding: { right: 0 }, duration: 300 });
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
      updateWorldOverviewFilterState(filtered.hasFilters);
      renderActiveFilterPills();
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
        markWorldModified();
      });
    });
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
  async function fetchStories(since) {
    const params = new URLSearchParams();
    if (since) params.set("since", since);
    const resp = await fetch(`/api/stories?${params.toString()}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return await resp.json();
  }
  async function loadAll() {
    try {
      const data = await fetchStories();
      state.geojsonData = data;
      state.lastFetchTime = (/* @__PURE__ */ new Date()).toISOString();
      state._lastDataUpdate = Date.now();
      fetchCloudData();
      updateStats();
      applyFilters();
    } catch (err) {
      console.error("Failed to load stories:", err);
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
      if (state._pendingWorldId) {
        const pending = state.allWorlds[state._pendingWorldId];
        if (pending && pending.keywords && pending.keywords.length > 0) {
          const matched = _matchingConcepts(pending.keywords);
          matched.forEach((c) => state.activeConcepts.add(c));
          applyFilters();
        }
        state._pendingWorldId = null;
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
    markWorldModified();
    updateFilterDrawerToggle();
    applyFilters();
  }
  function toggleExclude(name) {
    state.activeConcepts.delete(name);
    if (state.excludedConcepts.has(name)) state.excludedConcepts.delete(name);
    else state.excludedConcepts.add(name);
    markWorldModified();
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
    const defaultWorldId = localStorage.getItem("tm_default_world");
    const fallback = defaultWorldId && state.allWorlds[defaultWorldId] ? defaultWorldId : "all";
    switchWorld(fallback);
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
    markWorldModified();
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
    markWorldModified();
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
    const originFilterCount = state.activeOrigins.size < 2 ? 1 : 0;
    const activeCount = state.activeConcepts.size + state.excludedConcepts.size + originFilterCount;
    btn.classList.toggle("has-active", activeCount > 0);
    btn.textContent = activeCount > 0 ? `Refine (${activeCount})` : "Refine";
  }
  function updateSourcesIndicator() {
    const el = document.getElementById("stat-sources");
    const hasFilter = state.activeSources.size > 0 || state.excludedSources.size > 0;
    el.classList.toggle("has-source-filter", hasFilter);
  }
  function toggleWorldOverview() {
    const bar = document.getElementById("world-overview-bar");
    bar.classList.toggle("expanded");
  }
  function updateWorldOverviewFilterState(hasFilters) {
    const bar = document.getElementById("world-overview-bar");
    bar.classList.toggle("has-filters", !!hasFilters);
  }
  state._pendingWorldId = null;
  var _editingWorldId = null;
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
  function _getRemovedWorlds() {
    try {
      return JSON.parse(localStorage.getItem("tm_removed_worlds") || "[]");
    } catch (e) {
      return [];
    }
  }
  var ALL_WORLD = {
    label: "All",
    color: "#8b949e",
    builtIn: true,
    permanent: true,
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
    }
  };
  function loadWorlds() {
    const removed = _getRemovedWorlds();
    state.allWorlds = { all: ALL_WORLD };
    for (const [id, preset] of Object.entries(WORLD_PRESETS)) {
      if (!removed.includes(id)) state.allWorlds[id] = preset;
    }
    try {
      const saved = JSON.parse(localStorage.getItem("tm_worlds") || "{}");
      for (const [id, world] of Object.entries(saved)) {
        if (!WORLD_PRESETS[id]) {
          state.allWorlds[id] = world;
        }
      }
    } catch (e) {
      console.error("Failed to load saved worlds:", e);
    }
    loadWorldPrefs();
    const defaultWorldId = localStorage.getItem("tm_default_world");
    if (defaultWorldId && state.allWorlds[defaultWorldId]) {
      state.activeWorldId = defaultWorldId;
    }
  }
  function saveWorlds() {
    const custom = {};
    for (const [id, world] of Object.entries(state.allWorlds)) {
      if (!world.builtIn) custom[id] = world;
    }
    try {
      localStorage.setItem("tm_worlds", JSON.stringify(custom));
    } catch (e) {
      console.error("Failed to save worlds:", e);
    }
  }
  function loadWorldPrefs() {
    try {
      state.worldPrefs = JSON.parse(localStorage.getItem("tm_world_prefs") || "{}");
    } catch (e) {
      state.worldPrefs = {};
    }
    let order = 0;
    for (const id of Object.keys(state.allWorlds)) {
      if (!state.worldPrefs[id]) {
        state.worldPrefs[id] = { visible: true, order };
      }
      if (state.worldPrefs[id].order == null) state.worldPrefs[id].order = order;
      order++;
    }
    for (const id of Object.keys(state.worldPrefs)) {
      if (!state.allWorlds[id]) delete state.worldPrefs[id];
    }
    saveWorldPrefs();
  }
  function saveWorldPrefs() {
    try {
      localStorage.setItem("tm_world_prefs", JSON.stringify(state.worldPrefs));
    } catch (e) {
      console.error("Failed to save world prefs:", e);
    }
  }
  function _getVisibleWorldEntries() {
    return Object.entries(state.allWorlds).filter(([id]) => state.worldPrefs[id]?.visible !== false).sort((a, b) => (state.worldPrefs[a[0]]?.order ?? 99) - (state.worldPrefs[b[0]]?.order ?? 99));
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
      searchText: document.getElementById("search-box").value.trim(),
      timeHours: document.getElementById("filter-time").value,
      hideOpinion: document.getElementById("filter-opinion")?.checked || false
    };
  }
  function applyWorldConfig(config, keywords, feedTags) {
    state.activeConcepts.clear();
    state.excludedConcepts.clear();
    state.activeSources.clear();
    state.excludedSources.clear();
    state.brightSideMode = false;
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
    state.activeOrigins = new Set(config.activeOrigins || ["rss", "gdelt"]);
    state.brightSideMode = !!config.brightSideMode;
    document.querySelectorAll(".origin-btn").forEach((btn) => {
      btn.classList.toggle("active", state.activeOrigins.has(btn.dataset.origin));
    });
    updateFilterDrawerToggle();
    updateSourcesIndicator();
  }
  async function switchWorld(worldId) {
    const world = state.allWorlds[worldId];
    if (!world) return;
    if (state.activeWorldId === worldId && !state.worldModified) return;
    if (world.feedTags && world.feedTags.length > 0 && state._feedTagsReady) {
      await state._feedTagsReady;
    }
    if (state.activeNarrativeId) {
      const newDomain = WORLD_DOMAIN_MAP[worldId];
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
    const effectiveConfig = world.builtIn && state.worldPrefs[worldId]?.configOverride || world.config;
    applyWorldConfig(effectiveConfig, world.keywords, world.feedTags);
    state.activeWorldId = worldId;
    state.worldModified = false;
    updateWorldsBar();
    renderWorldOverview();
    applyFilters();
  }
  function markWorldModified() {
    if (!state.activeWorldId) return;
    state.worldModified = true;
    updateWorldsBar();
  }
  function updateWorldConfig(worldId) {
    const world = state.allWorlds[worldId];
    if (!world) return;
    const config = captureCurrentConfig();
    if (world.builtIn) {
      if (!state.worldPrefs[worldId]) state.worldPrefs[worldId] = { visible: true, order: 0 };
      state.worldPrefs[worldId].configOverride = config;
      saveWorldPrefs();
    } else {
      world.config = config;
      saveWorlds();
    }
    state.worldModified = false;
    updateWorldsBar();
  }
  function resetWorldConfig(worldId) {
    const pref = state.worldPrefs[worldId];
    if (pref?.configOverride) {
      delete pref.configOverride;
      saveWorldPrefs();
      switchWorld(worldId);
    }
  }
  function generatePresetURL(worldId) {
    const world = state.allWorlds[worldId];
    if (!world) return window.location.href;
    const base = window.location.origin + window.location.pathname;
    if (world.builtIn) {
      const pref = state.worldPrefs[worldId];
      if (pref?.configOverride) {
        return base + "#" + _configToParams(pref.configOverride).toString();
      }
      return base + "#world=" + worldId;
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
    if (config.activeOrigins?.length && (config.activeOrigins.length < 2 || !config.activeOrigins.includes("rss") || !config.activeOrigins.includes("gdelt"))) {
      params.set("origin", config.activeOrigins.join(","));
    }
    if (config.brightSideMode) params.set("bs", "1");
    if (config.searchText) params.set("q", config.searchText);
    if (config.timeHours) params.set("t", config.timeHours);
    if (config.hideOpinion) params.set("op", "0");
    return params;
  }
  function updateWorldsBarOverflow() {
    const wrapper = document.querySelector(".worlds-bar-wrapper");
    const bar = document.getElementById("worlds-bar");
    if (!wrapper || !bar) return;
    const sl = bar.scrollLeft;
    const sw = bar.scrollWidth;
    const cw = bar.clientWidth;
    wrapper.classList.toggle("scroll-left", sl > 4);
    wrapper.classList.toggle("scroll-right", sl + cw < sw - 4);
  }
  function updateWorldsBar() {
    const domainCounts = {};
    for (const n of state.narrativesData || []) {
      const d = n.domain || "news";
      domainCounts[d] = (domainCounts[d] || 0) + 1;
    }
    const visibleEntries = _getVisibleWorldEntries();
    const displayMode = visibleEntries.length <= 2 ? "text" : "icon";
    document.querySelectorAll(".world-btn").forEach((btn) => {
      const worldId = btn.dataset.world;
      const world = state.allWorlds[worldId];
      const isActive = worldId === state.activeWorldId;
      btn.classList.toggle("active", isActive);
      btn.classList.toggle("modified", isActive && state.worldModified);
      btn.classList.toggle("world-btn-text-mode", displayMode === "text");
      if (isActive && world && !world.builtIn) {
        btn.style.setProperty("--custom-world-color", world.color);
        btn.classList.add("custom-color");
      } else {
        btn.style.removeProperty("--custom-world-color");
        btn.classList.remove("custom-color");
      }
      const domain = WORLD_DOMAIN_MAP[worldId];
      const count = domain ? domainCounts[domain] || 0 : 0;
      const label = world?.label || worldId;
      const icon = WORLD_ICONS[worldId] || state.worldPrefs[worldId]?.icon;
      if (displayMode === "text") {
        if (count > 0) {
          btn.innerHTML = `${escapeHtml(label)} <span class="world-btn-count">${count}</span>`;
        } else {
          btn.textContent = label;
        }
        btn.title = label;
      } else if (icon) {
        if (count > 0) {
          btn.innerHTML = `${icon} <span class="world-btn-count">${count}</span>`;
        } else {
          btn.textContent = icon;
        }
        btn.title = label;
      } else {
        const abbrev = _getAbbreviation(label);
        if (count > 0) {
          btn.innerHTML = `${escapeHtml(abbrev)} <span class="world-btn-count">${count}</span>`;
        } else {
          btn.textContent = abbrev;
        }
        btn.title = label;
        btn.classList.add("world-btn-abbrev");
      }
    });
  }
  function saveCurrentAsWorld(name) {
    const id = "custom_" + Date.now();
    const config = captureCurrentConfig();
    const world = {
      label: name,
      color: _autoPickColor(id),
      builtIn: false,
      config
    };
    state.allWorlds[id] = world;
    const maxOrder = Math.max(0, ...Object.values(state.worldPrefs).map((p) => p.order ?? 0));
    state.worldPrefs[id] = {
      visible: true,
      order: maxOrder + 1,
      icon: _autoDetectIcon(name, world)
    };
    saveWorlds();
    saveWorldPrefs();
    state.activeWorldId = id;
    state.worldModified = false;
    renderWorldsBar();
    saveStateToURL();
  }
  function deleteWorld(worldId) {
    const world = state.allWorlds[worldId];
    if (!world || world.permanent) return;
    if (world.builtIn) {
      const removed = _getRemovedWorlds();
      if (!removed.includes(worldId)) removed.push(worldId);
      localStorage.setItem("tm_removed_worlds", JSON.stringify(removed));
    }
    delete state.allWorlds[worldId];
    delete state.worldPrefs[worldId];
    saveWorlds();
    saveWorldPrefs();
    if (localStorage.getItem("tm_default_world") === worldId) {
      localStorage.removeItem("tm_default_world");
    }
    renderWorldsBar();
    if (state.activeWorldId === worldId) {
      switchWorld("all");
    }
  }
  function renderWorldsBar() {
    const bar = document.getElementById("worlds-bar");
    const moreBtn = document.getElementById("worlds-more-btn");
    bar.querySelectorAll(".world-btn").forEach((b) => b.remove());
    const visibleEntries = _getVisibleWorldEntries();
    const displayMode = visibleEntries.length <= 2 ? "text" : "icon";
    for (const [id, world] of visibleEntries) {
      const btn = document.createElement("button");
      btn.className = "world-btn";
      if (displayMode === "text") btn.classList.add("world-btn-text-mode");
      btn.dataset.world = id;
      btn.dataset.color = world.color;
      const icon = WORLD_ICONS[id] || state.worldPrefs[id]?.icon;
      if (displayMode === "text") {
        btn.textContent = world.label;
        btn.title = world.label;
      } else if (icon) {
        btn.textContent = icon;
        btn.title = world.label;
      } else {
        btn.textContent = _getAbbreviation(world.label);
        btn.title = world.label;
        btn.classList.add("world-btn-abbrev");
      }
      btn.addEventListener("click", () => switchWorld(id));
      bar.insertBefore(btn, moreBtn);
    }
    updateWorldsBar();
    updateWorldsBarOverflow();
  }
  function toggleWorldsPanel() {
    const panel = document.getElementById("worlds-panel");
    panel.classList.toggle("visible");
    if (panel.classList.contains("visible")) {
      renderWorldsPanelContents();
    }
  }
  function closeWorldsPanel() {
    document.getElementById("worlds-panel").classList.remove("visible");
  }
  function renderWorldsPanelContents() {
    const listContainer = document.getElementById("worlds-panel-list");
    listContainer.innerHTML = "";
    const sorted = Object.entries(state.allWorlds).sort((a, b) => (state.worldPrefs[a[0]]?.order ?? 99) - (state.worldPrefs[b[0]]?.order ?? 99));
    let lastBuiltIn = -1;
    sorted.forEach(([_, w], i) => {
      if (w.builtIn) lastBuiltIn = i;
    });
    const defaultWorldId = localStorage.getItem("tm_default_world");
    sorted.forEach(([id, world], idx) => {
      const pref = state.worldPrefs[id] || {};
      const isVisible = pref.visible !== false;
      const isActive = id === state.activeWorldId;
      const isDefault = id === defaultWorldId;
      const hasOverride = world.builtIn && !!pref.configOverride;
      const item = document.createElement("div");
      item.className = "world-panel-item" + (isActive ? " active-world" : "") + (!isVisible ? " hidden-world" : "");
      const eye = document.createElement("button");
      eye.className = "world-panel-eye";
      eye.innerHTML = isVisible ? "&#x1F441;" : "&#x1F441;&#x200D;&#x1F5E8;";
      eye.title = isVisible ? "Hide from bar" : "Show in bar";
      eye.style.opacity = isVisible ? "0.7" : "0.3";
      eye.addEventListener("click", (e) => {
        e.stopPropagation();
        if (!state.worldPrefs[id]) state.worldPrefs[id] = { visible: true, order: idx };
        state.worldPrefs[id].visible = !isVisible;
        saveWorldPrefs();
        renderWorldsBar();
        renderWorldsPanelContents();
      });
      item.appendChild(eye);
      const dot = document.createElement("span");
      dot.className = "world-panel-color";
      dot.style.background = world.color;
      item.appendChild(dot);
      const icon = WORLD_ICONS[id] || pref.icon;
      const info = document.createElement("div");
      info.className = "world-panel-info";
      const labelEl = document.createElement("span");
      labelEl.className = "world-panel-label";
      labelEl.textContent = (icon ? icon + " " : "") + world.label;
      info.appendChild(labelEl);
      const desc = document.createElement("span");
      desc.className = "world-panel-desc";
      const effectiveConfig = world.builtIn && pref.configOverride || world.config;
      desc.textContent = _describeConfig(effectiveConfig, world.feedTags);
      info.appendChild(desc);
      if (isActive && state.worldModified) {
        const updateBtn = document.createElement("button");
        updateBtn.className = "world-panel-update";
        updateBtn.textContent = "Update";
        updateBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          updateWorldConfig(id);
          renderWorldsPanelContents();
        });
        info.appendChild(updateBtn);
      }
      if (hasOverride) {
        const resetBtn = document.createElement("button");
        resetBtn.className = "world-panel-reset";
        resetBtn.textContent = "Reset";
        resetBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          resetWorldConfig(id);
          renderWorldsPanelContents();
        });
        info.appendChild(resetBtn);
      }
      item.appendChild(info);
      const star = document.createElement("button");
      star.className = "world-panel-star" + (isDefault ? " active" : "");
      star.innerHTML = isDefault ? "&#x2605;" : "&#x2606;";
      star.title = isDefault ? "Remove as default" : "Set as default";
      star.addEventListener("click", (e) => {
        e.stopPropagation();
        if (isDefault) {
          localStorage.removeItem("tm_default_world");
        } else {
          localStorage.setItem("tm_default_world", id);
        }
        renderWorldsPanelContents();
      });
      item.appendChild(star);
      const share = document.createElement("button");
      share.className = "world-panel-share";
      share.innerHTML = "&#x1F517;";
      share.title = "Copy link";
      share.addEventListener("click", (e) => {
        e.stopPropagation();
        const url = generatePresetURL(id);
        navigator.clipboard.writeText(url).then(() => {
          share.textContent = "\u2713";
          setTimeout(() => {
            share.innerHTML = "&#x1F517;";
          }, 1200);
        }).catch(() => {
        });
      });
      item.appendChild(share);
      const arrows = document.createElement("span");
      arrows.className = "world-panel-arrows";
      const upBtn = document.createElement("button");
      upBtn.innerHTML = "&#x25B2;";
      upBtn.title = "Move up";
      upBtn.disabled = idx === 0;
      upBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        if (idx === 0) return;
        const prevId = sorted[idx - 1][0];
        const tmp = state.worldPrefs[id].order;
        state.worldPrefs[id].order = state.worldPrefs[prevId].order;
        state.worldPrefs[prevId].order = tmp;
        saveWorldPrefs();
        renderWorldsBar();
        renderWorldsPanelContents();
      });
      const downBtn = document.createElement("button");
      downBtn.innerHTML = "&#x25BC;";
      downBtn.title = "Move down";
      downBtn.disabled = idx === sorted.length - 1;
      downBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        if (idx === sorted.length - 1) return;
        const nextId = sorted[idx + 1][0];
        const tmp = state.worldPrefs[id].order;
        state.worldPrefs[id].order = state.worldPrefs[nextId].order;
        state.worldPrefs[nextId].order = tmp;
        saveWorldPrefs();
        renderWorldsBar();
        renderWorldsPanelContents();
      });
      arrows.appendChild(upBtn);
      arrows.appendChild(downBtn);
      item.appendChild(arrows);
      if (!world.builtIn) {
        const edit = document.createElement("button");
        edit.className = "world-panel-edit";
        edit.innerHTML = "&#x270E;";
        edit.title = "Rename";
        edit.addEventListener("click", (e) => {
          e.stopPropagation();
          showSaveWorldDialog(id);
        });
        item.appendChild(edit);
      }
      if (!world.permanent) {
        const del = document.createElement("button");
        del.className = "world-panel-delete";
        del.innerHTML = "&times;";
        del.addEventListener("click", (e) => {
          e.stopPropagation();
          deleteWorld(id);
          renderWorldsPanelContents();
        });
        item.appendChild(del);
      }
      item.addEventListener("click", () => {
        switchWorld(id);
        closeWorldsPanel();
      });
      listContainer.appendChild(item);
      if (idx === lastBuiltIn && lastBuiltIn < sorted.length - 1) {
        const sep = document.createElement("div");
        sep.className = "world-panel-separator";
        listContainer.appendChild(sep);
      }
    });
    const removed = _getRemovedWorlds();
    if (removed.length > 0) {
      const restore = document.createElement("button");
      restore.className = "world-panel-restore";
      restore.textContent = "Restore default presets";
      restore.addEventListener("click", (e) => {
        e.stopPropagation();
        localStorage.removeItem("tm_removed_worlds");
        loadWorlds();
        renderWorldsBar();
        renderWorldsPanelContents();
      });
      listContainer.appendChild(restore);
    }
  }
  function showSaveWorldDialog(editId) {
    closeWorldsPanel();
    _editingWorldId = editId || null;
    const dialog = document.getElementById("world-save-dialog");
    const input = document.getElementById("world-save-name");
    const heading = dialog.querySelector("h3");
    const confirmBtn = document.getElementById("world-save-confirm");
    if (_editingWorldId && state.allWorlds[_editingWorldId]) {
      heading.textContent = "Rename Preset";
      input.value = state.allWorlds[_editingWorldId].label;
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
  function closeSaveWorldDialog() {
    _editingWorldId = null;
    document.getElementById("world-save-dialog").classList.remove("visible");
  }
  function confirmSaveWorld() {
    const input = document.getElementById("world-save-name");
    const name = input.value.trim();
    if (!name) return;
    const nameLower = name.toLowerCase();
    const isDuplicate = Object.entries(state.allWorlds).some(
      ([wid, w]) => w.label.toLowerCase() === nameLower && wid !== _editingWorldId
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
    if (_editingWorldId && state.allWorlds[_editingWorldId]) {
      const world = state.allWorlds[_editingWorldId];
      world.label = name;
      if (state.worldPrefs[_editingWorldId]) {
        state.worldPrefs[_editingWorldId].icon = _autoDetectIcon(name, world);
      }
      saveWorlds();
      saveWorldPrefs();
      renderWorldsBar();
    } else {
      saveCurrentAsWorld(name);
    }
    closeSaveWorldDialog();
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
    markWorldModified();
    updateFilterDrawerToggle();
    updateSourcesIndicator();
    applyFilters();
  }
  function toggleExcludeSource(name) {
    state.activeSources.delete(name);
    if (state.excludedSources.has(name)) state.excludedSources.delete(name);
    else state.excludedSources.add(name);
    markWorldModified();
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
    markWorldModified();
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
    markWorldModified();
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
      container.innerHTML = '<div class="loading">No stories match your filters<br><small style="color:#484f58">Try clearing some filters or switching worlds</small></div>';
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
    container.querySelectorAll(".event-item .feedback-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        openFeedbackDialog({ type: btn.dataset.fbType, id: parseInt(btn.dataset.fbId), title: btn.dataset.fbTitle });
      });
    });
    container.querySelectorAll(".event-item").forEach((item) => {
      item.addEventListener("click", (e) => {
        if (e.target.tagName === "A" || e.target.classList.contains("feedback-btn")) return;
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
      updateWorldsBar();
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
        const sitId = btn.dataset.sitId;
        const url = new URL(window.location.origin);
        url.searchParams.set("sit", sitId);
        navigator.clipboard.writeText(url.toString()).then(() => {
          btn.textContent = "\u2713";
          setTimeout(() => {
            btn.innerHTML = "&#128279;";
          }, 1500);
        }).catch(() => {
        });
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
    container.querySelectorAll(".situation-item .feedback-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        openFeedbackDialog({ type: btn.dataset.fbType, id: parseInt(btn.dataset.fbId), title: btn.dataset.fbTitle });
      });
    });
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
            features.push({ type: "Feature", geometry: f.geometry, properties: { category: f.properties.category, radius } });
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
        const cy = canvas.clientHeight * 0.33;
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
              proxFeatures.push({ type: "Feature", geometry: f.geometry, properties: { category: f.properties.category, radius } });
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
  async function loadWorldOverview() {
    try {
      const resp = await fetch("/api/world-overview");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      state.worldOverview = await resp.json();
      renderWorldOverview();
    } catch (err) {
      console.error("Failed to load world overview:", err);
    }
  }
  function renderWorldOverview() {
    const bar = document.getElementById("world-overview-bar");
    if (!state.worldOverview || !state.worldOverview.summary) {
      bar.classList.remove("visible");
      return;
    }
    const worldId = state.activeWorldId || "news";
    const domain = _getWorldDomain(worldId);
    if (domain && domain !== "news") {
      const domainNarrs = (state.narrativesData || []).filter((n) => (n.domain || "news") === domain);
      if (domainNarrs.length > 0) {
        const topNames = domainNarrs.slice(0, 3).map((n) => n.title).join(" \xB7 ");
        const extra = domainNarrs.length > 3 ? ` +${domainNarrs.length - 3} more` : "";
        bar.querySelector(".world-overview-text").textContent = topNames + extra;
      } else {
        bar.querySelector(".world-overview-text").textContent = "Situations will appear as stories accumulate";
      }
    } else {
      bar.querySelector(".world-overview-text").textContent = state.worldOverview.summary;
    }
    const label = bar.querySelector(".world-overview-label");
    if (label) {
      const worldColors = { news: "#58a6ff", sports: "#3fb950", entertainment: "#bc8cff", positive: "#f5a623" };
      label.style.color = worldColors[worldId] || "#58a6ff";
    }
    bar.classList.add("visible");
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
      applyFilters();
    });
  }
  function applyInitialTheme() {
    if (state.lightMode) document.body.classList.add("light-mode");
  }
  function saveStateToURL() {
    const params = new URLSearchParams();
    if (state.activeWorldId && state.activeWorldId !== "news") params.set("world", state.activeWorldId);
    const world = state.allWorlds[state.activeWorldId];
    const worldFeedTagSources = world && world.feedTags ? new Set(sourcesForTags(world.feedTags)) : null;
    if (state.activeConcepts.size > 0) params.set("in", [...state.activeConcepts].join(","));
    if (state.excludedConcepts.size > 0) params.set("ex", [...state.excludedConcepts].join(","));
    if (state.activeSources.size > 0) {
      if (!worldFeedTagSources || state.activeSources.size !== worldFeedTagSources.size || [...state.activeSources].some((s) => !worldFeedTagSources.has(s))) {
        params.set("src", [...state.activeSources].join(","));
      }
    }
    if (state.excludedSources.size > 0) params.set("xsrc", [...state.excludedSources].join(","));
    if (state.activeOrigins.size < 2) params.set("origin", [...state.activeOrigins].join(","));
    if (state.brightSideMode) params.set("bs", "1");
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
      const defaultWorldId = localStorage.getItem("tm_default_world");
      if (defaultWorldId && state.allWorlds[defaultWorldId] && defaultWorldId !== "news") {
        const w = state.allWorlds[defaultWorldId];
        if (w.feedTags && w.feedTags.length > 0) {
          applyWorldConfig(w.config);
          if (state._feedTagsReady) {
            state._feedTagsReady.then(() => {
              const effectiveConfig = w.builtIn && state.worldPrefs[defaultWorldId]?.configOverride || w.config;
              applyWorldConfig(effectiveConfig, w.keywords, w.feedTags);
              applyFilters();
            });
          }
        } else if (w.keywords && w.keywords.length > 0) {
          state._pendingWorldId = defaultWorldId;
          applyWorldConfig(w.config);
        } else {
          const effectiveConfig = w.builtIn && state.worldPrefs[defaultWorldId]?.configOverride || w.config;
          applyWorldConfig(effectiveConfig, w.keywords, w.feedTags);
        }
        updateWorldsBar();
      }
      return;
    }
    localStorage.setItem("tm_last_visit", Date.now().toString());
    const params = new URLSearchParams(hash);
    if (params.has("world")) {
      const worldId = params.get("world");
      if (state.allWorlds[worldId]) {
        const w = state.allWorlds[worldId];
        if (w.keywords && w.keywords.length > 0) {
          state._pendingWorldId = worldId;
          state.activeWorldId = worldId;
          applyWorldConfig(w.config);
          state.worldModified = false;
          updateWorldsBar();
        } else if (w.feedTags && w.feedTags.length > 0) {
          state.activeWorldId = worldId;
          applyWorldConfig(w.config);
          state.worldModified = false;
          updateWorldsBar();
          if (state._feedTagsReady) {
            state._feedTagsReady.then(() => {
              applyWorldConfig(w.config, w.keywords, w.feedTags);
              applyFilters();
            });
          }
        } else {
          applyWorldConfig(w.config, w.keywords, w.feedTags);
          state.activeWorldId = worldId;
          state.worldModified = false;
          updateWorldsBar();
        }
      }
    }
    if (params.has("in")) {
      params.get("in").split(",").forEach((c) => state.activeConcepts.add(c.trim()));
      if (params.has("world")) state.worldModified = true;
    }
    if (params.has("ex")) {
      params.get("ex").split(",").forEach((c) => state.excludedConcepts.add(c.trim()));
      if (params.has("world")) state.worldModified = true;
    }
    if (params.has("src")) {
      params.get("src").split(",").forEach((s) => state.activeSources.add(s.trim()));
      if (params.has("world")) state.worldModified = true;
    }
    if (params.has("xsrc")) {
      params.get("xsrc").split(",").forEach((s) => state.excludedSources.add(s.trim()));
      if (params.has("world")) state.worldModified = true;
    }
    if (params.has("origin")) {
      state.activeOrigins = new Set(params.get("origin").split(",").map((s) => s.trim()));
      document.querySelectorAll(".origin-btn").forEach((btn) => {
        btn.classList.toggle("active", state.activeOrigins.has(btn.dataset.origin));
      });
      if (params.has("world")) state.worldModified = true;
    }
    if (params.has("bs")) {
      state.brightSideMode = true;
      if (params.has("world")) state.worldModified = true;
    }
    if (params.has("q")) {
      document.getElementById("search-box").value = params.get("q");
      if (params.has("world")) state.worldModified = true;
    }
    if (params.has("t")) {
      document.getElementById("filter-time").value = params.get("t");
      if (params.has("world")) state.worldModified = true;
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
    if (state.worldModified) updateWorldsBar();
  }
  document.addEventListener("DOMContentLoaded", async () => {
    applyInitialTheme();
    initMobileSheet();
    initInfoPanelSwipe(closeInfoPanel);
    loadFeedTags();
    loadWorlds();
    renderWorldsBar();
    loadStateFromURL();
    setLoadingStep("Loading state.map...");
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
        markWorldModified();
        updateFilterDrawerToggle();
        applyFilters();
      });
    });
    document.getElementById("btn-topics-all").addEventListener("click", () => setAllTopics("all"));
    document.getElementById("btn-topics-none").addEventListener("click", () => setAllTopics("none"));
    document.getElementById("world-overview-bar").addEventListener("click", toggleWorldOverview);
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
        markWorldModified();
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
    document.addEventListener("click", (e) => {
      const tag = e.target.closest(".story-concept-tag.clickable");
      if (!tag || !tag.dataset.concept) return;
      e.stopPropagation();
      state.activeConcepts.clear();
      state.activeConcepts.add(tag.dataset.concept);
      applyFilters();
      markWorldModified();
    });
    document.getElementById("theme-toggle").addEventListener("click", toggleTheme);
    document.getElementById("share-view-btn").addEventListener("click", () => {
      const btn = document.getElementById("share-view-btn");
      navigator.clipboard.writeText(window.location.href).then(() => {
        btn.textContent = "\u2713";
        btn.classList.add("copied");
        setTimeout(() => {
          btn.innerHTML = "&#128279;";
          btn.classList.remove("copied");
        }, 1500);
      }).catch(() => {
      });
    });
    document.getElementById("menu-btn").addEventListener("click", (e) => {
      e.stopPropagation();
      document.getElementById("main-menu").classList.toggle("visible");
    });
    document.getElementById("menu-shortcuts").addEventListener("click", () => {
      document.getElementById("main-menu").classList.remove("visible");
      document.getElementById("shortcuts-overlay").classList.add("visible");
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
    document.getElementById("worlds-bar").addEventListener("scroll", updateWorldsBarOverflow);
    document.getElementById("worlds-more-btn").addEventListener("click", toggleWorldsPanel);
    document.getElementById("worlds-panel-close").addEventListener("click", closeWorldsPanel);
    document.getElementById("worlds-save-btn").addEventListener("click", () => showSaveWorldDialog());
    document.getElementById("world-save-cancel").addEventListener("click", closeSaveWorldDialog);
    document.getElementById("world-save-confirm").addEventListener("click", confirmSaveWorld);
    document.getElementById("world-save-name").addEventListener("keydown", (e) => {
      if (e.key === "Enter") confirmSaveWorld();
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
      const panel = document.getElementById("worlds-panel");
      if (!panel.classList.contains("visible")) return;
      const moreBtn = document.getElementById("worlds-more-btn");
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
        const mainMenu = document.getElementById("main-menu");
        if (mainMenu.classList.contains("visible")) {
          mainMenu.classList.remove("visible");
          return;
        }
        const feedbackDialog = document.getElementById("feedback-dialog");
        if (feedbackDialog.classList.contains("visible")) {
          closeFeedbackDialog();
          return;
        }
        const worldsPanel = document.getElementById("worlds-panel");
        if (worldsPanel.classList.contains("visible")) {
          worldsPanel.classList.remove("visible");
          return;
        }
        const saveDialog = document.getElementById("world-save-dialog");
        if (saveDialog.classList.contains("visible")) {
          closeSaveWorldDialog();
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
          const visibleIds = _getVisibleWorldEntries().map(([id]) => id);
          if (visibleIds.length === 0) return;
          const currentIdx = visibleIds.indexOf(state.activeWorldId);
          const nextIdx = (currentIdx + 1) % visibleIds.length;
          switchWorld(visibleIds[nextIdx]);
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
    if (!state.activeWorldId) switchWorld("news");
    setInterval(loadEvents, EVENTS_INTERVAL);
    setInterval(loadWorldOverview, EVENTS_INTERVAL);
    setInterval(loadNarratives, NARRATIVES_INTERVAL);
    setInterval(pollUpdates, POLL_INTERVAL);
    setInterval(updateFreshnessIndicator, 1e4);
    setInterval(() => {
      document.querySelectorAll("[data-time]").forEach((el) => {
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
          context: { world: state.activeWorldId },
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
})();
