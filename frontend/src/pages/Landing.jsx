import { lazy, Suspense, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { MarketingNavbar } from "../components/marketing/Navbar";
import { Hero } from "../components/marketing/Hero";
import { useAuth } from "../contexts/AuthContext";
import { track } from "../lib/track";

const BelowFold = lazy(() => import("../components/marketing/BelowFold"));

export default function Landing() {
  const { status } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    document.documentElement.classList.remove("dark");
    track("landing_visit", {}, { oncePerSession: true });
  }, []);

  useEffect(() => {
    if (status === "authed") navigate("/app", { replace: true });
  }, [status, navigate]);

  useEffect(() => {
    if (!window.location.hash) return;
    const t = setTimeout(() => document.querySelector(window.location.hash)?.scrollIntoView(), 400);
    return () => clearTimeout(t);
  }, []);

  return (
    <div className="min-h-screen bg-white" data-testid="landing-page">
      <MarketingNavbar />
      <Hero />
      <Suspense fallback={<div className="h-screen" />}>
        <BelowFold />
      </Suspense>
    </div>
  );
}
