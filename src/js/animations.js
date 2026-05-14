import { state } from './state.js';

export function _initAnimCanvas() {
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
export function _stopAnim(stateKey) {
  if (state[stateKey]) { cancelAnimationFrame(state[stateKey]); state[stateKey] = null; }
  const canvas = document.getElementById("info-panel-bg-canvas");
  if (canvas) {
    if (canvas._resizeHandler) { window.removeEventListener("resize", canvas._resizeHandler); canvas._resizeHandler = null; }
    canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height);
  }
}
export function startNetworkAnimation() {
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
export function stopNetworkAnimation() { _stopAnim("networkAnimId"); }
export function startSpaceAnimation() {
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
export function stopSpaceAnimation() { _stopAnim("spaceAnimId"); }
