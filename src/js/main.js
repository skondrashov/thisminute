import { state, _markPopupDismiss, DOMAIN_COLORS, _hexToRGB, _rgbToHex, _domainRGB, _fallbackRGB, _BLEND_BASE_DARK, _BLEND_BASE_LIGHT, _featureDomain, _HEAT_STOPS, _heatColor, _blendLocationColors, COUNTRY_NAME_MAP, POLL_INTERVAL, EVENTS_INTERVAL, NARRATIVES_INTERVAL, BRIGHT_SIDE_MIN_SCORE, CURIOUS_MIN_SCORE, _VETO_TOPICS, _hasVetoTopic, _VISITED_KEY, _VISITED_MAX, TOPIC_DOMAIN_RULES, WORLD_PRESETS, PRESET_ALIASES, _resolvePresetAlias, PRESET_ICONS, NAME_EMOJI_MAP, CUSTOM_COLOR_PALETTE, PRESET_DOMAIN_MAP, _STORIES_DEFAULT_PRESETS, _getPresetDefaultView, _DOMAINLESS_HIDE_SITUATIONS, _DOMAIN_HIGHLIGHT_COLORS } from './state.js';
import { escapeHtml, truncateRaw, _fetchJson, _copyToClipboard, _clipboardFallback, _wireFeedbackButtons, formatTime, formatFullTime, _highlightText, _getFavicon } from './utils.js';
import { startNetworkAnimation, stopNetworkAnimation, startSpaceAnimation, stopSpaceAnimation } from './animations.js';
import { _isMobile, setPaneHeight, setSheetState, toggleSheet, updateMobileBar, initMobileSheet, initMobileMapControls, initInfoPanelSwipe } from './mobile.js';
import { _showHoverHighlight, _clearHoverHighlight } from './map-highlight.js';
import { updateEventMapLabels, updateCountryPolygons, addMapLayers } from './map-labels.js';
import { showNewBadge, triggerPulse, _animateCount } from './stats.js';
import { computeFilteredState, _getPresetDomain } from './store.js';

state.lightMode = localStorage.getItem("thisminute-theme") === "light";
/* Theme selector hidden — force domain theme, clear any stale preference */
localStorage.removeItem("tm_dot_theme");
state.dotColorTheme = "domain";
export function _markVisited(url) {
  if (!url || state._visitedStories.has(url)) return;
  state._visitedStories.add(url);
  if (state._visitedStories.size > _VISITED_MAX) {
    const arr = [...state._visitedStories];
    state._visitedStories = new Set(arr.slice(arr.length - _VISITED_MAX));
  }
  localStorage.setItem(_VISITED_KEY, JSON.stringify([...state._visitedStories]));
}
export var _introSpinActive = false;
export function _startIntroSpin() {
  _introSpinActive = true;
  var target = state._pendingMapView;
  var targetLon = target ? target.lon : 20 + Math.random() * 40;
  var targetLat = target ? target.lat : 15 + Math.random() * 25;
  var targetZoom = target ? target.zoom : 2.2;
  if (target) state._pendingMapView = null;
  var startLon = targetLon - 400 - Math.random() * 200;
  var startLat = 0;
  var startZoom = 0.05;
  var midZoom = Math.min(targetZoom + 1.2, 4.5);
  var endZoom = targetZoom;
  // v0 = distance * (1 - friction), total distance = v0 / (1 - f)
  var totalSpin = targetLon - startLon;
  var spinFriction = 0.982;
  var spinVelocity = totalSpin * (1 - spinFriction);
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
export function initMap() {
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
    state.map.setProjection({ type: "globe" });
    _startIntroSpin();
  });
  const _prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let _autoRotate = !_prefersReducedMotion;
  let _rotateId = null;
  function startAutoRotate() {
    if (_rotateId || !_autoRotate || _introSpinActive) return;
    _rotateId = setInterval(() => {
      if (!_autoRotate || _introSpinActive) {
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
  let _moveTimer = null;
  state.map.on("moveend", () => {
    clearTimeout(_moveTimer);
    _moveTimer = setTimeout(saveStateToURL, 500);
  });
  state.map.on("load", onMapLoad);
}
state.mapLabelsVisible = false;
export function setMapLabelsVisible(visible) {
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
export function toggleMapLabels() {
  setMapLabelsVisible(!state.mapLabelsVisible);
}
export function updateMapToggleButton() {
  // Globe toggle removed — stub kept for any remaining callers
}
export function showLoadingBar() {
  const bar = document.getElementById("loading-bar");
  if (bar) bar.classList.remove("hidden");
}
export function hideLoadingBar() {
  const bar = document.getElementById("loading-bar");
  if (!bar) return;
  bar.classList.add("hidden");
  setTimeout(() => bar.remove(), 600);
}
export async function onMapLoad() {
  addMapLayers(state.map, "");
  addMapInteractions(state.map, "");
  setMapLabelsVisible(false);
  showLoadingBar();
  // Phase 1: instant map dots from last hour
  await fetchCloudData(1);
  // Phase 2: full 24h data + metadata
  const storiesP = loadAll(null, 24);
  const conceptsP = loadConcepts();
  const sourcesP = loadSources();
  const eventsP = loadEvents();
  const overviewP = loadPresetOverview();
  const narrativesP = loadNarratives();
  await Promise.allSettled([storiesP, conceptsP, sourcesP, eventsP, overviewP, narrativesP]);
  hideLoadingBar();
  if (state._pendingMapView && state.map) {
    _introSpinActive = false;
    state.map.jumpTo({ center: [state._pendingMapView.lon, state._pendingMapView.lat], zoom: state._pendingMapView.zoom });
    state._pendingMapView = null;
  }
  // Phase 3: if time filter wants more than 24h, expand in background
  var filterHours = parseFloat(document.getElementById("filter-time").value) || 0;
  if (filterHours === 0 || filterHours > 24) {
    _expandTimeRange(filterHours);
  }
}
export function getHoverTooltip() {
  if (!state.hoverTooltipEl) {
    state.hoverTooltipEl = document.createElement("div");
    state.hoverTooltipEl.id = "hover-tooltip";
    document.body.appendChild(state.hoverTooltipEl);
  }
  return state.hoverTooltipEl;
}
export function showHoverTooltip(point, features) {
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
  tooltip.style.maxHeight = "";
  const rect = tooltip.getBoundingClientRect();
  if (rect.right > window.innerWidth - 10) tooltip.style.left = point.x - rect.width - 16 + "px";
  if (rect.bottom > window.innerHeight - 10) tooltip.style.top = point.y - rect.height - 10 + "px";
  const rect2 = tooltip.getBoundingClientRect();
  if (rect2.left < 10) tooltip.style.left = "10px";
  if (rect2.top < 10) {
    tooltip.style.top = "10px";
    tooltip.style.maxHeight = (window.innerHeight - 20) + "px";
  }
}
export function hideHoverTooltip() {
  if (state.hoverTooltipEl) state.hoverTooltipEl.classList.remove("visible");
}
export function _sortInfoStories(unique, sortMode) {
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
export function _renderInfoStories(unique, headerHtml, events) {
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
      highlightStory(parseInt(card.dataset.storyId));
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
export function openInfoPanel(title, features, loading, opts) {
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
export function closeInfoPanel() {
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
export function setLocationFilter(filter) {
  state.activeLocationFilter = filter;
  applyLocationVisuals();
}
export function clearLocationFilter() {
  if (!state.activeLocationFilter) return;
  state.activeLocationFilter = null;
  applyLocationVisuals();
}
export function applyLocationVisuals() {
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
export function applyFilters() {
  try {
    const filtered = computeFilteredState();
    state._filterState = filtered;
    if (state.map.getSource("stories-cloud")) state.map.getSource("stories-cloud").setData(filtered.clouds);
    updateCountryPolygons(filtered.clouds);
    _animateCount(document.getElementById("stat-showing"), filtered.stats.showing);
    const searchQ = (document.getElementById("search-box").value || "").trim();
    const searchCount = document.getElementById("search-count");
    if (searchQ && searchCount) {
      const hidden = filtered.stats.searchMatchAll - filtered.stats.showing;
      if (hidden > 0) {
        searchCount.textContent = `${filtered.stats.showing} results · ${hidden} hidden by filters`;
      } else {
        searchCount.textContent = `${filtered.stats.showing} results`;
      }
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
    if (!document.getElementById("sources-popup").classList.contains("visible")) {
      renderSourceChips(filtered.sourceCounts);
    } else {
      renderSourceChips();
    }
    updatePresetOverviewFilterState(filtered.hasFilters);
    renderActiveFilterPills();
    updateFilterStatus();
    updateMobileBar();
    saveStateToURL();
  } catch (err) {
    console.error("applyFilters error:", err);
  }
}
export var _PILL_COLLAPSE_THRESHOLD = 5;
export function renderActiveFilterPills() {
  const container = document.getElementById("active-filters");
  if (!container) return;
  const pills = [];
  for (const c of state.activeConcepts) {
    const domain = state.conceptDomainMap[c] || "general";
    const color = DOMAIN_COLORS[domain] || "#484f58";
    pills.push(`<span class="filter-pill" style="border-color:${color}" data-type="concept" data-value="${escapeHtml(c)}">${escapeHtml(c)} <span class="filter-pill-x">&times;</span></span>`);
  }
  if (state.excludedConcepts.size > _PILL_COLLAPSE_THRESHOLD) {
    pills.push(`<span class="filter-pill excluded-pill" data-type="clear-exclude-concepts" data-value="">${state.excludedConcepts.size} topics excluded <span class="filter-pill-x">&times;</span></span>`);
  } else {
    for (const c of state.excludedConcepts) {
      pills.push(`<span class="filter-pill excluded-pill" data-type="exclude-concept" data-value="${escapeHtml(c)}">-${escapeHtml(c)} <span class="filter-pill-x">&times;</span></span>`);
    }
  }
  if (state.activeSources.size > _PILL_COLLAPSE_THRESHOLD) {
    pills.push(`<span class="filter-pill source-pill" data-type="clear-sources" data-value="">${state.activeSources.size} sources selected <span class="filter-pill-x">&times;</span></span>`);
  } else {
    for (const s of state.activeSources) {
      pills.push(`<span class="filter-pill source-pill" data-type="source" data-value="${escapeHtml(s)}">${escapeHtml(s)} <span class="filter-pill-x">&times;</span></span>`);
    }
  }
  if (state.excludedSources.size > _PILL_COLLAPSE_THRESHOLD) {
    pills.push(`<span class="filter-pill excluded-pill" data-type="clear-exclude-sources" data-value="">${state.excludedSources.size} sources excluded <span class="filter-pill-x">&times;</span></span>`);
  } else {
    for (const s of state.excludedSources) {
      pills.push(`<span class="filter-pill excluded-pill" data-type="exclude-source" data-value="${escapeHtml(s)}">-${escapeHtml(s)} <span class="filter-pill-x">&times;</span></span>`);
    }
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
      if (type === "clear-exclude-concepts") state.excludedConcepts.clear();
      if (type === "clear-sources") state.activeSources.clear();
      if (type === "clear-exclude-sources") state.excludedSources.clear();
      applyFilters();
      markPresetModified();
    });
  });
}
export var _TIME_LABELS = { "": "", "0.0167": "1m", "1": "1h", "3": "3h", "6": "6h", "12": "12h", "24": "24h", "48": "2d", "168": "7d" };
export var _TIME_BADGE_LABELS = { "": "All Time", "0.0167": "This Minute", "1": "Last Hour", "3": "Last 3 Hours", "6": "Last 6 Hours", "12": "Last 12 Hours", "24": "Last 24 Hours", "48": "Last 2 Days", "168": "Last 7 Days" };
export var _TIME_CYCLE = ["", "0.0167", "1", "3", "6", "12", "24", "48", "168"];
export function _updateTimeBadge() {
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
export function _initTimeBadge() {
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
    if (menu.classList.contains("open")) {
      menu.classList.remove("open");
      _markPopupDismiss();
    }
  });
}
export function updateFilterStatus() {
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
export async function fetchCloudData(hours) {
  try {
    const params = new URLSearchParams();
    if (hours) params.set("hours", String(hours));
    state.cloudData = await _fetchJson("/api/stories/clouds?" + params.toString());
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
export async function fetchStories(since, limit, hours) {
  const params = new URLSearchParams();
  if (since) params.set("since", since);
  if (limit) params.set("limit", String(limit));
  if (hours) params.set("hours", String(hours));
  return _fetchJson("/api/stories?" + params.toString());
}
state._loadedHours = 0;
export async function loadAll(limit, hours) {
  try {
    const data = await fetchStories(null, limit, hours);
    state.geojsonData = data;
    state.lastFetchTime = (/* @__PURE__ */ new Date()).toISOString();
    state._lastDataUpdate = Date.now();
    await fetchCloudData(hours);
    updateStats();
    applyFilters();
    if (hours) state._loadedHours = hours;
  } catch (err) {
    console.error("Failed to load stories:", err);
  }
}
export async function loadRemainingStories(hours) {
  try {
    const data = await fetchStories(null, null, hours);
    state.geojsonData = data;
    state._lastDataUpdate = Date.now();
    await fetchCloudData(hours);
    updateStats();
    applyFilters();
    state._loadedHours = hours || Infinity;
  } catch (err) {
    console.error("Failed to load remaining stories:", err);
  }
}
export function _expandTimeRange(hours) {
  if (state._expandingRange) return;
  state._expandingRange = true;
  loadRemainingStories(hours || null).then(function() {
    state._expandingRange = false;
  });
}
export async function pollUpdates() {
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
export function classifyTopic(topic) {
  const lower = topic.toLowerCase();
  for (const rule of TOPIC_DOMAIN_RULES) {
    for (const kw of rule.keywords) {
      if (lower.includes(kw)) return { domain: rule.domain, color: rule.color };
    }
  }
  return { domain: "general", color: "#484f58" };
}
export async function loadConcepts() {
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
export function renderConceptChips(filteredCounts) {
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
export function toggleConcept(name) {
  state.excludedConcepts.delete(name);
  if (state.activeConcepts.has(name)) state.activeConcepts.delete(name);
  else state.activeConcepts.add(name);
  markPresetModified();
  updateFilterDrawerToggle();
  applyFilters();
}
export function toggleExclude(name) {
  state.activeConcepts.delete(name);
  if (state.excludedConcepts.has(name)) state.excludedConcepts.delete(name);
  else state.excludedConcepts.add(name);
  markPresetModified();
  updateFilterDrawerToggle();
  applyFilters();
}
export function clearAllFilters() {
  document.getElementById("search-box").value = "";
  document.getElementById("filter-time").value = "24";
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
export function toggleDomain(domain) {
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
export function excludeDomain(domain) {
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
export function toggleFilterDrawer() {
  state.filterDrawerOpen = !state.filterDrawerOpen;
  const drawer = document.getElementById("filter-drawer");
  const btn = document.getElementById("filter-drawer-toggle");
  drawer.classList.toggle("visible", state.filterDrawerOpen);
  btn.classList.toggle("open", state.filterDrawerOpen);
  updateFilterDrawerToggle();
}
export function updateFilterDrawerToggle() {
  const btn = document.getElementById("filter-drawer-toggle");
  const originFilterCount = state.activeOrigins.size < 15 ? 1 : 0;
  const activeCount = state.activeConcepts.size + state.excludedConcepts.size + originFilterCount;
  btn.classList.toggle("has-active", activeCount > 0);
  btn.textContent = activeCount > 0 ? `Refine (${activeCount})` : "Refine";
}
export function updateSourcesIndicator() {
  const el = document.getElementById("stat-sources");
  const hasFilter = state.activeSources.size > 0 || state.excludedSources.size > 0;
  el.classList.toggle("has-source-filter", hasFilter);
}
export function togglePresetOverview() {
  const bar = document.getElementById("preset-overview-bar");
  bar.classList.toggle("expanded");
}
export function updatePresetOverviewFilterState(hasFilters) {
  const bar = document.getElementById("preset-overview-bar");
  bar.classList.toggle("has-filters", !!hasFilters);
}
state._pendingPresetId = null;
export var _editingPresetId = null;
export function _matchingConcepts(keywords) {
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
export function _getRemovedPresets() {
  try {
    return JSON.parse(localStorage.getItem("tm_removed_worlds") || "[]");
  } catch (e) {
    return [];
  }
}
export function loadPresets() {
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
export function savePresets() {
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
export function loadPresetPrefs() {
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
export function savePresetPrefs() {
  try {
    localStorage.setItem("tm_world_prefs", JSON.stringify(state.presetPrefs));
  } catch (e) {
    console.error("Failed to save preset prefs:", e);
  }
}
export function _getVisiblePresetEntries() {
  return Object.entries(state.allPresets).filter(([id]) => state.presetPrefs[id]?.visible !== false).sort((a, b) => (state.presetPrefs[a[0]]?.order ?? 99) - (state.presetPrefs[b[0]]?.order ?? 99));
}
export function _autoDetectIcon(name, world) {
  for (const [re, emoji] of NAME_EMOJI_MAP) {
    if (re.test(name)) return emoji;
  }
  if (world?.config?.brightSideMode) return "\u{1F31F}";
  if (world?.feedTags?.some((t) => t === "sports")) return "\u{1F3C6}";
  return null;
}
export function _autoPickColor(id) {
  let hash = 0;
  for (let i = 0; i < id.length; i++) hash = (hash << 5) - hash + id.charCodeAt(i) | 0;
  return CUSTOM_COLOR_PALETTE[Math.abs(hash) % CUSTOM_COLOR_PALETTE.length];
}
export function captureCurrentConfig() {
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
export function applyPresetConfig(config, keywords, feedTags) {
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
export async function switchPreset(presetId) {
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
    document.getElementById("filter-time").value = "24";
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
  switchView(_getPresetDefaultView(presetId));
  _reorderViewTabs(presetId);
  _blendLocationColors(state.cloudData.features || []);
  _updateLegendColors();
  updatePresetsBar();
  renderPresetOverview();
  applyFilters();
}
export function markPresetModified() {
  if (!state.activePresetId) return;
  state.presetModified = true;
  updatePresetsBar();
}
export function updatePresetsBarOverflow() {
  const wrapper = document.querySelector(".presets-bar-wrapper");
  const bar = document.getElementById("presets-bar");
  if (!wrapper || !bar) return;
  const sl = bar.scrollLeft;
  const sw = bar.scrollWidth;
  const cw = bar.clientWidth;
  wrapper.classList.toggle("scroll-left", sl > 4);
  wrapper.classList.toggle("scroll-right", sl + cw < sw - 4);
}
export function updatePresetsBar() {
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
  _updatePresetDropdownTrigger();
}
export function saveCurrentAsPreset(name) {
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
export var PRESET_SHORT_LABELS = { entertainment: "Ent." };
export function renderPresetsBar() {
  const bar = document.getElementById("presets-bar");
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
      switchPreset(id);
    });
    bar.appendChild(btn);
  }
  // Render dropdown menu
  _renderPresetDropdownMenu(visibleEntries);
  updatePresetsBar();
  updatePresetsBarOverflow();
}
export function _renderPresetDropdownMenu(visibleEntries) {
  const menu = document.getElementById("preset-dropdown-menu");
  if (!menu) return;
  menu.innerHTML = "";
  for (const [id, world] of visibleEntries) {
    const item = document.createElement("button");
    item.className = "preset-dropdown-item";
    item.dataset.world = id;
    const icon = PRESET_ICONS[id] || state.presetPrefs[id]?.icon || "";
    const label = world.label;
    const desc = PRESET_PICKER_DESCRIPTIONS[id] || "";
    item.innerHTML =
      `<span class="preset-dropdown-item-icon">${icon}</span>` +
      `<span class="preset-dropdown-item-dot" style="background:${world.color}"></span>` +
      `<span class="preset-dropdown-item-info"><span class="preset-dropdown-item-label">${escapeHtml(label)}</span>` +
      (desc ? `<span class="preset-dropdown-item-desc">${escapeHtml(desc)}</span>` : "") +
      `</span>` +
      `<span class="preset-dropdown-item-count"></span>`;
    item.addEventListener("click", (e) => {
      e.stopPropagation();
      _closePresetDropdown();
      switchPreset(id);
    });
    menu.appendChild(item);
  }
}
export function _updatePresetDropdownTrigger() {
  const trigger = document.getElementById("preset-dropdown-trigger");
  if (!trigger) return;
  const presetId = state.activePresetId || "all";
  const world = state.allPresets[presetId];
  if (!world) return;
  const icon = PRESET_ICONS[presetId] || state.presetPrefs[presetId]?.icon || "";
  const iconEl = trigger.querySelector(".preset-dropdown-icon");
  const labelEl = trigger.querySelector(".preset-dropdown-label");
  if (iconEl) iconEl.textContent = icon;
  if (labelEl) labelEl.textContent = world.label;
  // Tint trigger border with preset color
  trigger.style.borderColor = world.color;
  // Update active state in dropdown menu
  document.querySelectorAll(".preset-dropdown-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.world === presetId);
  });
  // Update counts in dropdown
  const domainCounts = {};
  for (const n of state.narrativesData || []) {
    const d = n.domain || "news";
    domainCounts[d] = (domainCounts[d] || 0) + 1;
  }
  document.querySelectorAll(".preset-dropdown-item").forEach((item) => {
    const id = item.dataset.world;
    const domain = PRESET_DOMAIN_MAP[id];
    const count = domain ? domainCounts[domain] || 0 : 0;
    const countEl = item.querySelector(".preset-dropdown-item-count");
    if (countEl) countEl.textContent = count > 0 ? count : "";
  });
}
export function _togglePresetDropdown() {
  const trigger = document.getElementById("preset-dropdown-trigger");
  const menu = document.getElementById("preset-dropdown-menu");
  if (!trigger || !menu) return;
  const isOpen = menu.classList.contains("open");
  if (isOpen) {
    _closePresetDropdown();
  } else {
    trigger.classList.add("open");
    menu.classList.add("open");
    // Scroll active item into view
    const active = menu.querySelector(".preset-dropdown-item.active");
    if (active) active.scrollIntoView({ block: "nearest" });
  }
}
export function _closePresetDropdown() {
  const trigger = document.getElementById("preset-dropdown-trigger");
  const menu = document.getElementById("preset-dropdown-menu");
  if (trigger) trigger.classList.remove("open");
  if (menu) menu.classList.remove("open");
}
// === Preset Picker ===
export var PRESET_PICKER_DESCRIPTIONS = {
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
export var _presetPickerSelection = null;
export var _pickerOverlayClickRef = null;
export function showPresetPicker() {
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
export function _presetPickerToggle(e) {
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
export function closePresetPicker() {
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
export function confirmPresetPicker() {
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
}
export function _loadVisiblePresets() {
  try {
    var raw = localStorage.getItem("tm_visible_worlds");
    if (!raw) return null;
    var arr = JSON.parse(raw);
    if (Array.isArray(arr) && arr.length > 0) return arr;
  } catch (e) {}
  return null;
}
export function _applyVisiblePresetsToPrefs() {
  var visible = _loadVisiblePresets();
  for (var id in state.presetPrefs) {
    if (WORLD_PRESETS[id]) {
      state.presetPrefs[id].visible = visible ? visible.indexOf(id) !== -1 : true;
    }
  }
  savePresetPrefs();
}
export function _syncVisiblePresetsFromPrefs() {
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
export function togglePresetsPanel() {
  const panel = document.getElementById("presets-panel");
  panel.classList.toggle("visible");
  if (panel.classList.contains("visible")) {
    renderPresetsPanelContents();
  }
}
export function closePresetsPanel() {
  document.getElementById("presets-panel").classList.remove("visible");
}
export var _draggedPresetId = null;
export var _dragOverPresetId = null;
export function renderPresetsPanelContents() {
  const listContainer = document.getElementById("presets-panel-list");
  listContainer.innerHTML = "";
  const sorted = Object.entries(state.allPresets).sort((a, b) => (state.presetPrefs[a[0]]?.order ?? 99) - (state.presetPrefs[b[0]]?.order ?? 99));
  // Only show visible presets in main list
  const visibleSorted = sorted.filter(([id]) => {
    const pref = state.presetPrefs[id] || {};
    return pref.visible !== false;
  });
  visibleSorted.forEach(([id, world], idx) => {
    const pref = state.presetPrefs[id] || {};
    const isActive = id === state.activePresetId;
    const icon = PRESET_ICONS[id] || pref.icon;
    const item = document.createElement("div");
    item.className = "preset-panel-item" + (isActive ? " active-preset" : "");
    item.draggable = true;
    item.dataset.presetId = id;
    // Drag and drop handlers
    item.addEventListener("dragstart", (e) => {
      _draggedPresetId = id;
      item.classList.add("dragging");
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", id);
    });
    item.addEventListener("dragend", () => {
      _draggedPresetId = null;
      _dragOverPresetId = null;
      item.classList.remove("dragging");
      listContainer.querySelectorAll(".preset-panel-item").forEach(el => {
        el.classList.remove("drag-over-above", "drag-over-below");
      });
    });
    item.addEventListener("dragover", (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      if (_draggedPresetId === id) return;
      const rect = item.getBoundingClientRect();
      const midY = rect.top + rect.height / 2;
      listContainer.querySelectorAll(".preset-panel-item").forEach(el => {
        el.classList.remove("drag-over-above", "drag-over-below");
      });
      if (e.clientY < midY) {
        item.classList.add("drag-over-above");
      } else {
        item.classList.add("drag-over-below");
      }
      _dragOverPresetId = id;
    });
    item.addEventListener("drop", (e) => {
      e.preventDefault();
      if (!_draggedPresetId || _draggedPresetId === id) return;
      const rect = item.getBoundingClientRect();
      const midY = rect.top + rect.height / 2;
      const dropAbove = e.clientY < midY;
      // Rebuild order: remove dragged, insert at new position
      const currentOrder = visibleSorted.map(([wid]) => wid);
      const fromIdx = currentOrder.indexOf(_draggedPresetId);
      if (fromIdx === -1) return;
      currentOrder.splice(fromIdx, 1);
      let toIdx = currentOrder.indexOf(id);
      if (!dropAbove) toIdx++;
      currentOrder.splice(toIdx, 0, _draggedPresetId);
      // Update order values for all visible presets
      currentOrder.forEach((wid, i) => {
        if (!state.presetPrefs[wid]) state.presetPrefs[wid] = { visible: true, order: i };
        state.presetPrefs[wid].order = i;
      });
      // Hidden presets get order after visible ones
      const hiddenSorted = sorted.filter(([wid]) => {
        const p = state.presetPrefs[wid] || {};
        return p.visible === false;
      });
      hiddenSorted.forEach(([wid], i) => {
        if (!state.presetPrefs[wid]) state.presetPrefs[wid] = { visible: false, order: currentOrder.length + i };
        state.presetPrefs[wid].order = currentOrder.length + i;
      });
      savePresetPrefs();
      renderPresetsBar();
      renderPresetsPanelContents();
    });
    // Drag handle
    const handle = document.createElement("span");
    handle.className = "preset-panel-drag";
    handle.innerHTML = "&#x2630;";
    handle.title = "Drag to reorder";
    item.appendChild(handle);
    const dot = document.createElement("span");
    dot.className = "preset-panel-color";
    dot.style.background = world.color;
    item.appendChild(dot);
    const info = document.createElement("div");
    info.className = "preset-panel-info";
    const labelEl = document.createElement("span");
    labelEl.className = "preset-panel-label";
    labelEl.textContent = (icon ? icon + " " : "") + world.label;
    info.appendChild(labelEl);
    item.appendChild(info);
    // Remove button (hides from bar)
    const removeBtn = document.createElement("button");
    removeBtn.className = "preset-panel-remove";
    removeBtn.innerHTML = "&times;";
    removeBtn.title = "Remove from bar";
    removeBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      if (!state.presetPrefs[id]) state.presetPrefs[id] = { visible: true, order: idx };
      state.presetPrefs[id].visible = false;
      savePresetPrefs();
      _syncVisiblePresetsFromPrefs();
      renderPresetsBar();
      renderPresetsPanelContents();
      if (state.activePresetId === id) {
        const firstVisible = Object.keys(state.allPresets).find(wid => state.presetPrefs[wid]?.visible !== false);
        switchPreset(firstVisible || "all");
      }
    });
    item.appendChild(removeBtn);
    item.addEventListener("click", (e) => {
      if (e.target.closest(".preset-panel-remove") || e.target.closest(".preset-panel-drag")) return;
      switchPreset(id);
      closePresetsPanel();
    });
    listContainer.appendChild(item);
  });
  // Hidden presets section
  const hiddenPresets = sorted.filter(([id]) => {
    const pref = state.presetPrefs[id] || {};
    return pref.visible === false;
  });
  const removedBuiltIn = _getRemovedPresets();
  const allHidden = [...hiddenPresets.map(([id]) => id), ...removedBuiltIn];
  if (allHidden.length > 0) {
    const showRemovedBtn = document.createElement("button");
    showRemovedBtn.className = "preset-panel-show-removed";
    showRemovedBtn.textContent = "Show removed (" + allHidden.length + ")";
    showRemovedBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const section = listContainer.querySelector(".preset-panel-removed-section");
      if (section) {
        section.remove();
        showRemovedBtn.textContent = "Show removed (" + allHidden.length + ")";
        return;
      }
      showRemovedBtn.textContent = "Hide removed";
      const removedSection = document.createElement("div");
      removedSection.className = "preset-panel-removed-section";
      // Hidden-but-not-deleted presets
      hiddenPresets.forEach(([hid]) => {
        const hw = state.allPresets[hid];
        if (!hw) return;
        const hIcon = PRESET_ICONS[hid] || "";
        const hItem = document.createElement("div");
        hItem.className = "preset-panel-item hidden-preset";
        const hDot = document.createElement("span");
        hDot.className = "preset-panel-color";
        hDot.style.background = hw.color;
        hItem.appendChild(hDot);
        const hInfo = document.createElement("div");
        hInfo.className = "preset-panel-info";
        const hLabel = document.createElement("span");
        hLabel.className = "preset-panel-label";
        hLabel.textContent = (hIcon ? hIcon + " " : "") + hw.label;
        hInfo.appendChild(hLabel);
        hItem.appendChild(hInfo);
        const addBtn = document.createElement("button");
        addBtn.className = "preset-panel-add-back";
        addBtn.innerHTML = "+";
        addBtn.title = "Add back";
        addBtn.addEventListener("click", (ev) => {
          ev.stopPropagation();
          if (!state.presetPrefs[hid]) state.presetPrefs[hid] = { visible: true, order: 99 };
          state.presetPrefs[hid].visible = true;
          savePresetPrefs();
          _syncVisiblePresetsFromPrefs();
          renderPresetsBar();
          renderPresetsPanelContents();
        });
        hItem.appendChild(addBtn);
        removedSection.appendChild(hItem);
      });
      // Fully removed built-in presets
      removedBuiltIn.forEach((rid) => {
        const rw = WORLD_PRESETS[rid];
        if (!rw) return;
        const rIcon = PRESET_ICONS[rid] || "";
        const rItem = document.createElement("div");
        rItem.className = "preset-panel-item hidden-preset";
        const rDot = document.createElement("span");
        rDot.className = "preset-panel-color";
        rDot.style.background = rw.color;
        rItem.appendChild(rDot);
        const rInfo = document.createElement("div");
        rInfo.className = "preset-panel-info";
        const rLabel = document.createElement("span");
        rLabel.className = "preset-panel-label";
        rLabel.textContent = (rIcon ? rIcon + " " : "") + rw.label;
        rInfo.appendChild(rLabel);
        rItem.appendChild(rInfo);
        const restoreBtn = document.createElement("button");
        restoreBtn.className = "preset-panel-add-back";
        restoreBtn.innerHTML = "+";
        restoreBtn.title = "Restore preset";
        restoreBtn.addEventListener("click", (ev) => {
          ev.stopPropagation();
          const rem = _getRemovedPresets().filter(x => x !== rid);
          if (rem.length > 0) {
            localStorage.setItem("tm_removed_worlds", JSON.stringify(rem));
          } else {
            localStorage.removeItem("tm_removed_worlds");
          }
          loadPresets();
          renderPresetsBar();
          renderPresetsPanelContents();
        });
        rItem.appendChild(restoreBtn);
        removedSection.appendChild(rItem);
      });
      showRemovedBtn.after(removedSection);
    });
    listContainer.appendChild(showRemovedBtn);
  }
}
export function showSavePresetDialog(editId) {
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
export function closeSavePresetDialog() {
  _editingPresetId = null;
  document.getElementById("preset-save-dialog").classList.remove("visible");
}
export function confirmSavePreset() {
  const input = document.getElementById("preset-save-name");
  const name = input.value.trim().slice(0, 40);
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
export async function loadSources() {
  try {
    const data = await _fetchJson("/api/sources");
    if (data.counts) state.sourceCounts = data.counts;
  } catch (err) {
    console.error("Failed to load sources:", err);
  }
}
export function loadFeedTags() {
  state._feedTagsReady = (async () => {
    try {
      state.feedTagData = await _fetchJson("/api/feed-tags");
    } catch (err) {
      console.error("Failed to load feed tags:", err);
    }
  })();
  return state._feedTagsReady;
}
export function sourcesForTags(tags) {
  const sources = /* @__PURE__ */ new Set();
  for (const tag of tags) {
    for (const src of state.feedTagData.tag_sources[tag] || []) {
      sources.add(src);
    }
  }
  return [...sources];
}
export function renderSourceChips(filteredCounts) {
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
    chip.addEventListener("click", (e) => { e.stopPropagation(); toggleSource(chip.dataset.source); });
    chip.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      e.stopPropagation();
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
export function toggleSource(name) {
  state.excludedSources.delete(name);
  if (state.activeSources.has(name)) state.activeSources.delete(name);
  else state.activeSources.add(name);
  markPresetModified();
  updateFilterDrawerToggle();
  updateSourcesIndicator();
  applyFilters();
}
export function toggleExcludeSource(name) {
  state.activeSources.delete(name);
  if (state.excludedSources.has(name)) state.excludedSources.delete(name);
  else state.excludedSources.add(name);
  markPresetModified();
  updateFilterDrawerToggle();
  updateSourcesIndicator();
  applyFilters();
}
export function setAllSources(mode) {
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
export function setAllTopics(mode) {
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
export async function updateStats() {
  try {
    const [statsResp, sourcesResp] = await Promise.all([fetch("/api/stats"), fetch("/api/sources")]);
    if (statsResp.ok) {
      const stats = await statsResp.json();
      _animateCount(document.getElementById("stat-total"), stats.total_stories || 0);
      const velEl = document.getElementById("stat-velocity");
      if (velEl && stats.last_1h > 0) {
        velEl.textContent = `${stats.last_1h}/hr`;
      }
    }
    if (sourcesResp.ok) {
      const sources = await sourcesResp.json();
      if (sources.counts) {
        state.sourceCounts = sources.counts;
        document.getElementById("stat-sources").textContent = Object.keys(sources.counts).length;
      }
    }
  } catch (err) {
    console.error("Failed to load stats:", err);
  }
}
export function updateStoryList(features) {
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
export function highlightStory(storyId) {
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
export async function loadEvents() {
  try {
    const evResp = await fetch("/api/events?limit=50&min_stories=2");
    if (!evResp.ok) throw new Error(`Events HTTP ${evResp.status}`);
    const evData = await evResp.json();
    state.eventsData = evData.events || [];
    applyFilters();
  } catch (err) {
    console.error("Failed to load events:", err);
  }
}
export function updateEventList(events) {
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
export async function _fetchEventStories(eventId, eventItem, eventObj, lat, lon) {
  try {
    const data = await _fetchJson("/api/events/" + eventId);
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
export function _renderEventStories(eventItem, stories, eventObj) {
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
export function _highlightEventOnMap(stories, lat, lon) {
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
export function _clearEventHighlight() {
  _clearHoverHighlight();
  if (state.map && state.map.getLayer("cloud-points")) {
    state.map.setPaintProperty("cloud-points", "circle-opacity",
      ["interpolate", ["linear"], ["get", "age_hours"], 0, 0.95, 6, 0.85, 24, 0.6, 72, 0.35]);
  }
}
export async function loadNarratives() {
  try {
    const data = await _fetchJson("/api/narratives");
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
export function updateNarrativeList(narratives) {
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
export function openEventStoriesPanel(eventObj, stories) {
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
export function _navigateListItem(direction) {
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
export function _getMapPadding(base) {
  const p = typeof base === "number" ? { top: base, bottom: base, left: base, right: base } : { ...base };
  const panelOpen = document.getElementById("info-panel")?.classList.contains("visible");
  if (panelOpen && window.innerWidth > 768) {
    p.right = Math.max(p.right || 0, 370);
  }
  return p;
}
export function _flyToFeatures(features) {
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
export async function openNarrativeStoriesPanel(narrativeId) {
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
    const data = await _fetchJson("/api/narratives/" + narrativeId);
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
export function addMapInteractions(m, srcPrefix) {
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
    if (state._popupDismissing) return;
    if (_isMobile()) return;
    if (e.defaultPrevented) return;
    const lngLat = m.unproject(e.point);
    if (!lngLat || isNaN(lngLat.lng) || isNaN(lngLat.lat)) return;
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
    if (_isMobile()) return;
    const lngLat = m.unproject(e.point);
    if (!lngLat || isNaN(lngLat.lng) || isNaN(lngLat.lat)) {
      m.getCanvas().style.cursor = "";
      hideHoverTooltip();
      if (m.getSource(proxSrc)) m.getSource(proxSrc).setData(_emptyGeo);
      return;
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
    if (state._popupDismissing) return;
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
      const lngLat = m.unproject([cx, cy]);
      if (!lngLat || isNaN(lngLat.lng) || isNaN(lngLat.lat)) {
        _renderMobilePreviewEmpty();
        _reticleFeatures = [];
        return;
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
    if (_isMobile()) return;
    const z = m.getZoom();
    const scale = z >= 3.5 ? 1 : 1 + (3.5 - Math.max(0, z)) / 3.5 * 0.6;
    feedContainer.style.transform = scale > 1 ? `scale(${scale.toFixed(3)})` : "";
    feedContainer.classList.toggle("zoom-close", z >= 6);
  }
  m.on("zoom", _updateFeedZoom);
  _updateFeedZoom();
}
export function updateFeedButtonCounts(feedCounts) {
  document.querySelectorAll(".feed-btn").forEach((btn) => {
    const feedType = btn.dataset.feed;
    const count = feedCounts && feedCounts[feedType] || 0;
    const label = feedType === "space" ? "Space" : "Internet";
    const icon = feedType === "space" ? "\u2733" : "\u2683";
    btn.innerHTML = `${icon} ${label} <span class="feed-count">${count}</span>`;
    btn.classList.toggle("has-stories", count > 0);
  });
}
export function toggleFeedPanel(feedType) {
  if (state.activeFeedPanel === feedType) {
    closeInfoPanel();
  } else {
    state.activeFeedPanel = feedType;
    document.querySelectorAll(".feed-btn").forEach((b) => b.classList.toggle("active", b.dataset.feed === feedType));
    populateFeedPanel(feedType);
  }
}
export function populateFeedPanel(feedType) {
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
export function _updateSortToggleLabel() {
  const sel = document.getElementById("sort-toggle");
  if (!sel) return;
  const mode = state.currentView === "events" ? state.eventSortMode : state.narrativeSortMode;
  sel.value = mode;
}
export function switchView(view) {
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
export function _reorderViewTabs(presetId) {
  const container = document.getElementById("view-toggles");
  const btns = Array.from(container.querySelectorAll(".view-btn"));
  if (btns.length < 2) return;
  const eventsFirst = _STORIES_DEFAULT_PRESETS.has(presetId);
  const eventsBtn = btns.find((b) => b.dataset.view === "events");
  const narrativesBtn = btns.find((b) => b.dataset.view === "narratives");
  if (!eventsBtn || !narrativesBtn) return;
  if (eventsFirst) {
    container.insertBefore(eventsBtn, narrativesBtn);
  } else {
    container.insertBefore(narrativesBtn, eventsBtn);
  }
}
export async function loadPresetOverview() {
  try {
    state.presetOverview = await _fetchJson("/api/world-overview");
    renderPresetOverview();
  } catch (err) {
    console.error("Failed to load preset overview:", err);
  }
}
export function renderPresetOverview() {
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
export function toggleTheme() {
  state.lightMode = !state.lightMode;
  document.body.classList.toggle("light-mode", state.lightMode);
  localStorage.setItem("thisminute-theme", state.lightMode ? "light" : "dark");
  const style = state.lightMode ? "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json" : "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";
  state.map.setStyle(style);
  state.map.once("style.load", () => {
    state.map.setProjection({ type: "globe" });
    addMapLayers(state.map, "");
    addMapInteractions(state.map, "");
    setMapLabelsVisible(state.mapLabelsVisible);
    _blendLocationColors(state.cloudData.features || []);
    applyFilters();
  });
}
export function applyInitialTheme() {
  if (state.lightMode) document.body.classList.add("light-mode");
}
export var _DOT_THEMES = [
  { id: "domain", label: "Domain", desc: "Tinted by topic" },
  { id: "classic", label: "Classic", desc: "Uniform blue" },
  { id: "mono", label: "Mono", desc: "Single color" },
  { id: "heat", label: "Heat", desc: "Story density" },
  { id: "neon", label: "Neon", desc: "Vivid domains" }
];
export function setDotColorTheme(themeId) {
  state.dotColorTheme = themeId;
  localStorage.setItem("tm_dot_theme", themeId);
  _blendLocationColors(state.cloudData.features || []);
  applyFilters();
  _updateDotThemeMenu();
  _updateLegendForTheme();
}
export function _toggleDotThemeMenu() {
  var menu = document.getElementById("dot-theme-menu");
  if (!menu) return;
  menu.classList.toggle("open");
}
export function _updateDotThemeMenu() {
  var menu = document.getElementById("dot-theme-menu");
  if (!menu) return;
  var items = menu.querySelectorAll(".dot-theme-item");
  for (var i = 0; i < items.length; i++) {
    items[i].classList.toggle("active", items[i].dataset.theme === state.dotColorTheme);
  }
}
export function _updateLegendColors() {
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
    if (presetRGB && state.activePresetId !== "all" && (theme === "domain" || theme === "classic")) {
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
export function _updateLegendForTheme() {
  var legendEl = document.getElementById("map-legend");
  var heatLegend = document.getElementById("heat-legend");
  var legendToggle = document.getElementById("legend-toggle");
  if (!legendEl) return;
  var theme = state.dotColorTheme || "domain";
  if (theme === "heat") {
    legendEl.style.display = "none";
    if (legendToggle) legendToggle.style.display = "none";
    if (heatLegend) heatLegend.style.display = "";
  } else if (theme === "classic" || theme === "mono") {
    legendEl.style.display = "none";
    if (legendToggle) legendToggle.style.display = "none";
    if (heatLegend) heatLegend.style.display = "none";
  } else {
    /* domain or neon */
    legendEl.style.display = "";
    if (legendToggle) legendToggle.style.display = "";
    if (heatLegend) heatLegend.style.display = "none";
  }
}
export function _buildDotThemeUI() {
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
    if (m && m.classList.contains("open")) { m.classList.remove("open"); _markPopupDismiss(); }
  });
  /* Apply legend state on load */
  _updateLegendForTheme();
}
export function saveStateToURL() {
  const params = new URLSearchParams();
  if (state.activePresetId && state.activePresetId !== "all") params.set("world", state.activePresetId);
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
  var _defaultView = _getPresetDefaultView(state.activePresetId || "all");
  if (state.currentView && state.currentView !== _defaultView) params.set("view", state.currentView);
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
export function loadStateFromURL() {
  const hash = window.location.hash.slice(1);
  if (!hash) {
    localStorage.setItem("tm_last_visit", Date.now().toString());
    document.getElementById("filter-time").value = "24";
    const defaultPresetId = _resolvePresetAlias(localStorage.getItem("tm_default_world")) || state.activePresetId;
    if (defaultPresetId && state.allPresets[defaultPresetId]) {
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
    switchView(_getPresetDefaultView(defaultPresetId || "all"));
    _reorderViewTabs(defaultPresetId || "all");
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
  } else {
    switchView(_getPresetDefaultView(state.activePresetId || "all"));
  }
  _reorderViewTabs(state.activePresetId || "all");
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
    var hours = parseFloat(document.getElementById("filter-time").value) || 0;
    if ((hours === 0 || hours > state._loadedHours) && state._loadedHours < Infinity) {
      _expandTimeRange(hours);
    }
    applyFilters();
  });
  document.getElementById("filter-opinion").addEventListener("change", () => {
    applyFilters();
  });
  document.getElementById("filter-drawer-toggle").addEventListener("click", toggleFilterDrawer);
  searchBox.addEventListener("blur", () => {
    if (!searchBox.value.trim()) {
      searchClear.classList.remove("visible");
    }
  });
  document.getElementById("btn-clear-all-filters").addEventListener("click", clearAllFilters);
  document.getElementById("btn-sources-all").addEventListener("click", () => setAllSources("all"));
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
    const isMobile = window.innerWidth <= 768;
    if (isMobile) {
      legendEl.classList.add("collapsed");
      legendToggle.innerHTML = "&#9632;";
    }
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
  var menuThemeBtn = document.getElementById("menu-theme");
  if (menuThemeBtn) menuThemeBtn.addEventListener("click", function() {
    toggleTheme();
    document.getElementById("main-menu").classList.remove("visible");
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
    setTimeout(togglePresetsPanel, 0);
  });
  document.getElementById("menu-feeds").addEventListener("click", () => {
    document.getElementById("main-menu").classList.remove("visible");
    openUserFeedsDialog();
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
      _markPopupDismiss();
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
    if (state._popupDismissing) return;
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
      _markPopupDismiss();
    }
  });
  document.getElementById("presets-bar").addEventListener("scroll", updatePresetsBarOverflow);
  document.getElementById("preset-dropdown-trigger").addEventListener("click", (e) => {
    e.stopPropagation();
    _togglePresetDropdown();
  });
  document.addEventListener("click", (e) => {
    const menu = document.getElementById("preset-dropdown-menu");
    const trigger = document.getElementById("preset-dropdown-trigger");
    if (menu && menu.classList.contains("open") && !menu.contains(e.target) && e.target !== trigger) {
      _closePresetDropdown();
      _markPopupDismiss();
    }
  });
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
    if (!panel.contains(e.target)) {
      panel.classList.remove("visible");
      _markPopupDismiss();
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
      document.getElementById("search-box").focus();
    }
    if (e.key === "Escape") {
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
export function toggleSidebar() {
  const body = document.body;
  const btn = document.getElementById("sidebar-toggle");
  body.classList.toggle("sidebar-collapsed");
  btn.innerHTML = body.classList.contains("sidebar-collapsed") ? "&rsaquo;" : "&lsaquo;";
  setTimeout(() => state.map.resize(), 350);
}
export var _feedbackTarget = null;
export function _getBrowserHash() {
  const raw = navigator.userAgent + screen.width + "x" + screen.height;
  let h = 0;
  for (let i = 0; i < raw.length; i++) {
    h = (h << 5) - h + raw.charCodeAt(i) | 0;
  }
  return Math.abs(h).toString(36);
}
export function openFeedbackDialog(target) {
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
export function closeFeedbackDialog() {
  document.getElementById("feedback-dialog").classList.remove("visible");
  _feedbackTarget = null;
}
export async function submitFeedback() {
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
export function openUserFeedsDialog() {
  var dialog = document.getElementById("user-feeds-dialog");
  dialog.classList.add("visible");
  _loadUserFeeds();
}
export function closeUserFeedsDialog() {
  document.getElementById("user-feeds-dialog").classList.remove("visible");
  document.getElementById("user-feed-url").value = "";
  document.getElementById("user-feed-url").classList.remove("input-error");
  var hint = document.getElementById("user-feeds-hint");
  hint.textContent = "Added feeds appear on the map within 15 minutes.";
  hint.style.color = "";
}
export async function _loadUserFeeds() {
  var bh = _getBrowserHash();
  var list = document.getElementById("user-feeds-list");
  var counter = document.getElementById("user-feeds-count");
  try {
    var feeds = await _fetchJson("/api/user-feeds?hash=" + encodeURIComponent(bh));
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
      var statusTitle = feed.last_error ? "Error: " + escapeHtml(feed.last_error) : (feed.last_fetched ? "Active" : "Pending first fetch");
      var errorHtml = feed.last_error ? '<div class="user-feed-error-msg" title="' + escapeHtml(feed.last_error).replace(/"/g, "&quot;") + '">' + escapeHtml(feed.last_error) + '</div>' : "";
      item.innerHTML = '<div class="user-feed-info">' +
        '<div class="user-feed-title" title="' + escapeHtml(feed.title || "").replace(/"/g, "&quot;") + '">' + escapeHtml(feed.title || feed.url) + '</div>' +
        '<div class="user-feed-url" title="' + escapeHtml(feed.url).replace(/"/g, "&quot;") + '">' + escapeHtml(feed.url) + '</div>' +
        errorHtml +
        '</div>' +
        '<div class="user-feed-meta">' +
        '<span class="user-feed-tag">' + escapeHtml(feed.feed_tag) + '</span>' +
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
export async function _addUserFeed() {
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
export async function _deleteUserFeed(feedId) {
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
