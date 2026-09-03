import { useEffect, useState } from "react";
import api from "../lib/api";

export function usePublicConfig() {
  const [config, setConfig] = useState(null);
  useEffect(() => {
    api.get("/public/config").then(({ data }) => setConfig(data)).catch(() => setConfig({}));
  }, []);
  return config;
}

export const waLink = (number, text) =>
  `https://wa.me/${String(number || "").replace(/\D/g, "")}${text ? `?text=${encodeURIComponent(text)}` : ""}`;
