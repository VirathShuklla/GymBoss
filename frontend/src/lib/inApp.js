const KEY = "gb-in-app";

// Set at build time for Capacitor store builds (yarn build:store).
export const STORE_BUILD = process.env.REACT_APP_STORE_BUILD === "true";

export const isNative = () => typeof window !== "undefined" && !!window.Capacitor?.isNativePlatform?.();

// True when running inside the Play Store / App Store builds (Capacitor or TWA wrapper).
export function isInApp() {
  if (typeof window === "undefined") return false;
  if (STORE_BUILD || isNative()) return true;
  const p = new URLSearchParams(window.location.search);
  if (p.get("app") === "1" || p.get("src") === "play" || document.referrer.startsWith("android-app://")) {
    try { localStorage.setItem(KEY, "1"); } catch (e) { /* storage blocked */ }
  }
  try { return localStorage.getItem(KEY) === "1"; } catch (e) { return false; }
}

// "web" | "android_store" | "ios_store" — sent to the backend as X-Client-Platform.
export function getPlatform() {
  if (isNative()) return window.Capacitor.getPlatform() === "ios" ? "ios_store" : "android_store";
  if (!isInApp()) return "web";
  return /iPhone|iPad|iPod/i.test(navigator.userAgent) ? "ios_store" : "android_store";
}

// Routes that sell or show pricing; never reachable inside store builds.
export const STORE_BLOCKED = /^\/($|pricing|billing|app\/subscription)/;
