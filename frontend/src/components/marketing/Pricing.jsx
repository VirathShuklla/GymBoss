import { Link } from "react-router-dom";
import { Check, Smartphone } from "lucide-react";
import { usePublicConfig } from "../../hooks/usePublicConfig";
import { inr } from "../../lib/format";

const INCLUDED = [
  "Unlimited members",
  "Membership & plan management",
  "QR & biometric attendance",
  "Payment tracking, reminders & PDF receipts",
  "Enquiries & lead follow-ups",
  "Announcements via WhatsApp",
  "Staff & role management",
  "Multi-outlet support",
  "Reports & exports",
  "Dedicated support",
];
const per = (m) => (m === 1 ? "month" : m === 12 ? "year" : `${m} months`);

function PlanCard({ p, featured }) {
  return (
    <div className={`relative flex flex-col rounded-2xl border bg-white p-7 ${featured ? "border-brand shadow-lift" : "border-slate-200"}`} data-testid={`pricing-plan-${p.id}`}>
      {(p.offer_label || p.save_pct > 0) && (
        <span className="absolute -top-3 left-7 rounded-full bg-emerald-500 px-3 py-1 text-[11px] font-bold uppercase tracking-wide text-white" data-testid={`pricing-offer-${p.id}`}>
          {p.offer_label || `Save ${p.save_pct}%`}
        </span>
      )}
      <p className="font-display text-lg font-bold text-slate-900">{p.name}</p>
      <div className="mt-3 flex items-baseline gap-2">
        <span className="font-num text-4xl font-extrabold tracking-tight text-slate-900" data-testid={`pricing-price-${p.id}`}>{inr(p.effective_price)}</span>
        <span className="text-sm text-slate-500">/{per(p.months)}</span>
      </div>
      <p className="mt-1 h-5 text-sm text-slate-500">
        {p.offer_price && <span className="font-num mr-2 line-through">{inr(p.price)}</span>}
        {p.months > 1 && `${inr(p.per_month)}/month`}
      </p>
      <Link to="/register" data-testid={`pricing-cta-${p.id}`}
        className={`mt-6 block rounded-xl py-3 text-center text-sm font-semibold transition-colors ${featured ? "bg-brand text-white hover:bg-brand-hover" : "border border-slate-300 text-slate-900 hover:bg-slate-50"}`}>
        Start 10-Day Free Trial
      </Link>
    </div>
  );
}

export function Pricing() {
  const config = usePublicConfig();
  const hasStoreLinks = config?.play_store_url || config?.app_store_url;
  const plans = config?.pricing_plans || [];
  const featured = plans.length > 1 ? plans.reduce((a, b) => (b.save_pct > a.save_pct ? b : a), plans[0]).id : plans[0]?.id;
  return (
    <section id="pricing" className="bg-white py-20 sm:py-28" data-testid="pricing-section">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="font-display text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
            Simple pricing. <span className="text-brand">10 days free.</span>
          </h2>
          <p className="mt-4 text-base text-slate-600 sm:text-lg">Every plan includes every feature. No credit card needed to start.</p>
        </div>
        <div className={`mx-auto mt-14 grid gap-6 ${plans.length > 2 ? "md:grid-cols-3" : plans.length === 2 ? "max-w-3xl md:grid-cols-2" : "max-w-md"}`} data-testid="pricing-card">
          {plans.length === 0
            ? [0, 1, 2].map((i) => <div key={i} className="h-60 animate-pulse rounded-2xl bg-slate-100" />)
            : plans.map((p) => <PlanCard key={p.id} p={p} featured={p.id === featured} />)}
        </div>
        <div className="mx-auto mt-10 max-w-3xl rounded-2xl border border-slate-200 bg-slate-50 p-6">
          <p className="text-center text-sm font-semibold text-slate-900">Everything included in every plan</p>
          <ul className="mt-4 grid gap-2.5 sm:grid-cols-2">
            {INCLUDED.map((f) => (
              <li key={f} className="flex items-start gap-2.5 text-sm text-slate-700"><Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" strokeWidth={3} />{f}</li>
            ))}
          </ul>
          {!hasStoreLinks && (
            <p className="mt-5 flex items-center justify-center gap-1.5 text-center text-xs text-slate-400">
              <Smartphone className="h-3.5 w-3.5" /> Android & iOS apps coming soon. The web app works everywhere today.
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
