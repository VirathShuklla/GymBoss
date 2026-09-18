import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { IndianRupee, UserPlus, RefreshCw, HelpCircle, Wallet, Users, CalendarClock, ArrowUpRight, X, Check } from "lucide-react";
import api from "../../lib/api";
import { inr, formatDate } from "../../lib/format";
import { useAuth } from "../../contexts/AuthContext";
import { ListSkeleton, MThemeToggle } from "../ui";

const METRICS = [
  { key: "due_members", label: "Due Members", icon: Wallet, color: "text-danger" },
  { key: "expiring_today", label: "Expiry Today", icon: CalendarClock, color: "text-warning" },
  { key: "active_members", label: "Active", icon: Users, color: "text-success" },
  { key: "total_members", label: "Total Members", icon: Users, color: "text-foreground" },
  { key: "today_enquiries", label: "Enquiries", icon: HelpCircle, color: "text-info" },
];

export default function Home() {
  const navigate = useNavigate();
  const { organisation, user, subscription, reload } = useAuth();
  const [summary, setSummary] = useState(null);
  const [txns, setTxns] = useState(null);
  const [onb, setOnb] = useState(null);

  useEffect(() => {
    api.get("/dashboard/summary").then(({ data }) => setSummary(data)).catch(() => setSummary({}));
    api.get("/dashboard/recent-transactions").then(({ data }) => setTxns(data)).catch(() => setTxns([]));
    // Fetch onboarding fresh (AuthContext copy is loaded once at login and goes stale).
    api.get("/onboarding").then(({ data }) => setOnb(data)).catch(() => {});
  }, []);

  const trial = subscription?.status === "trial";

  return (
    <div className="m-anim" data-testid="m-home">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-muted-foreground">Hi {user?.full_name?.split(" ")[0] || "there"} 👋</p>
          <h1 className="font-display text-2xl font-extrabold tracking-tight text-foreground">{organisation?.name}</h1>
        </div>
        <div className="flex items-center gap-2">
          {trial && (
            <button onClick={() => navigate("/m/profile")} className="rounded-full bg-brand/10 px-3 py-1.5 text-xs font-bold text-brand" data-testid="m-trial-badge">
              {subscription?.trial_days_left}d trial left
            </button>
          )}
          <MThemeToggle />
        </div>
      </div>

      {(() => { const ob = onb || organisation?.onboarding; return ob && !ob.dismissed ? (
        <MOnboarding onboarding={ob}
          onDismiss={async () => { setOnb((p) => ({ ...(p || {}), dismissed: true })); await api.put("/onboarding", { dismissed: true }); reload(); }} />
      ) : null; })()}

      <div className="mt-5 overflow-hidden rounded-3xl bg-gradient-to-br from-brand to-[#5B21B6] p-5 text-white shadow-xl shadow-brand/25" data-testid="m-today-card">
        <p className="text-xs font-semibold uppercase tracking-wider opacity-80">Today's Collection</p>
        <p className="font-num mt-1 text-4xl font-extrabold tracking-tight">{summary ? inr(summary.today_collection) : "—"}</p>
        <div className="mt-4 flex gap-2">
          <div className="flex-1 rounded-2xl bg-white/15 px-3 py-2">
            <p className="text-[11px] opacity-80">Online</p>
            <p className="font-num text-base font-bold">{summary ? inr(summary.today_online) : "—"}</p>
          </div>
          <div className="flex-1 rounded-2xl bg-white/15 px-3 py-2">
            <p className="text-[11px] opacity-80">Cash</p>
            <p className="font-num text-base font-bold">{summary ? inr(summary.today_cash) : "—"}</p>
          </div>
          <div className="flex-1 rounded-2xl bg-white/15 px-3 py-2">
            <p className="text-[11px] opacity-80">Admissions</p>
            <p className="font-num text-base font-bold">{summary ? summary.today_admissions : "—"}</p>
          </div>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-3">
        {[
          { label: "Add Member", icon: UserPlus, to: "/m/manage?add=member" },
          { label: "Payment", icon: IndianRupee, to: "/m/manage?tab=members" },
          { label: "Renewals", icon: RefreshCw, to: "/m/manage?tab=members" },
        ].map((a) => (
          <button key={a.label} onClick={() => navigate(a.to)} data-testid={`m-quick-${a.label.toLowerCase().replace(/\s/g, "-")}`}
            className="flex flex-col items-center gap-2 rounded-2xl border border-border bg-card py-4 text-xs font-semibold text-foreground active:scale-95">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand/10 text-brand"><a.icon className="h-5 w-5" /></span>
            {a.label}
          </button>
        ))}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3">
        {METRICS.map((m) => (
          <div key={m.key} className="rounded-2xl border border-border bg-card px-4 py-3.5" data-testid={`m-metric-${m.key.replace(/_/g, "-")}`}>
            <div className="flex items-center justify-between">
              <p className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">{m.label}</p>
              <m.icon className={`h-4 w-4 ${m.color}`} />
            </div>
            <p className={`font-num mt-1 text-2xl font-extrabold ${m.color}`}>{summary ? summary[m.key] ?? 0 : "—"}</p>
          </div>
        ))}
      </div>

      <div className="mb-3 mt-7 flex items-center justify-between">
        <h2 className="font-display text-sm font-bold uppercase tracking-wider text-muted-foreground">Recent Transactions</h2>
      </div>
      {!txns ? (
        <ListSkeleton rows={4} />
      ) : txns.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border py-12 text-center text-sm text-muted-foreground" data-testid="m-txn-empty">No transactions yet</div>
      ) : (
        <div className="space-y-2.5" data-testid="m-txn-list">
          {txns.map((t) => (
            <div key={t.id} className="flex items-center gap-3 rounded-2xl border border-border bg-card px-4 py-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-success/10 text-success"><ArrowUpRight className="h-5 w-5" /></span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-foreground">{t.member_name}</p>
                <p className="text-xs text-muted-foreground">{formatDate(t.created_at)} · {t.method}</p>
              </div>
              <p className="font-num text-sm font-bold text-success">{inr(t.amount)}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Getting-started checklist ("tutorial") shown until the owner dismisses it.
// Each pending step deep-links into the relevant Manage tab; done steps come from
// organisation.onboarding (set server-side as the owner completes each action).
function MOnboarding({ onboarding, onDismiss }) {
  const navigate = useNavigate();
  const steps = [
    { key: "plan", label: "Create your first plan", to: "/m/manage?tab=plans" },
    { key: "member", label: "Add your first member", to: "/m/manage?add=member" },
    { key: "staff", label: "Add staff", to: "/m/manage?tab=staff" },
    { key: "payment", label: "Record a payment", to: "/m/manage?tab=members" },
  ];
  const done = steps.filter((s) => onboarding?.[s.key]).length;
  return (
    <div className="mt-5 rounded-3xl border border-brand/25 bg-brand/5 p-5" data-testid="m-onboarding">
      <div className="flex items-start justify-between">
        <div>
          <p className="font-display text-base font-bold text-foreground">Get your gym ready</p>
          <p className="text-xs text-muted-foreground">{done} of {steps.length} done</p>
        </div>
        <button onClick={onDismiss} data-testid="m-onboarding-dismiss" aria-label="Dismiss" className="rounded-md p-1 text-muted-foreground">
          <X className="h-4 w-4" />
        </button>
      </div>
      <ul className="mt-3 space-y-2">
        {steps.map((s) => {
          const d = onboarding?.[s.key];
          return (
            <li key={s.key} className="flex items-center gap-2.5 text-sm">
              <span className={`flex h-5 w-5 items-center justify-center rounded-full ${d ? "bg-success text-white" : "border-2 border-muted-foreground/40"}`}>
                {d && <Check className="h-3 w-3" strokeWidth={3.5} />}
              </span>
              {d
                ? <span className="text-muted-foreground line-through">{s.label}</span>
                : <button onClick={() => navigate(s.to)} data-testid={`m-onboarding-${s.key}`} className="font-medium text-foreground">{s.label}</button>}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
