import axios from "axios";
import { getPlatform, isNative } from "./inApp";
import { tokensReady, readTokens, saveTokens, clearTokens } from "./nativeTokens";

const api = axios.create({
  baseURL: `${process.env.REACT_APP_BACKEND_URL}/api`,
  withCredentials: true,
});

let refreshing = null;
const platform = getPlatform();
const native = isNative();

// Money writes carry an Idempotency-Key that is reused when the same request is retried, so a lost
// response, double tap or page reload never records twice. Only a hash of the request is stored on the
// device (no member details). A pending key is discarded only after the server confirms the outcome.
const IDEM_ROUTES = [/^post \/members$/, /^post \/members\/[^/]+\/renew$/, /^post \/payments$/, /^delete \/payments\/[^/]+$/];
const IDEM_STORE = "gb-idem";
const UNKNOWN_GRACE = 10 * 60 * 1000;
const hashScope = (s) => {
  let a = 5381, b = 52711;
  for (let i = 0; i < s.length; i += 1) { const c = s.charCodeAt(i); a = (a * 33) ^ c; b = (b * 31) ^ c; }
  return `h${(a >>> 0).toString(36)}${(b >>> 0).toString(36)}${s.length.toString(36)}`;
};
const loadKeys = () => {
  try {
    const all = JSON.parse(localStorage.getItem(IDEM_STORE)) || {};
    return Object.fromEntries(Object.entries(all).map(([s, v]) => [s.startsWith("h") && !s.includes(" ") ? s : hashScope(s), v]));
  } catch (e) { return {}; }
};
const storeKeys = (keys) => { try { localStorage.setItem(IDEM_STORE, JSON.stringify(keys)); } catch (e) { /* storage full/blocked */ } };
const pendingKey = (scope) => {
  const keys = loadKeys();
  if (!keys[scope]) { keys[scope] = { k: newKey(), t: Date.now() }; storeKeys(keys); }
  return keys[scope].k;
};
const resolveKey = (scope) => { const keys = loadKeys(); delete keys[scope]; storeKeys(keys); };
const newKey = () => (window.crypto?.randomUUID ? window.crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`);
const idemScope = (config) => {
  const route = `${(config.method || "get").toLowerCase()} ${(config.url || "").split("?")[0]}`;
  return IDEM_ROUTES.some((r) => r.test(route)) ? hashScope(`${route} ${typeof config.data === "string" ? config.data : JSON.stringify(config.data ?? null)}`) : null;
};

// Ask the server about each pending key: "completed" means it was recorded (drop the key); "unknown" after the
// grace period means the transaction never committed, so nothing was recorded and the key can go.
export async function reconcilePendingKeys() {
  const keys = loadKeys();
  storeKeys(keys);
  for (const [scope, v] of Object.entries(keys)) {
    try {
      const { data } = await api.get(`/idempotency/${encodeURIComponent(v.k)}`);
      if (data.status === "completed" || Date.now() - v.t > UNKNOWN_GRACE) resolveKey(scope);
    } catch (e) { /* offline or signed out: keep the key */ }
  }
}

// Store apps identify themselves; native (Capacitor) builds use Bearer tokens (kept in secure storage).
api.interceptors.request.use(async (config) => {
  const scope = idemScope(config);
  if (scope && !config.headers["Idempotency-Key"]) {
    config.headers["Idempotency-Key"] = pendingKey(scope);
    config._idemScope = scope;
  }
  if (platform !== "web") config.headers["X-Client-Platform"] = platform;
  if (native) {
    await tokensReady;
    if (config.url === "/auth/logout") await clearTokens();
    const { access_token } = readTokens();
    if (access_token && !config.headers.Authorization) config.headers.Authorization = `Bearer ${access_token}`;
  }
  return config;
});

api.interceptors.response.use(
  async (res) => {
    if (res.config?._idemScope) resolveKey(res.config._idemScope);
    if (native && res.data?.tokens) await saveTokens(res.data.tokens);
    return res;
  },
  async (error) => {
    const original = error.config;
    const isAuthCall = /^\/auth\/(login|refresh|register|logout|forgot-password|reset-password)/.test(original?.url || "");
    if (error.response?.status === 401 && !isAuthCall && !original._retried) {
      original._retried = true;
      try {
        const body = native ? { refresh_token: readTokens().refresh_token } : undefined;
        refreshing = refreshing || api.post("/auth/refresh", body).finally(() => (refreshing = null));
        if (native) delete original.headers.Authorization;
        await refreshing;
        return api(original);
      } catch {
        return Promise.reject(error);
      }
    }
    return Promise.reject(error);
  }
);

export function apiError(err, fallback = "Something went wrong. Please try again.") {
  const detail = err?.response?.data?.detail;
  if (!detail) return err?.message || fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((e) => e?.msg || JSON.stringify(e)).join(" ");
  return detail?.msg || String(detail);
}

export default api;
