import { state, PRESET_DOMAIN_MAP, _DOMAINLESS_HIDE_SITUATIONS, BRIGHT_SIDE_MIN_SCORE, _hasVetoTopic, CURIOUS_MIN_SCORE } from './state.js';

export function _getPresetDomain(presetId) {
  return PRESET_DOMAIN_MAP[presetId] || null;
}
export function computeFilteredState() {
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
  let searchMatchAll = 0;
  const _searchTerms = searchText ? searchText.split(/\s+/).filter((t) => t.length > 0) : [];
  for (const f of state.geojsonData.features) {
    const p = f.properties;
    let concepts = p.concepts;
    if (typeof concepts === "string") try {
      concepts = JSON.parse(concepts);
    } catch {
      concepts = [];
    }
    concepts = concepts || [];
    if (searchText) {
      const kw = Array.isArray(p.search_keywords) ? p.search_keywords.join(" ") : "";
      const haystack = `${p.title || ""} ${p.summary || ""} ${p.location_name || ""} ${kw}`.toLowerCase();
      if (_searchTerms.every((term) => haystack.includes(term))) searchMatchAll++;
    }
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
        if (!_searchTerms.every((term) => haystack.includes(term))) continue;
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
  let events;
  if (contentFiltering && storyIds) {
    events = state.eventsData.filter((ev) => {
      if (ev.story_ids && ev.story_ids.some((id) => storyIds.has(id))) return true;
      if (searchText) {
        const haystack = `${ev.title || ""} ${ev.description || ""} ${ev.summary || ""}`.toLowerCase();
        return _searchTerms.every((term) => haystack.includes(term));
      }
      return false;
    });
  } else {
    events = [...state.eventsData];
  }
  if (state.eventSortMode === "new") {
    events.sort((a, b) => new Date(b.last_updated || 0).getTime() - new Date(a.last_updated || 0).getTime());
  } else if (state.eventSortMode === "broadest") {
    events.sort((a, b) => (b.source_count || 0) - (a.source_count || 0) || (b.story_count || 0) - (a.story_count || 0));
  } else {
    events.sort((a, b) => (b.story_count || 0) - (a.story_count || 0));
  }
  const allStoryIds = new Set(state.geojsonData.features.map((f) => f.properties.id));
  const presetDomain = _getPresetDomain(state.activePresetId);
  let narratives = (state.narrativesData || []).map((n) => {
    // Domain-matched narratives bypass source filtering for their count —
    // the domain filter IS the relevance filter, and situations often contain
    // stories from general-news sources that would be excluded by feedTag filters
    const matchesDomain = presetDomain && (n.domain || "news") === presetDomain;
    const useSourceFilter = contentFiltering && storyIds && n.story_ids && !matchesDomain;
    return {
      ...n,
      filteredCount: useSourceFilter ? n.story_ids.filter((id) => storyIds.has(id)).length : n.story_ids ? n.story_ids.filter((id) => allStoryIds.has(id)).length || n.story_count : n.story_count
    };
  });
  if (_DOMAINLESS_HIDE_SITUATIONS.has(state.activePresetId)) {
    narratives = [];
  } else if (presetDomain) {
    narratives = narratives.filter((n) => (n.domain || "news") === presetDomain);
  }
  if (state.brightSideMode && !presetDomain) {
    narratives = narratives.filter((n) => (n.bright_side_count || 0) > 0);
  }
  if (searchText) {
    narratives = narratives.filter((n) => {
      const haystack = `${n.title || ""} ${n.description || ""} ${(n.theme_tags || []).join(" ")}`.toLowerCase();
      const textMatch = _searchTerms.every((term) => haystack.includes(term));
      return textMatch || n.filteredCount > 0;
    });
  } else {
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
      sources: Object.keys(sourceCountMap).length,
      searchMatchAll
    },
    hasFilters
  };
}
