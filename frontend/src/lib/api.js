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

// Store apps identify themselves; native (Capacitor) builds use Bearer tokens instead of cross-site cookies.
api.interceptors.request.use((config) => {
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
    if (native && res.data?.tokens) saveTokens(res.data.tokens);
    return res;
  },
  async (error) => {
    const original = error.config;
    const isAuthCall = original?.url?.startsWith("/auth/");
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
