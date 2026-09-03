import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { MarketingNavbar } from "../components/marketing/Navbar";
import { Hero } from "../components/marketing/Hero";
import { Features } from "../components/marketing/Features";
import { HowItWorks } from "../components/marketing/HowItWorks";
import { Pricing } from "../components/marketing/Pricing";
import { Faq } from "../components/marketing/Faq";
import { FinalCta } from "../components/marketing/FinalCta";
import { MarketingFooter } from "../components/marketing/Footer";
import { FloatingWhatsApp } from "../components/marketing/FloatingWhatsApp";
import { useAuth } from "../contexts/AuthContext";

export default function Landing() {
  const { status } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    document.documentElement.classList.remove("dark");
  }, []);

  useEffect(() => {
    if (status === "authed") navigate("/app", { replace: true });
  }, [status, navigate]);

  return (
    <div className="min-h-screen bg-white" data-testid="landing-page">
      <MarketingNavbar />
      <Hero />
      <Features />
      <HowItWorks />
      <Pricing />
      <Faq />
      <FinalCta />
      <MarketingFooter />
      <FloatingWhatsApp />
    </div>
  );
}
