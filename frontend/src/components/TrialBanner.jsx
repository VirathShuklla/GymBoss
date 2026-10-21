import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PartyPopper, Clock, ShieldCheck, ArrowRight, Users, IndianRupee, ClipboardCheck, RefreshCw } from "lucide-react";
import api from "../lib/api";
import { inr } from "../lib/format";
import { isInApp } from "../lib/inApp";

const inApp = isInApp();

const STAT_ROWS = [
  ["members", "members managed", Users],
  ["payments", "payments recorded", IndianRupee],
  ["attendance", "attendance records", ClipboardCheck],
  ["renewals", "renewals tracked", RefreshCw],
];

function Stats({ stats }) {
  return (
    <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4" data-testid="trial-value-stats">
      {STAT_ROWS.map(([k, label, Icon]) => (
        <div key={k} className="rounded-xl bg-background/70 px-3 py-2">
          <p className="font-num flex items-center gap-1.5 text-lg font-extrabold text-foreground"><Icon className="h-4 w-4 text-brand" />{stats[k] ?? 0}</p>
          <p className="text-[11px] text-muted-foreground">{label}</p>
        </div>
      ))}
    </div>
  );
}

function CTA({ to, children = "Choose Your Plan", testid }) {
  return (
    <Link to={to} data-testid={testid} className="inline-flex items-center gap-1.5 rounded-xl bg-brand px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-hover">
      {children}<ArrowRight className="h-4 w-4" />
    </Link>
  );
}

// Friendly trial reminder that shows what the gym has already built in GymBoss.
export function TrialBanner({ planPath }) {
  const [t, setT] = useState(null);
  useEffect(() => { api.get("/trial/status").then(({ data }) => setT(data)).catch(() => {}); }, []);
  if (!t || t.status !== "trial") return null;
  const left = t.days_left;
  const from = inr(t.from_price);
  const dayWord = `${left} day${left === 1 ? "" : "s"}`;
  if (inApp) {
    return (
      <div className="rounded-xl border border-border bg-card px-4 py-2.5 text-sm text-muted-foreground" data-testid="trial-banner" data-phase="store">
        <span className="font-semibold text-foreground">{dayWord} left</span> in your organisation's free trial
      </div>
    );
  }

  if (left <= 2) {
    return (
      <div className="rounded-2xl border border-brand/25 bg-brand/5 p-4" data-testid="trial-banner" data-phase="late">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="flex items-center gap-1.5 font-display text-base font-bold text-foreground"><Clock className="h-4 w-4 text-brand" />{left === 0 ? "Last day of your free trial" : `${dayWord} remaining`}</p>
            <p className="mt-0.5 text-sm text-muted-foreground">Here's what you've already built in GymBoss. Keep it all running from {from}/month.</p>
          </div>
          <CTA to={planPath} testid="trial-banner-cta" />
        </div>
        <Stats stats={t.stats} />
      </div>
    );
  }
  if (left <= 5 && t.stats.members > 0) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-success/25 bg-success/5 p-4" data-testid="trial-banner" data-phase="mid">
        <div>
          <p className="flex items-center gap-1.5 font-display text-base font-bold text-foreground"><PartyPopper className="h-4 w-4 text-success" />You've already added {t.stats.members} members</p>
          <p className="mt-0.5 text-sm text-muted-foreground">Continue using GymBoss after your trial from {from}/month. {dayWord} left.</p>
        </div>
        <Link to={planPath} className="text-sm font-semibold text-brand hover:underline" data-testid="trial-banner-cta">See plans</Link>
      </div>
    );
  }
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border bg-card px-4 py-2.5 text-sm" data-testid="trial-banner" data-phase="early">
      <p className="text-muted-foreground"><span className="font-semibold text-foreground">{dayWord} left</span> in your free trial</p>
      <Link to={planPath} className="font-semibold text-brand hover:underline" data-testid="trial-banner-cta">See plans</Link>
    </div>
  );
}

// Shown after the trial ends: app stays viewable, data is safe, writes are paused.
export function ExpiredBanner({ planPath, price, status }) {
  const due = status === "payment_due";
  if (inApp) {
    return (
      <div className="mb-5 rounded-2xl border border-warning/30 bg-warning/10 p-4" data-testid="trial-expired-banner" data-mode="store">
        <p className="font-display text-base font-bold text-foreground">Your organisation's subscription is not active</p>
        <p className="mt-1 flex items-start gap-1.5 text-sm text-foreground/80"><ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-success" />Your data is safe. You can still view everything; adding or editing is paused.</p>
        <p className="mt-1 text-xs text-muted-foreground">For billing questions, contact your account administrator.</p>
      </div>
    );
  }
  return (
    <div className="mb-5 rounded-2xl border border-warning/30 bg-warning/10 p-4 sm:p-5" data-testid="trial-expired-banner">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0">
          <p className="font-display text-lg font-bold text-foreground">{due ? "Your GymBoss subscription is due" : "Your GymBoss trial has ended"}</p>
          <p className="mt-1 flex items-start gap-1.5 text-sm text-foreground/80">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-success" />Your members, payment records and attendance data are safe.
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            {due ? "Renew to keep everything running." : "You can still view everything. Adding or editing is paused."} Continue managing your gym: plans starting at <span className="font-semibold text-foreground">{inr(price || 999)}/month</span>.
          </p>
        </div>
        <CTA to={planPath} testid="reactivate-button">Reactivate GymBoss</CTA>
      </div>
    </div>
  );
}
