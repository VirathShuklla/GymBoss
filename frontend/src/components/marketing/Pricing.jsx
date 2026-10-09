import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { Check, Smartphone, CreditCard, ShieldCheck, RotateCcw, Sparkles, ArrowRight } from "lucide-react";
import { usePublicConfig } from "../../hooks/usePublicConfig";
import { inr } from "../../lib/format";
import { track } from "../../lib/track";

const TRUST = [
  { icon: CreditCard, text: "No credit card for the trial" },
  { icon: RotateCcw, text: "Cancel anytime" },
  { icon: ShieldCheck, text: "Your data is never deleted" },
];
const per = (m) => (m === 1 ? "month" : m === 12 ? "year" : `${m} months`);

// Savings are shown against paying the monthly price for the same period.
function withSavings(p, monthly) {
  const full = Math.max(p.price, (monthly || 0) * p.months);
  const save = full - p.effective_price;
  return { ...p, compareAt: save > 0 ? full : null, save: save > 0 ? save : 0, pct: save > 0 ? Math.round((100 * save) / full) : 0 };
}

function PlanCard({ p, featured }) {
  return (
    <div
      data-testid={`pricing-plan-${p.id}`}
      className={`relative flex flex-col rounded-3xl p-7 transition-transform duration-300 hover:-translate-y-1 sm:p-8 ${
        featured
          ? "order-first bg-slate-900 text-white shadow-2xl shadow-brand/30 ring-2 ring-brand md:order-none md:-my-4 md:py-12"
          : "border border-slate-200 bg-white text-slate-900"
      }`}
    >
      {featured && (
        <span className="absolute -top-3.5 left-1/2 inline-flex -translate-x-1/2 items-center gap-1.5 whitespace-nowrap rounded-full bg-brand px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-white shadow-lg shadow-brand/40" data-testid="pricing-best-value">
          <Sparkles className="h-3.5 w-3.5" />Best Value
        </span>
      )}
      <div className="flex items-center justify-between gap-2">
        <p className={`font-display text-lg font-bold ${featured ? "text-white" : "text-slate-900"}`}>{p.name}</p>
        {(p.offer_label || p.pct > 0) && (
          <span className={`rounded-full px-2.5 py-1 text-[11px] font-bold ${featured ? "bg-emerald-400/15 text-emerald-300" : "bg-emerald-50 text-emerald-700"}`} data-testid={`pricing-offer-${p.id}`}>
            {p.offer_label || `Save ${p.pct}%`}
          </span>
        )}
      </div>

      <div className="mt-5 flex items-baseline gap-1.5">
        <span className="font-display text-5xl font-extrabold tracking-tight" data-testid={`pricing-price-${p.id}`}>{inr(p.effective_price)}</span>
        <span className={`text-sm font-medium ${featured ? "text-slate-400" : "text-slate-500"}`}>/{per(p.months)}</span>
      </div>
      <div className={`mt-2 min-h-[44px] text-sm ${featured ? "text-slate-300" : "text-slate-500"}`}>
        {p.months > 1 ? (
          <p>Just <span className={`font-semibold ${featured ? "text-white" : "text-slate-900"}`}>{inr(p.per_month)}/month</span> · only {inr(Math.round(p.effective_price / (p.months * 30)))}/day</p>
        ) : (
          <p>Only {inr(Math.round(p.effective_price / 30))}/day. Switch plans anytime.</p>
        )}
        {p.compareAt && (
          <p className="mt-0.5">
            <span className="line-through opacity-70">{inr(p.compareAt)}</span>
            <span className={`ml-2 font-semibold ${featured ? "text-emerald-300" : "text-emerald-600"}`}>You save {inr(p.save)}</span>
          </p>
        )}
      </div>

      <Link
        to="/register"
        onClick={() => track("pricing_cta_click", { plan: p.id, price: p.effective_price })}
        data-testid={`pricing-cta-${p.id}`}
        className={`group mt-7 flex items-center justify-center gap-2 rounded-xl py-3.5 text-sm font-semibold transition-colors ${
          featured ? "bg-brand text-white hover:bg-brand-hover" : "border border-slate-300 text-slate-900 hover:border-slate-900 hover:bg-slate-900 hover:text-white"
        }`}
      >
        Start 10-Day Free Trial
        <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
      </Link>
      <p className={`mt-3 text-center text-xs ${featured ? "text-slate-400" : "text-slate-400"}`}>Free for 10 days, then {inr(p.effective_price)}/{per(p.months)}</p>
    </div>
  );
}

export function Pricing() {
  const config = usePublicConfig();
  const hasStoreLinks = config?.play_store_url || config?.app_store_url;
  const raw = config?.pricing_plans || [];
  const monthly = raw.find((p) => p.id === "monthly")?.effective_price;
  const plans = raw.map((p) => withSavings(p, monthly));
  const featured = plans.some((p) => p.id === "yearly") ? "yearly" : plans[plans.length - 1]?.id;
  const cols = plans.length > 2 ? "md:grid-cols-3" : plans.length === 2 ? "max-w-3xl md:grid-cols-2" : "max-w-md";
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current;
    if (!el || !("IntersectionObserver" in window)) return;
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { track("pricing_viewed", {}, { oncePerSession: true }); io.disconnect(); } }, { threshold: 0.3 });
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <section id="pricing" ref={ref} className="relative overflow-hidden bg-gradient-to-b from-white via-violet-50/40 to-white py-20 sm:py-28" data-testid="pricing-section">
      <div className="pointer-events-none absolute left-1/2 top-40 hidden h-96 w-96 -translate-x-1/2 rounded-full bg-brand/10 blur-3xl sm:block" />
      <div className="relative mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-bold uppercase tracking-widest text-brand">Pricing</p>
          <h2 className="mt-3 font-display text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
            Every feature in every plan.<br /><span className="text-brand">First 10 days free.</span>
          </h2>
          <p className="mt-4 text-base text-slate-600 sm:text-lg">Try everything free. No credit card needed. Pick a plan only when you're ready.</p>
        </div>

        <div className={`mx-auto mt-16 grid items-center gap-6 ${cols}`} data-testid="pricing-card">
          {plans.length === 0
            ? [0, 1, 2].map((i) => <div key={i} className="h-80 animate-pulse rounded-3xl bg-slate-100" />)
            : plans.map((p) => <PlanCard key={p.id} p={p} featured={p.id === featured} />)}
        </div>

        <div className="mt-10 flex flex-wrap items-center justify-center gap-x-8 gap-y-3" data-testid="pricing-trust">
          {TRUST.map(({ icon: Icon, text }) => (
            <span key={text} className="inline-flex items-center gap-2 text-sm font-medium text-slate-600">
              <Icon className="h-4 w-4 text-brand" />{text}
            </span>
          ))}
          <span className="inline-flex items-center gap-2 text-sm font-medium text-slate-600">Pay by UPI, card or netbanking</span>
        </div>

        <div className="mx-auto mt-10 max-w-3xl rounded-2xl border border-slate-200 bg-white px-6 py-4 text-center" data-testid="pricing-included">
          <p className="flex items-center justify-center gap-2 text-sm font-semibold text-slate-900"><Check className="h-4 w-4 shrink-0 text-emerald-600" strokeWidth={3} />Every plan includes every feature. Unlimited members, no add-ons, no per-member fees.</p>
          {!hasStoreLinks && (
            <p className="mt-2 flex items-center justify-center gap-1.5 text-xs text-slate-400">
              <Smartphone className="h-3.5 w-3.5" /> Android & iOS apps coming soon. The web app works on every phone today.
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
