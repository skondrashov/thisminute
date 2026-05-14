import { openFeedbackDialog } from './main.js';

export function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
export function truncateRaw(text, maxLen) {
  if (!text) return "";
  return text.length <= maxLen ? text : text.slice(0, maxLen) + "...";
}
export async function _fetchJson(url, options) {
  var resp = await fetch(url, options);
  if (!resp.ok) throw new Error("HTTP " + resp.status);
  return resp.json();
}

/** Shared clipboard-copy with checkmark animation. */
export function _copyToClipboard(btn, url, originalIcon) {
  originalIcon = originalIcon || "&#128279;";
  function onSuccess() {
    btn.textContent = "\u2713";
    if (btn.classList) btn.classList.add("copied");
    setTimeout(() => {
      btn.innerHTML = originalIcon;
      if (btn.classList) btn.classList.remove("copied");
    }, 1500);
  }
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(url).then(onSuccess).catch(() => {
      _clipboardFallback(url, onSuccess);
    });
  } else {
    _clipboardFallback(url, onSuccess);
  }
}
export function _clipboardFallback(text, onSuccess) {
  var ta = document.createElement("textarea");
  ta.value = text;
  ta.style.position = "fixed";
  ta.style.opacity = "0";
  document.body.appendChild(ta);
  ta.select();
  try { document.execCommand("copy"); if (onSuccess) onSuccess(); } catch (e) {}
  document.body.removeChild(ta);
}

/** Shared feedback-button wiring — call on any container with .feedback-btn elements. */
export function _wireFeedbackButtons(container) {
  container.querySelectorAll(".feedback-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      openFeedbackDialog({ type: btn.dataset.fbType, id: parseInt(btn.dataset.fbId), title: btn.dataset.fbTitle });
    });
  });
}
export function formatTime(isoString) {
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
export function formatFullTime(isoString) {
  if (!isoString) return "";
  try {
    const d = new Date(isoString);
    return d.toLocaleString(void 0, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
  } catch {
    return "";
  }
}
export function _highlightText(escapedHtml, query) {
  if (!query || query.length < 2) return escapedHtml;
  const escaped = escapeHtml(query);
  const re = new RegExp(`(${escaped.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi");
  return escapedHtml.replace(re, "<mark>$1</mark>");
}
export function _getFavicon(url) {
  if (!url) return "";
  try {
    const domain = new URL(url).hostname;
    return `<img class="source-favicon" src="https://www.google.com/s2/favicons?sz=16&domain=${domain}" alt="" width="14" height="14" onerror="this.remove()">`;
  } catch {
    return "";
  }
}
