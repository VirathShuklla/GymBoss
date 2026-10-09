// First-party conversion tracking (events are stored in GymBoss and shown in Super Admin).
const VID = "gb_vid";

export function visitorId() {
  let v = localStorage.getItem(VID);
  if (!v) {
    v = (window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`);
    localStorage.setItem(VID, v);
  }
  return v;
}

function firstTouch() {
  const p = new URLSearchParams(window.location.search);
  const cur = { utm_source: p.get("utm_source"), utm_medium: p.get("utm_medium"), utm_campaign: p.get("utm_campaign") };
  if (cur.utm_source) {
    localStorage.setItem("gb_utm", JSON.stringify(cur));
    return cur;
  }
  try { return JSON.parse(localStorage.getItem("gb_utm")) || {}; } catch { return {}; }
}

export function track(event, props = {}, { oncePerSession = false } = {}) {
  try {
    if (oncePerSession) {
      const k = `gb_ev_${event}`;
      if (sessionStorage.getItem(k)) return;
      sessionStorage.setItem(k, "1");
    }
    const ref = document.referrer && !document.referrer.includes(window.location.host) ? document.referrer : null;
    const body = {
      event, visitor_id: visitorId(), path: window.location.pathname, referrer: ref,
      device: window.innerWidth < 768 ? "mobile" : "desktop", props, ...firstTouch(),
    };
    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/events`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
      keepalive: true, credentials: "include",
    }).catch(() => {});
  } catch { /* tracking must never break the app */ }
}

// WhatsApp opens happen through links and window.open across many screens; catch them in one place.
export function installWhatsAppTracking() {
  if (window.__gbWa) return;
  window.__gbWa = true;
  const fire = (u) => {
    if (!/wa\.me|whatsapp\.com/.test(String(u || ""))) return;
    const path = window.location.pathname;
    if (/^\/(app|m)(\/|$)/.test(path)) track("whatsapp_used", { screen: path });
    else if (path === "/") track("demo_click", { via: "whatsapp" });
  };
  const orig = window.open;
  window.open = function (u, ...rest) { fire(u); return orig.call(window, u, ...rest); };
  document.addEventListener("click", (e) => { const a = e.target.closest?.("a[href]"); if (a) fire(a.href); }, true);
}
