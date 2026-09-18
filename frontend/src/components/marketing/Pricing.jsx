import { Link } from "react-router-dom";
import { Check, Smartphone } from "lucide-react";
import { usePublicConfig } from "../../hooks/usePublicConfig";
import { inr } from "../../lib/format";

const INCLUDED = [
  "Unlimited members",
  "Membership & plan management",
  "Attendance tracking",
  "Payment tracking & reminders",
  "Enquiries & lead follow-ups",
  "Announcements via WhatsApp",
  "Staff & role management",
  "Multi-outlet support",
  "Reports & exports",
  "Dedicated support",
];

export function Pricing() {
  const config = usePublicConfig();
  const hasStoreLinks = config?.play_store_url || config?.app_store_url;
  return (
    <section id="pricing" className="relative overflow-hidden bg-white py-20 sm:py-28" data-testid="pricing-section">
      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="font-display text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
            Start Your <span className="text-brand">Free Trial</span>
          </h2>
          <p className="mt-4 text-base text-slate-600 sm:text-lg">
            Try GymBoss_VVO completely free for 10 days. No credit card required.
          </p>
        </div>
        <div className="relative mx-auto mt-14 max-w-md" data-testid="pricing-card">
          <img src="/mascots/peek.png" alt="" aria-hidden="true" data-testid="pricing-mascot"
               className="mascot-float pointer-events-none absolute -top-12 right-3 z-20 w-24 drop-shadow-xl sm:right-6 sm:w-28" />
          <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-lift">
            <div className="bg-gradient-to-br from-brand to-[#5B21B6] px-8 py-8 text-center text-white">
              <span className="inline-block rounded-full bg-white/20 px-3.5 py-1 text-xs font-bold uppercase tracking-wide">
                10-Day Free Trial
              </span>
              <p className="mt-4 font-display text-xl font-bold">Experience Full Access</p>
              <p className="mt-2 font-display text-5xl font-extrabold tracking-tight">
                FREE <span className="text-base font-semibold opacity-90">for 10 days</span>
              </p>
              <p className="mt-2 text-sm opacity-90">No credit card required</p>
            </div>
            <div className="px-8 py-7">
              <p className="text-center text-sm text-slate-500">
                Then just <span className="font-num text-lg font-bold text-slate-900">{inr(config?.plan_price_inr || 999)}</span>/month after the trial
              </p>
              <ul className="mt-6 space-y-3">
                {INCLUDED.map((f) => (
                  <li key={f} className="flex items-start gap-2.5 text-sm text-slate-700">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" strokeWidth={3} />
                    {f}
                  </li>
                ))}
              </ul>
              <Link to="/register" data-testid="pricing-cta"
                    className="mt-8 block rounded-xl bg-brand py-3.5 text-center text-base font-semibold text-white transition-colors hover:bg-brand-hover">
                Start Free Trial
              </Link>
              {!hasStoreLinks && (
                <p className="mt-4 flex items-center justify-center gap-1.5 text-center text-xs text-slate-400">
                  <Smartphone className="h-3.5 w-3.5" /> Android & iOS apps coming soon — the web app works everywhere today.
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
