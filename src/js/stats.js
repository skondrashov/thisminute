import { state } from './state.js';

export function showNewBadge(count) {
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
export function triggerPulse(storyIds) {
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
export function _animateCount(el, target) {
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
