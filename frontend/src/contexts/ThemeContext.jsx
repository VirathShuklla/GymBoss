import { createContext, useContext, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

const ThemeContext = createContext({ theme: "system", setTheme: () => {} });

function applyTheme(theme, forceLight) {
  const root = document.documentElement;
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const dark = !forceLight && (theme === "dark" || (theme === "system" && prefersDark));
  root.classList.toggle("dark", dark);
}

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(() => localStorage.getItem("gb-theme") || "system");
  const { pathname } = useLocation();
  const forceLight = pathname === "/";

  useEffect(() => {
    applyTheme(theme, forceLight);
    localStorage.setItem("gb-theme", theme);
    if (theme === "system" && !forceLight) {
      const mq = window.matchMedia("(prefers-color-scheme: dark)");
      const handler = () => applyTheme("system", false);
      mq.addEventListener("change", handler);
      return () => mq.removeEventListener("change", handler);
    }
  }, [theme, forceLight]);

  const setTheme = (t) => setThemeState(t);

  return <ThemeContext.Provider value={{ theme, setTheme }}>{children}</ThemeContext.Provider>;
}

export const useTheme = () => useContext(ThemeContext);
