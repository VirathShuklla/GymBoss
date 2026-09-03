import { createContext, useContext, useEffect, useState, useCallback } from "react";
import api from "../lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [state, setState] = useState({ status: "loading", user: null, organisation: null, outlets: [], subscription: null });

  const reload = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setState({ status: "authed", user: data.user, organisation: data.organisation, outlets: data.outlets || [], subscription: data.subscription });
    } catch {
      setState({ status: "guest", user: null, organisation: null, outlets: [], subscription: null });
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const login = async (identifier, password) => {
    await api.post("/auth/login", { identifier, password });
    await reload();
  };

  const register = async (payload) => {
    await api.post("/auth/register", payload);
    await reload();
  };

  const logout = async () => {
    try {
      await api.post("/auth/logout");
    } finally {
      setState({ status: "guest", user: null, organisation: null, outlets: [], subscription: null });
    }
  };

  return (
    <AuthContext.Provider value={{ ...state, reload, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
