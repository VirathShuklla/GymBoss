import axios from "axios";
import { getPlatform, isNative } from "./inApp";

const api = axios.create({
  baseURL: `${process.env.REACT_APP_BACKEND_URL}/api`,
  withCredentials: true,
});

let refreshing = null;
const platform = getPlatform();
const native = isNative();
const TK = "gb-tokens";
const readTokens = () => { try { return JSON.parse(localStorage.getItem(TK)) || {}; } catch (e) { return {}; } };
const saveTokens = (t) => localStorage.setItem(TK, JSON.stringify({ ...readTokens(), ...t }));

// Money writes carry an Idempotency-Key that is reused when the same request is retried, so a lost
// response or double tap never records twice. The key is dropped once the server confirms success.
const IDEM_ROUTES = [/^post \/members$/, /^post \/members\/[^/]+\/renew$/, /^post \/payments$/, /^delete \/payments\/[^/]+$/];
const pendingKeys = new Map();
const newKey = () => (window.crypto?.randomUUID ? window.crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`);
const idemScope = (config) => {
  const route = `${(config.method || "get").toLowerCase()} ${(config.url || "").split("?")[0]}`;
  return IDEM_ROUTES.some((r) => r.test(route)) ? `${route} ${typeof config.data === "string" ? config.data : JSON.stringify(config.data ?? null)}` : null;
};

// Store apps identify themselves; native (Capacitor) builds use Bearer tokens instead of cross-site cookies.
api.interceptors.request.use((config) => {
  const scope = idemScope(config);
  if (scope && !config.headers["Idempotency-Key"]) {
    if (!pendingKeys.has(scope)) pendingKeys.set(scope, newKey());
    config.headers["Idempotency-Key"] = pendingKeys.get(scope);
    config._idemScope = scope;
  }
  if (platform !== "web") config.headers["X-Client-Platform"] = platform;
  if (native) {
    if (config.url === "/auth/logout") localStorage.removeItem(TK);
    const { access_token } = readTokens();
    if (access_token && !config.headers.Authorization) config.headers.Authorization = `Bearer ${access_token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => {
    if (res.config?._idemScope) pendingKeys.delete(res.config._idemScope);
    if (native && res.data?.tokens) saveTokens(res.data.tokens);
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
