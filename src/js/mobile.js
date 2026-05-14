import { state, _markPopupDismiss } from './state.js';
import { toggleMapLabels, _toggleDotThemeMenu } from './main.js';

export var _isMobile = () => window.innerWidth <= 768;
export function setPaneHeight(h) {
  var vh = window.innerHeight;
  var clamped = Math.max(56, Math.min(vh * 0.9, h));
  document.body.style.setProperty("--pane-height", clamped + "px");
  var sidebar = document.getElementById("sidebar");
  sidebar.dataset.paneHeight = clamped;
  if (state.map) state.map.resize();
}
export function setSheetState(sheetState) {
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
export function toggleSheet() {
  const sidebar = document.getElementById("sidebar");
  const current = sidebar.dataset.sheetState || "closed";
  if (current === "closed") setSheetState("half");
  else setSheetState("closed");
}
export function updateMobileBar() {
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
export function initMobileSheet() {
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
export function initMobileMapControls() {
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
        _markPopupDismiss();
      }
    });
  }
  var mLabels = document.getElementById("mobile-labels-btn");
  var mTheme = document.getElementById("mobile-theme-btn");
  var mSpin = document.getElementById("mobile-spin-btn");
  var mReload = document.getElementById("mobile-reload-btn");
  if (mLabels) mLabels.addEventListener("click", toggleMapLabels);
  if (mTheme) mTheme.addEventListener("click", _toggleDotThemeMenu);
  if (mSpin) mSpin.addEventListener("click", () => { if (state.toggleAutoRotate) state.toggleAutoRotate(); });
  if (mReload) mReload.addEventListener("click", () => {
    mReload.classList.add("spinning");
    setTimeout(() => location.reload(), 300);
  });
}
export function initInfoPanelSwipe(closeInfoPanel2) {
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
