import { Link } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";
import { DashboardMockup } from "./DashboardMockup";
import { usePublicConfig } from "../../hooks/usePublicConfig";
import { inr } from "../../lib/format";

export function Hero() {
  const config = usePublicConfig();
  const price = inr(config?.plan_price_inr || 999);
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-brand-soft/50 via-white to-white" data-testid="hero-section">
      <div className="pointer-events-none absolute left-1/2 top-0 h-[420px] w-[820px] -translate-x-1/2 rounded-full bg-brand/10 blur-3xl" aria-hidden="true" />
      <div className="relative mx-auto max-w-7xl px-4 pb-16 pt-14 sm:px-6 sm:pt-20 lg:px-8">
        <div className="grid items-center gap-8 lg:grid-cols-[1.05fr_0.95fr] lg:gap-10">
          {/* Text */}
          <div className="animate-fade-up text-center lg:text-left">
            <span className="inline-flex items-center gap-2 rounded-full border border-brand/20 bg-white px-4 py-1.5 text-xs font-semibold text-brand shadow-sm" data-testid="hero-badge">
              <span className="h-1.5 w-1.5 rounded-full bg-brand" />
              10-Day Free Trial · No Credit Card Required
            </span>
            <h1 className="mx-auto mt-6 max-w-xl font-display text-4xl font-extrabold leading-[1.08] tracking-tight text-slate-900 sm:text-5xl lg:mx-0 lg:text-6xl">
              Run Your <span className="text-brand">Gym</span>.<br />Not Your Spreadsheets.
            </h1>
            <p className="mx-auto mt-5 max-w-xl text-base leading-relaxed text-slate-600 sm:text-lg lg:mx-0">
              Manage members, memberships, attendance, payments, staff and WhatsApp communication from one simple platform — built for Indian gyms.
            </p>
            <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row lg:justify-start">
              <Link to="/register" data-testid="hero-cta-trial"
                    className="w-full rounded-full bg-brand px-8 py-3.5 text-base font-semibold text-white shadow-glow transition-all hover:-translate-y-0.5 hover:bg-brand-hover sm:w-auto">
                Start Your 10-Day Free Trial
              </Link>
              <a href="#how-it-works" data-testid="hero-cta-how"
                 className="w-full rounded-full border border-slate-300 bg-white px-8 py-3.5 text-base font-semibold text-slate-700 transition-colors hover:border-slate-400 hover:text-slate-900 sm:w-auto">
                See How It Works
              </a>
            </div>
            <div className="mt-7 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-slate-500 lg:justify-start">
              {["10-Day Free Trial", "No Credit Card Required", `${price}/month after trial`].map((t) => (
                <span key={t} className="inline-flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" /> {t}
                </span>
              ))}
            </div>
          </div>

          {/* Mascot */}
          <div className="relative flex justify-center lg:justify-end" data-testid="hero-mascot">
            <div className="pointer-events-none absolute inset-x-0 top-1/2 mx-auto h-[360px] w-[360px] -translate-y-1/2 rounded-full bg-brand/12 blur-3xl" aria-hidden="true" />
            <div className="relative">
              <span className="pointer-events-none absolute -bottom-2 left-1/2 h-6 w-3/4 -translate-x-1/2 rounded-[50%] bg-slate-900/12 blur-md" aria-hidden="true" />
              <img src="/mascots/hero.png" alt="GymBoss mascot — a cool panda in gym gear" loading="eager"
                   className="mascot-float relative z-10 w-[220px] drop-shadow-2xl sm:w-[280px] lg:w-[360px]" />
            </div>
          </div>
        </div>

        <div className="mt-14">
          <DashboardMockup />
        </div>
      </div>
    </section>
  );
}
