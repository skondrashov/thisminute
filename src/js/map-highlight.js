import { state, _DOMAIN_HIGHLIGHT_COLORS } from './state.js';

export function _showHoverHighlight(storyIds, domain) {
  if (!storyIds || !storyIds.length || !state.map.getSource("hover-highlight")) return;
  const idSet = new Set(storyIds);
  const features = state.geojsonData.features.filter((f) => idSet.has(f.properties.id));
  const palette = state.lightMode ? _DOMAIN_HIGHLIGHT_COLORS.light : _DOMAIN_HIGHLIGHT_COLORS.dark;
  const color = palette[domain] || palette.news;
  state.map.setPaintProperty("hover-highlight", "circle-color", color);
  state.map.setPaintProperty("hover-highlight", "circle-stroke-color", color);
  state.map.getSource("hover-highlight").setData({ type: "FeatureCollection", features });
}
export function _clearHoverHighlight() {
  if (state.map.getSource("hover-highlight")) {
    state.map.getSource("hover-highlight").setData({ type: "FeatureCollection", features: [] });
  }
}
