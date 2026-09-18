import { useEffect, useState } from "react";
import { useOutletContext, useNavigate, Link } from "react-router-dom";
import {
  IndianRupee, UserPlus, RefreshCw, Wallet, HelpCircle, Zap, Briefcase, Package,
  Users, CalendarClock, Cake, Plus, X, Check, AlertTriangle,
} from "lucide-react";
import api from "../../lib/api";
import { inr, formatDate } from "../../lib/format";
import { useAuth } from "../../contexts/AuthContext";
import { Skeleton } from "../../components/ui/skeleton";

const PRIMARY_KPIS = [
  { key: "today_collection", label: "Today's Collection", icon: IndianRupee, color: "text-success", tile: "bg-success/12", money: true },
  { key: "today_admissions", label: "Today's Admissions", icon: UserPlus, color: "text-info", tile: "bg-info/12" },
  { key: "today_renewals", label: "Today's Renewals", icon: RefreshCw, color: "text-brand", tile: "bg-brand/12" },
  { key: "due_paid_today", label: "Due Paid Today", icon: Wallet, color: "text-warning", tile: "bg-warning/12", money: true },
  { key: "today_enquiries", label: "Today's Enquiries", icon: HelpCircle, color: "text-info", tile: "bg-info/12" },
  { key: "today_pt", label: "Today's PT Sales", icon: Zap, color: "text-warning", tile: "bg-warning/12", money: true },
  { key: "today_service", label: "Today's Service Sales", icon: Briefcase, color: "text-info", tile: "bg-info/12", money: true },
  { key: "today_product", label: "Today's Product Sales", icon: Package, color: "text-success", tile: "bg-success/12", money: true },
];

const SECONDARY = [
  { key: "due_members", label: "Due Members", color: "text-danger" },
  { key: "expiring_today", label: "Expiry Today", color: "text-warning" },
  { key: "expiring_1_3_days", label: "Expiry in 1–3 Days", color: "text-warning" },
  { key: "birthdays_today", label: "Birthdays Today", color: "text-brand" },
  { key: "active_members", label: "Active Members", color: "text-success" },
  { key: "total_members", label: "Total Members", color: "text-foreground" },
];

function OnboardingChecklist({ onboarding, onDismiss }) {
  const items = [
    { key: "gym", label: "Gym created", done: true, to: null },
    { key: "plan", label: "Create your first membership plan", done: onboarding?.plan, to: "/app/plans" },
    { key: "member", label: "Add your first member", done: onboarding?.member, to: "/app/members" },
    { key: "staff", label: "Add staff", done: onboarding?.staff, to: "/app/staff" },
    { key: "payment", label: "Record a payment", done: onboarding?.payment, to: "/app/payments" },
  ];
  return (
    <div className="rounded-xl border border-brand/25 bg-brand/5 p-5" data-testid="onboarding-checklist">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-display text-base font-bold text-foreground">Welcome to GymBoss_VVO</h3>
          <p className="mt-0.5 text-sm text-muted-foreground">Let's get your gym ready.</p>
        </div>
        <button onClick={onDismiss} className="rounded-md p-1 text-muted-foreground hover:text-foreground" data-testid="onboarding-dismiss" aria-label="Dismiss checklist">
          <X className="h-4 w-4" />
        </button>
      </div>
      <ul className="mt-4 space-y-2.5">
        {items.map((item) => (
          <li key={item.key} className="flex items-center gap-2.5 text-sm">
            <span className={`flex h-5 w-5 items-center justify-center rounded-full ${item.done ? "bg-success text-white" : "border-2 border-muted-foreground/40"}`}>
              {item.done && <Check className="h-3 w-3" strokeWidth={3.5} />}
            </span>
            {item.to && !item.done ? (
              <Link to={item.to} className="font-medium text-foreground hover:text-brand" data-testid={`onboarding-${item.key}`}>{item.label}</Link>
            ) : (
              <span className={item.done ? "text-muted-foreground line-through" : "font-medium text-foreground"}>{item.label}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function BillingHaltedAlert() {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-danger/30 bg-danger/8 p-4 sm:flex-row sm:items-center sm:justify-between" data-testid="billing-halted-alert">
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-danger/15 text-danger">
          <AlertTriangle className="h-[18px] w-[18px]" strokeWidth={2.2} />
        </div>
        <div>
          <p className="text-sm font-bold text-foreground">Your monthly payment didn't go through</p>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Auto-debit was paused after a failed charge. Retry now to keep your GymBoss_VVO access uninterrupted.
          </p>
        </div>
      </div>
      <Link to="/app/subscription" data-testid="billing-halted-retry"
            className="shrink-0 rounded-lg bg-danger px-4 py-2.5 text-center text-sm font-semibold text-white transition-opacity hover:opacity-90">
        Retry Payment
      </Link>
    </div>
  );
}

export default function Dashboard() {
  const { outletId } = useOutletContext() || {};
  const { organisation, outlets, reload, user } = useAuth();
  const readOnly = user?.permission === "view" && user?.role !== "owner";
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [transactions, setTransactions] = useState(null);
  const [error, setError] = useState("");
  const [billingHalted, setBillingHalted] = useState(false);

  const outletName = outletId ? outlets.find((o) => o.id === outletId)?.name : null;

  useEffect(() => {
    const params = outletId ? { outlet_id: outletId } : {};
    setError("");
    Promise.all([
      api.get("/dashboard/summary", { params }),
      api.get("/dashboard/recent-transactions", { params }),
    ])
      .then(([s, t]) => { setSummary(s.data); setTransactions(t.data); })
      .catch(() => setError("We couldn't load your dashboard."));
  }, [outletId]);

  useEffect(() => {
    if (user?.role !== "owner") return;
    api.get("/subscription")
      .then(({ data }) => setBillingHalted(data?.autodebit?.status === "halted"))
      .catch(() => {});
  }, [user?.role]);

  // Onboarding flags are updated server-side as steps are completed on other pages,
  // so always fetch the latest here instead of the AuthContext copy (loaded once at login).
  useEffect(() => {
    api.get("/onboarding").then(({ data }) => setOnb(data)).catch(() => {});
  }, []);

  const dismissOnboarding = async () => {
    await api.put("/onboarding", { dismissed: true });
    setOnb((prev) => ({ ...(prev || {}), dismissed: true }));
    reload();
  };

  const quickActions = [
    { label: "Add Member", icon: Plus, to: "/app/members?add=1" },
    { label: "Record Payment", icon: IndianRupee, to: "/app/payments" },
    { label: "Add Enquiry", icon: UserPlus, to: "/app/enquiries" },
  ];

  return (
    <div className="space-y-6" data-testid="dashboard-page">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-bold tracking-tight text-foreground">Dashboard</h1>
          <p className="mt-0.5 text-sm text-muted-foreground" data-testid="dashboard-subtitle">
            {organisation?.name}{outletName ? ` — ${outletName}` : " — All Outlets"}
          </p>
        </div>
      </div>

      {billingHalted && <BillingHaltedAlert />}

      {(() => { const ob = onb || organisation?.onboarding; return ob && !ob.dismissed ? (
        <OnboardingChecklist onboarding={ob} onDismiss={dismissOnboarding} />
      ) : null; })()}

      {error ? (
        <div className="rounded-xl border border-border bg-card p-10 text-center" data-testid="dashboard-error">
          <p className="text-sm text-muted-foreground">{error}</p>
          <button onClick={() => window.location.reload()} className="mt-3 rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-white">Try Again</button>
        </div>
      ) : !summary ? (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-4" data-testid="kpi-grid">
            {PRIMARY_KPIS.map((k) => (
              <div key={k.key} className="rounded-xl border border-border bg-card p-4 shadow-card" data-testid={`kpi-${k.key.replace(/_/g, "-")}`}>
                <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${k.tile}`}>
                  <k.icon className={`h-[18px] w-[18px] ${k.color}`} strokeWidth={2.2} />
                </div>
                <p className="mt-3 text-xs font-medium text-muted-foreground">{k.label}</p>
                <p className="font-num mt-1 text-xl font-bold text-foreground">{k.money ? inr(summary[k.key]) : summary[k.key]}</p>
                {k.key === "today_collection" && (
                  <p className="mt-1 text-[11px] text-muted-foreground">
                    Online <span className="font-num text-info">{inr(summary.today_online)}</span> · Cash <span className="font-num text-success">{inr(summary.today_cash)}</span>
                  </p>
                )}
              </div>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7" data-testid="secondary-metrics">
            {SECONDARY.map((s) => (
              <div key={s.key} className="rounded-xl border border-border bg-card px-4 py-3" data-testid={`metric-${s.key.replace(/_/g, "-")}`}>
                <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{s.label}</p>
                <p className={`font-num mt-1.5 text-lg font-bold ${s.color}`}>{summary[s.key]}</p>
              </div>
            ))}
          </div>
        </>
      )}

      {!readOnly && (
        <div>
          <h2 className="mb-3 font-display text-sm font-bold uppercase tracking-wider text-muted-foreground">Quick Actions</h2>
        <div className="flex flex-wrap gap-2.5" data-testid="quick-actions">
          {quickActions.map((a) => (
            <button key={a.label} onClick={() => navigate(a.to)} data-testid={`quick-${a.label.toLowerCase().replace(/\s/g, "-")}`}
                    className="flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-2.5 text-sm font-medium text-foreground shadow-card transition-all hover:border-brand/40 hover:text-brand">
              <a.icon className="h-4 w-4 text-brand" /> {a.label}
            </button>
          ))}
        </div>
        </div>
      )}

      <div className="rounded-xl border border-border bg-card shadow-card" data-testid="recent-transactions">
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h2 className="font-display text-base font-bold text-foreground">Recent Transactions</h2>
          <Link to="/app/payments" className="text-sm font-medium text-brand hover:underline" data-testid="view-all-transactions">View all</Link>
        </div>
        {!transactions ? (
          <div className="space-y-2 px-5 py-5">
            {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-9 w-full rounded-md" />)}
          </div>
        ) : transactions.length === 0 ? (
          <div className="px-5 py-12 text-center" data-testid="transactions-empty">
            <IndianRupee className="mx-auto h-8 w-8 text-muted-foreground/40" />
            <p className="mt-3 text-sm font-medium text-foreground">No transactions yet</p>
            <p className="mt-1 text-sm text-muted-foreground">Payments you record will appear here.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                  <th className="px-5 py-3">Date</th>
                  <th className="px-5 py-3">Member</th>
                  <th className="px-5 py-3">Type</th>
                  <th className="px-5 py-3">Plan</th>
                  <th className="px-5 py-3 text-right">Amount</th>
                  <th className="px-5 py-3">Method</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((t) => (
                  <tr key={t.id} className="border-b border-border/60 last:border-0 hover:bg-secondary/40" data-testid={`transaction-${t.receipt_no}`}>
                    <td className="px-5 py-2.5 text-muted-foreground">{formatDate(t.created_at)}</td>
                    <td className="px-5 py-2.5 font-medium text-foreground">{t.member_name}</td>
                    <td className="px-5 py-2.5">
                      <span className={`badge-status ${t.type === "admission" ? "badge-active" : t.type === "renewal" ? "badge-frozen" : "badge-expiring"}`}>
                        {t.type === "admission" ? "Admission" : t.type === "renewal" ? "Renewal" : "Due"}
                      </span>
                    </td>
                    <td className="px-5 py-2.5 text-muted-foreground">{t.plan_name}</td>
                    <td className="px-5 py-2.5 text-right font-num font-bold text-success">{inr(t.amount)}</td>
                    <td className="px-5 py-2.5 text-muted-foreground">{t.method}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
