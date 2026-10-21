import { SecureStorage } from "@aparajita/capacitor-secure-storage";
import { isNative } from "./inApp";

// Native (Capacitor) Bearer tokens live in the OS keychain/keystore, cached in memory for request headers.
const KEY = "gb-tokens";
let cache = {};

export const tokensReady = !isNative() ? Promise.resolve() : (async () => {
  try {
    const legacy = localStorage.getItem(KEY);
    if (legacy) {
      cache = JSON.parse(legacy) || {};
      await SecureStorage.set(KEY, JSON.stringify(cache));
      localStorage.removeItem(KEY);
      return;
    }
    const stored = await SecureStorage.get(KEY);
    cache = stored ? (typeof stored === "string" ? JSON.parse(stored) : stored) : {};
  } catch (e) {
    cache = {};
  }
})();

export const readTokens = () => cache;

export async function saveTokens(t) {
  cache = { ...cache, ...t };
  try { await SecureStorage.set(KEY, JSON.stringify(cache)); } catch (e) { /* keychain unavailable */ }
}

export async function clearTokens() {
  cache = {};
  try { await SecureStorage.remove(KEY); } catch (e) { /* nothing stored */ }
}
