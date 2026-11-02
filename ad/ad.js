const FMT = new URLSearchParams(location.search).get("fmt") === "vertical" ? "v" : "w";
const V = FMT === "v";
const W = V ? 1080 : 1920, H = V ? 1920 : 1080;
const BEAT = 60 / 124;
const stage = document.getElementById("stage");
stage.style.width = W + "px";
stage.style.height = H + "px";

const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const prog = (t, a, d) => clamp((t - a) / d);
const lerp = (a, b, q) => a + (b - a) * q;
const eOut = (x) => 1 - Math.pow(1 - x, 3);
const eInOut = (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
const eBack = (x) => { const c1 = 2.0, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };

function el(tag, cls, html, parent, css) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html != null) e.innerHTML = html;
  if (css) Object.assign(e.style, css);
  (parent || stage).appendChild(e);
  return e;
}
const px = (v) => (typeof v === "number" ? v + "px" : v);
function place(e, x, y, w) { e.style.left = px(x); e.style.top = px(y); if (w != null) e.style.width = px(w); return e; }
function tf(e, { x = 0, y = 0, s = 1, sx = 1, sy = 1, r = 0, o = 1, ry = 0, blur = 0 } = {}) {
  e.style.transform = `perspective(1600px) translate(${x}px,${y}px) rotateY(${ry}deg) rotate(${r}deg) scale(${s * sx},${s * sy})`;
  e.style.opacity = o;
  e.style.filter = blur > 0.2 ? `blur(${blur}px)` : "none";
}
const icon = (n, size = 26) => `<svg class="i" viewBox="0 0 24 24" width="${size}" height="${size}">${ICONS[n]}</svg>`;
const inr = (n) => "₹" + Math.round(n).toLocaleString("en-IN");

// ---------- global layers ----------
const bg = el("div", "abs", "", stage, { width: W + "px", height: H + "px" });
const grid = el("div", "grid", "", bg);
const blobA = el("div", "blob", "", bg, { width: "900px", height: "900px", background: "rgba(124,58,237,.55)" });
const blobB = el("div", "blob", "", bg, { width: "700px", height: "700px", background: "rgba(167,139,250,.28)" });
const sceneLayer = el("div", "abs", "", stage, { width: W + "px", height: H + "px" });
const logoBug = el("div", "abs logo", `<span class="lime">${icon("crown", 34)}</span><span style="font-size:34px">GYMBOSS<span class="violet">_VVO</span></span>`, stage);
place(logoBug, V ? 60 : 70, V ? 70 : 52);
const slabA = el("div", "slab", "", stage, { width: W * 1.9 + "px", background: "var(--lime)", transform: "skewX(-18deg)" });
const slabB = el("div", "slab", "", stage, { width: W * 1.9 + "px", background: "var(--purple)", transform: "skewX(-18deg)" });
const progress = el("div", "abs", "", stage, { height: "8px", background: "var(--lime)", top: H - 8 + "px" });
const grain = el("div", "grain", "", stage);

const scenes = [];
function scene(start, end, build, opts = {}) {
  const root = el("div", "scene", "", sceneLayer);
  if (opts.bg) root.style.background = opts.bg;
  scenes.push({ start, end, root, upd: build(root), logo: opts.logo !== false });
}

// ---------- reusable animated parts ----------
function bgWord(root, text, y, size, speed = 60) {
  const e = el("div", "abs bgword", text, root, { fontSize: size + "px" });
  place(e, 0, y);
  return (t) => tf(e, { x: W * 0.05 - t * speed, o: clamp(t * 3) });
}

function headline(root, { x, y, size, lines, delay = 0.15, stagger = 0.12, align = "left" }) {
  const box = el("div", "abs head", "", root, { fontSize: size + "px", textAlign: align });
  place(box, x, y, align === "center" ? W - 2 * x : null);
  const words = [];
  lines.forEach(([text, cls]) => {
    const line = el("span", "line " + (cls || ""), "", box);
    text.split(" ").forEach((w) => words.push(el("span", "w", w, line)));
  });
  return (t) => words.forEach((w, i) => {
    const q = prog(t, delay + i * stagger, 0.32);
    tf(w, { y: (1 - eOut(q)) * size * 0.6, s: lerp(1.7, 1, eOut(q)), o: q > 0 ? 1 : 0, blur: (1 - q) * 10 });
  });
}

function panda(root, { src, x, bottom, h, from = "bottom", delay = 0.1, bounce = 16, flip = false }) {
  const img = el("img", "abs", null, root, { height: h + "px" });
  img.src = `assets/cut/${src}.png`;
  img.style.left = px(x);
  img.style.top = px(bottom - h);
  img.style.transformOrigin = "50% 100%";
  return (t) => {
    const q = eBack(prog(t, delay, 0.7));
    const off = 1 - q;
    const dx = from === "left" ? -W * 0.6 * off : from === "right" ? W * 0.6 * off : 0;
    const dy = from === "bottom" ? h * off : 0;
    const beat = Math.abs(Math.sin((Math.PI * (t - delay)) / BEAT));
    const live = t > delay + 0.7 ? 1 : 0;
    tf(img, { x: dx, y: dy - beat * bounce * live, sy: 1 + 0.025 * beat * live, sx: (flip ? -1 : 1) * (1 - 0.012 * beat * live), r: Math.sin(t * 2.2) * 1.5 * live, o: clamp(prog(t, delay, 0.15)) });
  };
}

function device(root, { kind, src, x, y, w, from = "right", delay = 0.25, ry = 0 }) {
  let box;
  if (kind === "browser") {
    box = el("div", "abs browser", `<div class="bar"><i></i><i></i><i></i><div class="url">GymBoss_VVO</div></div><img src="assets/screens/${src}.png">`, root);
  } else {
    box = el("div", "abs phone", `<div class="scr"><img src="assets/screens/${src}.png"></div>`, root);
  }
  place(box, x, y, w);
  return (t) => {
    const q = eOut(prog(t, delay, 0.8));
    const off = 1 - q;
    tf(box, { x: (from === "right" ? 1 : from === "left" ? -1 : 0) * W * 0.5 * off, y: (from === "bottom" ? H * 0.6 : 0) * off + Math.sin(t * 1.6) * 6, ry: ry + (from === "left" ? 25 : -25) * off, o: clamp(q * 2) });
  };
}

function chip(root, { text, ic, x, y, delay, size = 30 }) {
  const c = el("div", "abs chip", `<span class="ic">${icon(ic)}</span><span>${text}</span>`, root, { fontSize: size + "px" });
  place(c, x, y);
  return (t) => { const q = prog(t, delay, 0.45); tf(c, { s: q > 0 ? eBack(q) : 0, y: Math.sin((t + delay) * 2.4) * 8, o: q > 0 ? 1 : 0 }); };
}

function toast(root, { x, y, w, delay, amount = 2500, who = "UPI · Member payment" }) {
  const c = el("div", "abs toast", `<svg viewBox="0 0 52 52" width="96" height="96"><circle cx="26" cy="26" r="24" fill="#22C55E"/><path d="M15 27l7 7 15-16" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="40" stroke-dashoffset="40"/></svg><div><div class="t1">Payment received</div><div class="amt">₹0</div><div class="t2">${who}</div></div>`, root);
  place(c, x, y, w);
  const path = c.querySelector("path"), amt = c.querySelector(".amt");
  return (t) => {
    const q = prog(t, delay, 0.5);
    tf(c, { y: (1 - eBack(q)) * 160, s: lerp(0.7, 1, eBack(q)), o: clamp(q * 3), r: lerp(-6, -2, eOut(q)) });
    path.setAttribute("stroke-dashoffset", 40 * (1 - eOut(prog(t, delay + 0.35, 0.35))));
    amt.textContent = inr(amount * eOut(prog(t, delay + 0.2, 0.7)));
  };
}

function duesPill(root, { x, y, delay, from = 32625, to = 30125 }) {
  const c = el("div", "abs pill", `<span style="color:#F87171">${icon("wallet", 30)}</span><span>Dues pending</span><span class="num" style="font-family:'JetBrains Mono';color:var(--lime)">${inr(from)}</span>`, root, { background: "rgba(22,14,43,.85)", border: "1.5px solid rgba(167,139,250,.35)" });
  place(c, x, y);
  const num = c.querySelector(".num");
  return (t) => {
    const q = prog(t, delay, 0.4);
    tf(c, { x: (1 - eOut(q)) * -120, o: clamp(q * 2) });
    num.textContent = inr(lerp(from, to, eInOut(prog(t, delay + 0.9, 0.8))));
  };
}

function pdfCard(root, { x, y, w, delay }) {
  const rows = [["Collections", "var(--purple)", 0.92], ["Expenses", "#F59E0B", 0.55], ["Dues", "#F87171", 0.3], ["Net", "#22C55E", 0.62]];
  const c = el("div", "abs pdf", `<div class="tag">PDF</div><div style="display:flex;gap:14px;align-items:center;color:var(--purple)">${icon("file-text", 40)}<h4 style="color:#0A0712">Monthly Finance Report</h4></div><div class="sub">By transaction date · All outlets</div>` +
    rows.map(([n, col]) => `<div class="row"><span>${n}</span></div><div class="barx" data-w="1" style="background:${col}"></div>`).join(""), root);
  place(c, x, y, w);
  const bars = [...c.querySelectorAll(".barx")];
  return (t) => {
    const q = prog(t, delay, 0.6);
    tf(c, { s: lerp(0.3, 1, eBack(q)), r: lerp(-18, -4, eOut(q)), y: (1 - eOut(q)) * 120, o: clamp(q * 3) });
    bars.forEach((b, i) => { b.style.width = 100 * rows[i][2] * eOut(prog(t, delay + 0.4 + i * 0.12, 0.5)) + "%"; });
  };
}

function burst(root, { cx, cy, r }) {
  const b = el("div", "burst", "", root, { width: r * 2 + "px", height: r * 2 + "px", left: cx - r + "px", top: cy - r + "px" });
  return (t) => { b.style.transform = `rotate(${t * 18}deg) scale(${0.6 + 0.4 * eOut(prog(t, 0, 0.8))})`; };
}

const all = (fns) => (t, d) => fns.forEach((f) => f(t, d));
const L = (w, v) => (V ? v : w);

// ---------- scenes ----------
function hookScene(start, end) {
  scene(start, end, (root) => all([
    bgWord(root, "GYMBOSS GYMBOSS", L(640, 1180), L(520, 520), 90),
    burst(root, { cx: L(1440, 540), cy: L(560, 1300), r: L(620, 720) }),
    headline(root, V
      ? { x: 70, y: 210, size: 230, lines: [["Gym", ""], ["owners!", "lime"]], delay: 0.1, stagger: 0.18 }
      : { x: 130, y: 250, size: 230, lines: [["Meet", ""], ["GymBoss", "lime"]], delay: 0.15, stagger: 0.25 }),
    V ? headline(root, { x: 70, y: 700, size: 92, lines: [["Meet GymBoss", "violet"]], delay: 1.2, stagger: 0.1 })
      : headline(root, { x: 136, y: 760, size: 64, lines: [["The panda who runs your gym", "violet"]], delay: 1.6, stagger: 0.07 }),
    panda(root, V ? { src: "panda_hero", x: 150, bottom: 1880, h: 1060, delay: 0.35 } : { src: "panda_hero", x: 1060, bottom: 1060, h: 960, delay: 0.35 }),
  ]), { logo: false });
}

function featureScene(start, end, cfg) {
  scene(start, end, (root) => {
    const parts = [bgWord(root, cfg.word, cfg.wordY ?? L(700, 1500), L(420, 380))];
    if (cfg.device) parts.push(device(root, cfg.device));
    if (cfg.device2) parts.push(device(root, cfg.device2));
    parts.push(headline(root, cfg.head));
    if (cfg.panda) parts.push(panda(root, cfg.panda));
    (cfg.chips || []).forEach((c) => parts.push(chip(root, c)));
    if (cfg.toast) parts.push(toast(root, cfg.toast));
    if (cfg.dues) parts.push(duesPill(root, cfg.dues));
    if (cfg.pdf) parts.push(pdfCard(root, cfg.pdf));
    return all(parts);
  });
}

function catchScene(start, end) {
  scene(start, end, (root) => {
    const rows = [0, 1, 2, 3, 4, 5].map((i) => {
      const r = el("div", "abs marq", Array(6).fill("No excuses bro ✦ Manage grow repeat ✦").join(" "), root, { fontSize: L(150, 170) + "px", color: "transparent", WebkitTextStroke: "2px rgba(10,7,18,.25)" });
      place(r, -400, i * L(190, 330) - 60);
      return (t) => tf(r, { x: (i % 2 ? -1 : 1) * t * 140 - (i % 2 ? 0 : 900), r: -6 });
    });
    const bro = el("div", "abs head black", "No excuses,<br>bro!", root, { fontSize: L(250, 230) + "px" });
    place(bro, L(110, 70), L(200, 220));
    const words = ["Manage.", "Grow.", "Repeat."].map((w, i) => {
      const e = el("div", "abs head", w, root, { fontSize: L(210, 230) + "px", color: i === 2 ? "var(--lime)" : "#fff", WebkitTextStroke: i === 2 ? "3px #0A0712" : "0" });
      place(e, L(110, 70), L(120 + i * 220, 160 + i * 250));
      return e;
    });
    const p1 = panda(root, V ? { src: "panda_flex", x: 230, bottom: 1880, h: 900, delay: 0.1, bounce: 24 } : { src: "panda_flex", x: 1260, bottom: 1060, h: 900, delay: 0.1, bounce: 24 });
    const p2 = panda(root, V ? { src: "panda_excited", x: 260, bottom: 1880, h: 900, delay: 1.3, bounce: 40 } : { src: "panda_excited", x: 1200, bottom: 1060, h: 940, delay: 1.3, bounce: 40 });
    const imgs = root.querySelectorAll("img");
    return (t, d) => {
      rows.forEach((f) => f(t));
      const qb = prog(t, 0.25, 0.3), out = prog(t, 1.15, 0.2);
      tf(bro, { s: lerp(2.2, 1, eOut(qb)) * (1 - out * 0.3), x: Math.sin(t * 60) * 8 * (1 - prog(t, 0.55, 0.3)) * qb, o: qb > 0 ? 1 - out : 0, r: -3 });
      words.forEach((e, i) => { const q = prog(t, 1.3 + i * 0.33, 0.25); tf(e, { s: lerp(2, 1, eOut(q)), o: q > 0 ? 1 : 0, r: -3, x: Math.sin((t - 1.3 - i * 0.33) * 50) * 6 * (1 - prog(t, 1.45 + i * 0.33, 0.25)) * (q > 0 ? 1 : 0) }); });
      p1(t);
      imgs[0].style.opacity = t < 1.3 ? imgs[0].style.opacity : 0;
      p2(t);
      if (t < 1.3) imgs[1].style.opacity = 0;
    };
  }, { bg: "var(--purple)", logo: false });
}

function endScene(start, end, voDelay) {
  scene(start, end, (root) => {
    const parts = [burst(root, { cx: L(560, 540), cy: L(560, 1360), r: L(700, 760) })];
    parts.push(panda(root, V ? { src: "panda_wave", x: 200, bottom: 1880, h: 860, delay: 0.1 } : { src: "panda_wave", x: 190, bottom: 1060, h: 940, delay: 0.1 }));
    const lock = el("div", "abs", `<div class="lime" style="margin-bottom:6px">${icon("crown", L(120, 130))}</div><div class="head" style="font-size:${L(150, 150)}px">GYMBOSS<span class="violet">_VVO</span></div><div style="font:700 ${L(34, 36)}px 'Space Grotesk';letter-spacing:${L(14, 12)}px;color:#CFC6F2;margin-top:14px">MANAGE · GROW · REPEAT</div>`, root, { textAlign: L("left", "center") });
    place(lock, L(960, 0), L(150, 150), L(null, W));
    const got = el("div", "abs head lime", "GymBoss got you!", root, { fontSize: L(96, 100) + "px", textAlign: L("left", "center") });
    place(got, L(960, 0), L(610, 640), L(null, W));
    const cta = el("div", "abs", `<div class="cta">Start your free trial ${icon("trending-up", 44)}</div>`, root, { textAlign: L("left", "center") });
    place(cta, L(960, 0), L(760, 800), L(null, W));
    const feats = el("div", "abs", "Members · Fees · Attendance · Reports · Outlets · Staff", root, { font: `600 ${L(28, 30)}px 'Space Grotesk'`, color: "#A79FC7", textAlign: L("left", "center") });
    place(feats, L(964, 0), L(930, 960), L(null, W));
    return (t, d) => {
      parts.forEach((f) => f(t));
      const ql = prog(t, 0.2, 0.6);
      tf(lock, { s: lerp(1.5, 1, eBack(ql)), o: clamp(ql * 3) });
      const qg = prog(t, voDelay, 0.35);
      tf(got, { s: lerp(1.8, 1, eOut(qg)), o: qg > 0 ? 1 : 0, r: -2 });
      const qc = prog(t, voDelay + 0.7, 0.45);
      tf(cta, { s: (qc > 0 ? eBack(qc) : 0) * (1 + 0.035 * Math.abs(Math.sin((Math.PI * t) / BEAT))), o: qc > 0 ? 1 : 0 });
      tf(feats, { o: prog(t, voDelay + 1.2, 0.5), y: (1 - eOut(prog(t, voDelay + 1.2, 0.5))) * 30 });
    };
  }, { logo: false });
}

// ---------- timelines ----------
const WIDE = {
  total: 30,
  cuts: [4.0, 7.6, 10.4, 13.8, 17.0, 20.6, 25.0],
  build() {
    hookScene(0, 4.0);
    featureScene(4.0, 7.6, {
      word: "MEMBERS MEMBERS",
      head: { x: 120, y: 150, size: 132, lines: [["Add members", ""], ["in seconds", "lime"]] },
      device: { kind: "browser", src: "web_members", x: 760, y: 250, w: 1080, ry: -10 },
      panda: { src: "panda_tablet", x: 170, bottom: 1060, h: 700, from: "left", delay: 0.2 },
      chips: [
        { text: "Photo & member ID", ic: "camera", x: 600, y: 520, delay: 1.0 },
        { text: "Plans & batches", ic: "dumbbell", x: 1420, y: 170, delay: 1.3 },
        { text: "Smart search", ic: "search", x: 1380, y: 900, delay: 1.6 },
      ],
    });
    featureScene(7.6, 10.4, {
      word: "FEES & DUES",
      head: { x: 860, y: 110, size: 132, lines: [["Fees & dues.", ""], ["Tracked.", "lime"]] },
      device: { kind: "browser", src: "web_payments", x: 980, y: 430, w: 900, ry: -14, delay: 0.1 },
      panda: { src: "panda_phone", x: 90, bottom: 1060, h: 900, from: "left", delay: 0.1 },
      toast: { x: 700, y: 520, w: 620, delay: 0.55 },
      dues: { x: 720, y: 860, delay: 1.0 },
    });
    featureScene(10.4, 13.8, {
      word: "CHECK-IN RENEW",
      head: { x: 120, y: 140, size: 120, lines: [["Attendance.", ""], ["Renewals.", ""], ["Sorted.", "lime"]], stagger: 0.2 },
      device: { kind: "phone", src: "mob_attendance", x: 930, y: 120, w: 400, from: "bottom", delay: 0.15 },
      panda: { src: "panda_lifting", x: 1320, bottom: 1060, h: 760, from: "right", delay: 0.3, bounce: 26 },
      chips: [
        { text: "QR & biometric check-in", ic: "qr-code", x: 120, y: 620, delay: 1.0 },
        { text: "Expiry reminders", ic: "bell-ring", x: 120, y: 730, delay: 1.3 },
        { text: "One-tap renewals", ic: "refresh-cw", x: 120, y: 840, delay: 1.6 },
      ],
    });
    featureScene(13.8, 17.0, {
      word: "REPORTS REPORTS",
      head: { x: 120, y: 120, size: 110, lines: [["Finance reports.", ""], ["Monthly PDF in one tap.", "lime"]], stagger: 0.09 },
      device: { kind: "browser", src: "web_reports", x: 600, y: 380, w: 1000, ry: -8, delay: 0.15 },
      panda: { src: "panda_laptop", x: 40, bottom: 1060, h: 560, from: "left", delay: 0.25 },
      pdf: { x: 1360, y: 430, w: 470, delay: 1.0 },
    });
    featureScene(17.0, 20.6, {
      word: "EVERYWHERE",
      head: { x: 120, y: 130, size: 104, lines: [["All outlets. All staff.", ""], ["Web + Android + iOS", "lime"]], align: "center", stagger: 0.09 },
      device: { kind: "browser", src: "web_plans", x: 110, y: 440, w: 860, ry: 10, from: "left", delay: 0.2 },
      device2: { kind: "phone", src: "mob_manage", x: 1450, y: 400, w: 330, from: "right", delay: 0.35 },
      panda: { src: "panda_wave", x: 880, bottom: 1080, h: 640, from: "bottom", delay: 0.5 },
      chips: [
        { text: "Multiple outlets", ic: "building-2", x: 150, y: 950, delay: 1.1 },
        { text: "Staff roles & access", ic: "shield-check", x: 1280, y: 950, delay: 1.4 },
      ],
    });
    catchScene(20.6, 25.0);
    endScene(25.0, 30.0, 0.6);
  },
  vo: [["w1", 0.3], ["w2", 4.2], ["w3", 7.8], ["w4", 10.6], ["w5", 14.0], ["w6", 17.3], ["w7", 21.0], ["w8", 25.6]],
};

const VERT = {
  total: 20,
  cuts: [3.0, 6.6, 9.6, 12.8, 16.0],
  build() {
    hookScene(0, 3.0);
    featureScene(3.0, 6.6, {
      word: "FEES DUES", wordY: 1250,
      head: { x: 70, y: 200, size: 150, lines: [["Members.", ""], ["Fees. Dues.", "lime"]], stagger: 0.15 },
      device: { kind: "phone", src: "mob_manage", x: 90, y: 560, w: 520, from: "bottom", delay: 0.15 },
      panda: { src: "panda_phone", x: 520, bottom: 1880, h: 860, from: "right", delay: 0.3 },
      toast: { x: 140, y: 1180, w: 640, delay: 1.1 },
      dues: { x: 140, y: 1560, delay: 1.6 },
    });
    featureScene(6.6, 9.6, {
      word: "CHECK-IN", wordY: 1300,
      head: { x: 70, y: 200, size: 140, lines: [["Attendance.", ""], ["Renewals.", ""], ["Sorted.", "lime"]], stagger: 0.18 },
      device: { kind: "phone", src: "mob_attendance", x: 520, y: 700, w: 480, from: "right", delay: 0.15 },
      panda: { src: "panda_lifting", x: 20, bottom: 1880, h: 700, from: "left", delay: 0.3, bounce: 26 },
      chips: [
        { text: "QR check-in", ic: "qr-code", x: 70, y: 720, delay: 0.9 },
        { text: "Expiry reminders", ic: "bell-ring", x: 70, y: 830, delay: 1.15 },
        { text: "One-tap renewals", ic: "refresh-cw", x: 70, y: 940, delay: 1.4 },
      ],
    });
    featureScene(9.6, 12.8, {
      word: "REPORTS", wordY: 1250,
      head: { x: 70, y: 200, size: 140, lines: [["Reports +", ""], ["monthly PDF", "lime"]], stagger: 0.15 },
      device: { kind: "browser", src: "web_reports", x: 50, y: 560, w: 980, delay: 0.15 },
      panda: { src: "panda_laptop", x: 30, bottom: 1880, h: 620, from: "left", delay: 0.3 },
      pdf: { x: 540, y: 1120, w: 480, delay: 1.0 },
    });
    catchScene(12.8, 16.0);
    endScene(16.0, 20.0, 0.4);
  },
  vo: [["v1", 0.25], ["v2", 3.2], ["v3", 6.8], ["v4", 9.8], ["v5", 13.0], ["v6", 16.4]],
};

const TL = V ? VERT : WIDE;
TL.build();
window.TIMELINE = { total: TL.total, vo: TL.vo };

window.render = (t) => {
  blobA.style.transform = `translate(${W * 0.55 + Math.sin(t * 0.5) * 260}px, ${H * 0.1 + Math.cos(t * 0.4) * 180}px)`;
  blobB.style.transform = `translate(${-200 + Math.cos(t * 0.6) * 220}px, ${H * 0.55 + Math.sin(t * 0.45) * 200}px)`;
  grid.style.transform = `translate(${(t * 30) % 90}px, ${(t * 18) % 90}px)`;
  let logo = false;
  for (const s of scenes) {
    const on = t >= s.start && t < s.end;
    s.root.style.display = on ? "block" : "none";
    if (on) { s.upd(t - s.start, s.end - s.start); logo = s.logo; }
  }
  logoBug.style.opacity = logo ? 1 : 0;
  let xa = W * 2, xb = W * 2;
  for (const c of TL.cuts) {
    const qa = prog(t, c - 0.3, 0.55), qb = prog(t, c - 0.24, 0.55);
    if (qa > 0 && qa < 1) xa = lerp(W * 1.15, -W * 2.1, eInOut(qa));
    if (qb > 0 && qb < 1) xb = lerp(W * 1.15, -W * 2.1, eInOut(qb));
  }
  slabA.style.left = xa + "px";
  slabB.style.left = xb + "px";
  progress.style.width = (W * t) / TL.total + "px";
  const f = Math.floor(t * 30);
  grain.style.transform = `translate(${(f * 37) % 120 - 60}px, ${(f * 53) % 120 - 60}px)`;
};

window.READY = Promise.all([document.fonts.ready, ...[...document.images].map((i) => (i.complete ? 1 : new Promise((r) => { i.onload = i.onerror = r; })))]).then(() => document.fonts.ready).then(() => true);
render(0);
