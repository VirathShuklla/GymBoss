const KEY = "gb-in-app";

// True when running inside the Play Store (TWA) / App Store (Capacitor) wrappers.
export function isInApp() {
  if (typeof window === "undefined") return false;
  if (window.Capacitor?.isNativePlatform?.()) return true;
  const p = new URLSearchParams(window.location.search);
  if (p.get("app") === "1" || document.referrer.startsWith("android-app://")) {
    try { localStorage.setItem(KEY, "1"); } catch (e) { /* storage blocked */ }
  }
  try { return localStorage.getItem(KEY) === "1"; } catch (e) { return false; }
}
