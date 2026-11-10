(() => {
  const REEL = new URLSearchParams(location.search).get("reel");
  if (!REEL) return;

  const shake = (root, hits, amp = 18) => (t) => {
    let k = 0;
    hits.forEach((h) => { const q = prog(t, h, 0.35); if (q > 0 && q < 1) k = Math.max(k, 1 - q); });
    root.style.transform = k ? `translate(${Math.sin(t * 90) * amp * k}px, ${Math.cos(t * 77) * amp * k}px) rotate(${Math.sin(t * 60) * k}deg)` : "none";
  };

  const pop = (e, t, delay, { r = 0, from = 0.4 } = {}) => {
    const q = prog(t, delay, 0.4);
    tf(e, { s: q > 0 ? lerp(from, 1, eBack(q)) : 0, o: q > 0 ? 1 : 0, r, y: Math.sin((t + delay) * 2.2) * 6 });
  };

  function bubbles(root, { msgs, x, y, gap, delay, step }) {
    const els = msgs.map(([nm, txt, tm], i) => {
      const b = el("div", "abs bub", `<div class="nm">${nm}</div>${txt}<span class="tm">${tm}</span>`, root);
      place(b, x + (i % 2) * 40, y + i * gap);
      return b;
    });
    return (t) => els.forEach((b, i) => pop(b, t, delay + i * step, { r: i % 2 ? 2 : -2 }));
  }

  function counterPill(root, { label, x, y, from, to, delay, dur = 0.9, money = true, color = "var(--lime)", ic = "wallet", icColor = "#F87171" }) {
    const c = el("div", "abs pill", `<span style="color:${icColor}">${icon(ic, 30)}</span><span>${label}</span><span class="num" style="font-family:'JetBrains Mono';color:${color}"></span>`, root, { background: "rgba(22,14,43,.88)", border: "1.5px solid rgba(167,139,250,.35)" });
    place(c, x, y);
    const num = c.querySelector(".num");
    return (t) => {
      const q = prog(t, delay, 0.4);
      tf(c, { x: (1 - eOut(q)) * -140, o: clamp(q * 2) });
      const v = lerp(from, to, eInOut(prog(t, delay + 0.3, dur)));
      num.textContent = money ? inr(v) : Math.round(v);
    };
  }

  function badChips(root, items, { x, y, gap, delay, step }) {
    const els = items.map((text, i) => {
      const c = el("div", "abs chip bad", `<span class="ic">${icon("triangle-alert")}</span><span>${text}</span>`, root, { fontSize: "34px" });
      place(c, x, y + i * gap);
      return c;
    });
    return (t) => els.forEach((c, i) => pop(c, t, delay + i * step, { r: i % 2 ? 1.5 : -1.5 }));
  }

  function bigText(root, { html, x, y, size, color = "#fff", stroke, delay, from = 2.2, r = -2, wobble = 0 }) {
    const e = el("div", "abs head", html, root, { fontSize: size + "px", color, WebkitTextStroke: stroke || "0" });
    place(e, x, y);
    return (t) => { const q = prog(t, delay, 0.3); tf(e, { s: lerp(from, 1, eOut(q)), o: q > 0 ? 1 : 0, r, x: Math.sin(t * 50) * wobble * (1 - prog(t, delay + 0.2, 0.4)) * (q > 0 ? 1 : 0) }); };
  }

  // Reel 1 — The Fee Chase
  function r1Hook(start, end) {
    scene(start, end, (root) => {
      const parts = [
        bgWord(root, "PAY UP PAY UP", 1350, 380, 80),
        panda(root, { src: "panda_angry", x: 500, bottom: 1880, h: 1020, delay: -0.35, bounce: 10 }),
        headline(root, { x: 70, y: 170, size: 96, lines: [["POV:", "lime"]], delay: -0.4 }),
        headline(root, { x: 70, y: 270, size: 150, lines: [["It's the 5th.", ""], ["Nobody paid.", "lime"]], delay: -0.6, stagger: 0.09 }),
        counterPill(root, { label: "Unpaid members", x: 70, y: 620, from: 3, to: 47, delay: 0.3, dur: 2.6, money: false, color: "#F87171", ic: "users" }),
        bubbles(root, {
          x: 50, y: 760, gap: 160, delay: 0.55, step: 0.42,
          msgs: [["RAHUL · MEMBER", "Bro, next week pakka", "9:02"], ["PRIYA · MEMBER", "Salary not credited yet", "9:14"], ["VIKRAM · MEMBER", "Paid na? (he didn't)", "9:31"], ["AMIT · MEMBER", "50% now, 50% later?", "10:05"], ["SAHIL · MEMBER", "Seen ✓✓", "11:47"]],
        }),
      ];
      const sh = shake(root, [0.55, 0.97, 1.39, 1.81, 2.23].map((x) => x + 0.05), 10);
      return (t) => { parts.forEach((f) => f(t)); sh(t); };
    }, { logo: false });
  }

  function cashScene(start, end) {
    scene(start, end, (root) => all([
      bgWord(root, "CASH CASH CASH", 1250, 400),
      burst(root, { cx: 560, cy: 1350, r: 720 }),
      headline(root, { x: 70, y: 200, size: 150, lines: [["Less chasing.", ""], ["More cash.", "lime"]], stagger: 0.14 }),
      counterPill(root, { label: "Collected", x: 70, y: 560, from: 0, to: 128500, delay: 0.5, dur: 1.4, color: "var(--lime)", ic: "indian-rupee", icColor: "#22C55E" }),
      counterPill(root, { label: "Dues pending", x: 70, y: 680, from: 32625, to: 0, delay: 0.8, dur: 1.4, color: "#F87171" }),
      panda(root, { src: "panda_cash", x: 200, bottom: 1880, h: 1040, delay: 0.25, bounce: 22 }),
    ]));
  }

  // Reel 2 — The Money Leak
  function r2Hook(start, end) {
    scene(start, end, (root) => {
      const vign = el("div", "abs", "", root, { width: W + "px", height: H + "px", background: "radial-gradient(circle at 50% 45%, transparent 35%, rgba(239,68,68,.5) 100%)" });
      const parts = [
        bgWord(root, "LEAK LEAK LEAK", 1300, 400, 80),
        panda(root, { src: "panda_shocked", x: 250, bottom: 1880, h: 1000, delay: -0.35, bounce: 8 }),
        headline(root, { x: 70, y: 170, size: 110, lines: [["Your gym is losing", ""]], delay: -0.4, stagger: 0.06 }),
        headline(root, { x: 70, y: 610, size: 100, lines: [["Every. Single. Month.", "lime"]], delay: 1.15, stagger: 0.2 }),
      ];
      const big = el("div", "abs head", "", root, { fontSize: "255px", color: "#FF4D4D", textShadow: "0 0 60px rgba(255,77,77,.55)" });
      place(big, 60, 290);
      const math = el("div", "abs pill", `<span style="color:#F87171">${icon("users", 30)}</span><span>20 late payers × ₹2,000</span>`, root, { background: "rgba(43,10,18,.9)", border: "1.5px solid rgba(248,113,113,.6)", fontSize: "34px" });
      place(math, 70, 760);
      const sh = shake(root, [1.1], 26);
      return (t) => {
        parts.forEach((f) => f(t));
        vign.style.opacity = 0.55 + 0.45 * Math.abs(Math.sin(t * 4));
        const q = eOut(prog(t, 0, 1.1));
        big.textContent = inr(lerp(9000, 40000, q));
        tf(big, { s: 1 + 0.06 * (1 - prog(t, 1.1, 0.4)) * (t > 1.1 ? 1 : 0), r: -2, o: 1 });
        pop(math, t, 2.0, { r: -1 });
        sh(t);
      };
    }, { logo: false });
  }

  function leakScene(start, end) {
    scene(start, end, (root) => all([
      bgWord(root, "WHERE? WHERE?", 1300, 400),
      panda(root, { src: "panda_confused", x: 430, bottom: 1880, h: 900, from: "right", delay: 0.1 }),
      headline(root, { x: 70, y: 200, size: 150, lines: [["Where's it", ""], ["leaking?", "lime"]], stagger: 0.14 }),
      badChips(root, ["Missed renewals", "Expired, still training", "Dues nobody tracked", "Cash never recorded"], { x: 60, y: 580, gap: 112, delay: 0.5, step: 0.45 }),
    ]));
  }

  // Reel 3 — Midnight Register
  function r3Hook(start, end) {
    scene(start, end, (root) => {
      const papers = [...Array(9)].map((_, i) => {
        const p = el("div", "abs paper", "", root, { width: "120px", height: "150px" });
        place(p, 40 + ((i * 131) % 1000), -200);
        return p;
      });
      const parts = [
        bgWord(root, "11:47 PM 11:47 PM", 1250, 380, 60),
        panda(root, { src: "panda_tired", x: 120, bottom: 1840, h: 900, delay: -0.35, bounce: 4 }),
        headline(root, { x: 70, y: 180, size: 140, lines: [["Me doing gym", ""], ["accounts at", ""], ["midnight", "lime"]], delay: -0.6, stagger: 0.07 }),
      ];
      const clock = el("div", "abs pill", `<span class="violet">${icon("moon", 34)}</span><span class="tm" style="font-family:'JetBrains Mono';font-size:56px">11:47 PM</span>`, root, { background: "rgba(22,14,43,.88)", border: "1.5px solid rgba(167,139,250,.35)" });
      place(clock, 70, 640);
      const zz = el("div", "abs head violet", "z z Z", root, { fontSize: "90px" });
      place(zz, 760, 820);
      const tm = clock.querySelector(".tm");
      return (t) => {
        parts.forEach((f) => f(t));
        papers.forEach((p, i) => {
          const life = ((t * 0.55 + i * 0.29) % 1.4) / 1.4;
          tf(p, { y: life * (H + 400), x: Math.sin(t * 2 + i) * 60, r: t * 70 * (i % 2 ? 1 : -1) + i * 30, o: 0.85 });
        });
        pop(clock, t, 0.3, { r: -2 });
        tm.textContent = `11${Math.floor(t * 2) % 2 ? " " : ":"}${t < 2.6 ? "47" : "48"} PM`;
        tf(zz, { y: -((t * 60) % 120), o: 0.4 + 0.6 * Math.abs(Math.sin(t * 2.5)), r: -8 });
      };
    }, { logo: false, bg: "#06041A" });
  }

  function messScene(start, end) {
    scene(start, end, (root) => {
      const parts = [
        bgWord(root, "CASH? UPI?", 1300, 400),
        panda(root, { src: "panda_confused", x: 470, bottom: 1880, h: 900, from: "right", delay: 0.05 }),
        headline(root, { x: 70, y: 200, size: 124, lines: [["Cash here.", ""], ["UPI there.", ""], ["Nothing adds up.", "lime"]], stagger: 0.12 }),
      ];
      const rc = [["Cash", "₹2,500", 80, 760, -8], ["UPI", "₹1,800", 120, 960, 6], ["Pending", "₹3,000", 60, 1160, -4], ["Total", "₹??,???", 100, 1360, 5]].map(([lb, v, x, y, r]) => {
        const c = el("div", "abs rcpt", `<div class="lb">${lb}</div>${v}<span class="q">?</span>`, root);
        place(c, x, y);
        return [c, r];
      });
      return (t) => { parts.forEach((f) => f(t)); rc.forEach(([c, r], i) => pop(c, t, 0.6 + i * 0.4, { r })); };
    });
  }

  function foundScene(start, end) {
    scene(start, end, (root) => all([
      burst(root, { cx: 540, cy: 1300, r: 760 }),
      bigText(root, { html: "Then I found", x: 70, y: 230, size: 130, delay: 0.05, from: 1.6 }),
      bigText(root, { html: "GymBoss!", x: 60, y: 380, size: 270, color: "var(--lime)", stroke: "4px #0A0712", delay: 0.45, wobble: 10 }),
      panda(root, { src: "panda_excited", x: 170, bottom: 1880, h: 1040, delay: 0.3, bounce: 40 }),
    ]), { bg: "var(--purple)", logo: false });
  }

  const REELS = {
    1: {
      name: "GymBoss_Reel1_FeeChase_9x16",
      total: 20.6,
      cuts: [4.0, 8.0, 12.0, 16.0],
      build() {
        r1Hook(0, 4.0);
        featureScene(4.0, 8.0, {
          word: "DUES DUES", wordY: 1250,
          head: { x: 70, y: 200, size: 150, lines: [["Every due.", ""], ["One list.", "lime"]], stagger: 0.15 },
          device: { kind: "phone", src: "mob_manage", x: 90, y: 560, w: 520, from: "bottom", delay: 0.15 },
          panda: { src: "panda_phone", x: 520, bottom: 1880, h: 860, from: "right", delay: 0.3 },
          dues: { x: 140, y: 1560, delay: 1.0 },
        });
        featureScene(8.0, 12.0, {
          word: "REMIND RENEW", wordY: 1300,
          head: { x: 70, y: 200, size: 140, lines: [["Remind.", ""], ["Renew.", ""], ["Collect.", "lime"]], stagger: 0.18 },
          device: { kind: "phone", src: "mob_attendance", x: 540, y: 660, w: 460, from: "right", delay: 0.15 },
          chips: [
            { text: "Expiry reminders", ic: "bell-ring", x: 60, y: 700, delay: 0.8 },
            { text: "One-tap renewals", ic: "refresh-cw", x: 60, y: 810, delay: 1.05 },
          ],
          toast: { x: 60, y: 1320, w: 660, delay: 1.5 },
        });
        cashScene(12.0, 16.0);
        endScene(16.0, 20.6, 0.4);
      },
      vo: [["r1a", 0.15], ["sfx_pop", 0.55], ["sfx_pop", 0.97], ["sfx_pop", 1.39], ["sfx_pop", 1.81], ["sfx_pop", 2.23], ["r1b", 4.2], ["r1c", 8.2], ["sfx_ching", 9.75], ["r1d", 12.2], ["sfx_ching", 12.9], ["r1e", 16.4]],
    },
    2: {
      name: "GymBoss_Reel2_MoneyLeak_9x16",
      total: 20.6,
      cuts: [4.0, 8.0, 12.0, 16.0],
      build() {
        r2Hook(0, 4.0);
        leakScene(4.0, 8.0);
        featureScene(8.0, 12.0, {
          word: "FLAGGED", wordY: 1250,
          head: { x: 70, y: 200, size: 140, lines: [["Every expiry.", ""], ["Flagged.", "lime"]], stagger: 0.15 },
          device: { kind: "phone", src: "mob_manage", x: 70, y: 560, w: 500, from: "bottom", delay: 0.15 },
          panda: { src: "panda_tablet", x: 540, bottom: 1880, h: 800, from: "right", delay: 0.3 },
          chips: [
            { text: "Expiring this week", ic: "calendar-clock", x: 540, y: 600, delay: 0.9, size: 28 },
            { text: "Dues with amounts", ic: "wallet", x: 540, y: 705, delay: 1.15, size: 28 },
            { text: "Auto reminders", ic: "bell-ring", x: 540, y: 810, delay: 1.4, size: 28 },
          ],
        });
        featureScene(12.0, 16.0, {
          word: "REPORTS", wordY: 1250,
          head: { x: 70, y: 200, size: 140, lines: [["Every rupee.", ""], ["Accounted.", "lime"]], stagger: 0.15 },
          device: { kind: "browser", src: "web_reports", x: 50, y: 560, w: 980, delay: 0.15 },
          panda: { src: "panda_laptop", x: 30, bottom: 1880, h: 620, from: "left", delay: 0.3 },
          pdf: { x: 540, y: 1120, w: 480, delay: 1.0 },
        });
        endScene(16.0, 20.6, 0.4);
      },
      vo: [["r2a", 0.15], ["sfx_boom", 1.1], ["r2b", 4.2], ["sfx_pop", 4.5], ["sfx_pop", 4.95], ["sfx_pop", 5.4], ["sfx_pop", 5.85], ["r2c", 8.2], ["r2d", 12.2], ["r2e", 16.4]],
    },
    3: {
      name: "GymBoss_Reel3_MidnightRegister_9x16",
      total: 21.4,
      cuts: [4.0, 7.0, 9.6, 13.2, 16.8],
      build() {
        r3Hook(0, 4.0);
        messScene(4.0, 7.0);
        foundScene(7.0, 9.6);
        featureScene(9.6, 13.2, {
          word: "ONE APP", wordY: 1300,
          head: { x: 70, y: 200, size: 140, lines: [["Members.", ""], ["Attendance.", ""], ["Fees.", "lime"]], stagger: 0.15 },
          device: { kind: "phone", src: "mob_home", x: 540, y: 700, w: 460, from: "right", delay: 0.15 },
          panda: { src: "panda_lifting", x: 20, bottom: 1880, h: 660, from: "left", delay: 0.3, bounce: 26 },
          chips: [
            { text: "QR check-in", ic: "qr-code", x: 60, y: 720, delay: 0.8 },
            { text: "Plans & batches", ic: "dumbbell", x: 60, y: 830, delay: 1.05 },
            { text: "Fees & dues", ic: "indian-rupee", x: 60, y: 940, delay: 1.3 },
          ],
        });
        featureScene(13.2, 16.8, {
          word: "BED BY 10", wordY: 1250,
          head: { x: 70, y: 200, size: 140, lines: [["Finance PDF.", ""], ["Bed by 10.", "lime"]], stagger: 0.15 },
          device: { kind: "browser", src: "web_finance", x: 50, y: 560, w: 980, delay: 0.15 },
          panda: { src: "panda_laptop", x: 30, bottom: 1880, h: 620, from: "left", delay: 0.3 },
          pdf: { x: 540, y: 1120, w: 480, delay: 0.9 },
        });
        endScene(16.8, 21.4, 0.4);
      },
      vo: [["r3a", 0.15], ["r3b", 4.15], ["sfx_pop", 4.6], ["sfx_pop", 5.0], ["sfx_pop", 5.4], ["sfx_pop", 5.8], ["sfx_scratch", 6.85], ["r3c", 7.2], ["r3d", 9.8], ["r3e", 13.4], ["r3f", 17.2]],
    },
  };

  window.REEL_TL = () => REELS[REEL];
})();
