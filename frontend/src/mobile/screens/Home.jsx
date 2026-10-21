import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { IndianRupee, UserPlus, RefreshCw, ArrowUpRight, X, Check, ClipboardCheck, ChevronRight } from "lucide-react";
import api from "../../lib/api";
import { inr, formatDate } from "../../lib/format";
import { useAuth } from "../../contexts/AuthContext";
import { ListSkeleton, MThemeToggle, EmptyRow } from "../ui";
import { TrialBanner } from "../../components/TrialBanner";

const ATTENTION = [
  { key: "due_members", label: "Members with dues", hint: "Collect pending payments", tone: "bg-danger", to: "/m/manage?tab=members" },
  { key: "expiring_today", label: "Expiring today", hint: "Renew before they lapse", tone: "bg-warning", to: "/m/manage?tab=members" },
  { key: "today_enquiries", label: "New enquiries", hint: "Follow up while warm", tone: "bg-info", to: "/m/manage?tab=enquiries" },
];
const GLANCE = [
  { key: "active_members", label: "Active", to: "/m/manage?tab=members" },
  { key: "total_members", label: "Members", to: "/m/manage?tab=members" },
  { key: "attendance_today", label: "Check-ins", to: "/m/attendance" },
];
const ACTIONS = [
  { label: "Add Member", icon: UserPlus, to: "/m/manage?add=member" },
  { label: "Payment", icon: IndianRupee, to: "/m/manage?tab=members" },
  { label: "Check-in", icon: ClipboardCheck, to: "/m/attendance" },
  { label: "Renewals", icon: RefreshCw, to: "/m/manage?tab=members" },
];
const today = new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "short" });

export default function Home() {
  const navigate = useNavigate();
  const { organisation, user, subscription, reload } = useAuth();
  const [summary, setSummary] = useState(null);
  const [txns, setTxns] = useState(null);
  const [onb, setOnb] = useState(null);

  useEffect(() => {
    api.get("/dashboard/summary").then(({ data }) => setSummary(data)).catch(() => setSummary({}));
    api.get("/dashboard/recent-transactions").then(({ data }) => setTxns(data)).catch(() => setTxns([]));
    api.get("/onboarding").then(({ data }) => setOnb(data)).catch(() => {});
  }, []);

  const ob = onb || organisation?.onboarding;
  const showOnboarding = ob && !ob.dismissed && !["plan", "member", "staff", "payment"].every((k) => ob[k]);
  const val = (k) => (summary ? summary[k] ?? 0 : "—");

  return (
    <div className="m-anim" data-testid="m-home">
      <header className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">{today}</p>
          <h1 className="mt-1 font-display text-[26px] font-bold leading-tight tracking-tight text-foreground line-clamp-2">
            Hi, {user?.full_name?.split(" ")[0] || "there"}
          </h1>
          <p className="truncate text-sm text-muted-foreground">{organisation?.name}</p>
        </div>
        <div className="flex shrink-0 items-center gap-2 pt-1">
          {subscription?.status === "trial" && (
            <button onClick={() => navigate("/m/profile")} className="whitespace-nowrap rounded-full border border-border px-3 py-1.5 text-[11px] font-semibold text-muted-foreground active:scale-95" data-testid="m-trial-badge">
              Trial · {subscription?.trial_days_left}d
            </button>
          )}
          <MThemeToggle />
        </div>
      </header>

      <div className="mt-5"><TrialBanner planPath="/m/profile" /></div>
      {showOnboarding && <MOnboarding onboarding={ob} onDismiss={async () => { setOnb((p) => ({ ...(p || {}), dismissed: true })); await api.put("/onboarding", { dismissed: true }); reload(); }} />}

      <section className="m-hero mt-5" data-testid="m-today-card">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-white/55">Today's collection</p>
        <p className="font-num mt-2 text-[40px] font-bold leading-none tracking-tight text-white">{summary ? inr(summary.today_collection) : "—"}</p>
        <div className="mt-5 grid grid-cols-3 divide-x divide-white/10 border-t border-white/10 pt-4">
          {[["Online", summary && inr(summary.today_online)], ["Cash", summary && inr(summary.today_cash)], ["Joined", summary?.today_admissions]].map(([l, v], i) => (
            <div key={l} className={i ? "pl-3" : ""}>
              <p className="text-[11px] text-white/50">{l}</p>
              <p className="font-num mt-0.5 text-sm font-semibold text-white">{v ?? "—"}</p>
            </div>
          ))}
        </div>
      </section>

      <nav className="mt-6 grid grid-cols-4 gap-1" aria-label="Quick actions">
        {ACTIONS.map((a) => (
          <button key={a.label} onClick={() => navigate(a.to)} data-testid={`m-quick-${a.label.toLowerCase().replace(/\s/g, "-")}`}
            className="group flex flex-col items-center gap-2 rounded-2xl py-2 text-[11px] font-medium text-foreground">
            <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-secondary text-foreground transition-[transform,background-color] duration-150 group-active:scale-90 group-active:bg-brand/15">
              <a.icon className="h-[20px] w-[20px]" strokeWidth={1.9} />
            </span>
            {a.label}
          </button>
        ))}
      </nav>

      <SectionLabel>Needs attention</SectionLabel>
      <div className="m-group">
        {ATTENTION.map((m) => (
          <button key={m.key} onClick={() => navigate(m.to)} className="m-group-row" data-testid={`m-metric-${m.key.replace(/_/g, "-")}`}>
            <span className={`h-2 w-2 shrink-0 rounded-full ${m.tone}`} />
            <span className="min-w-0 flex-1 text-left">
              <span className="block text-sm font-medium text-foreground">{m.label}</span>
              <span className="block text-xs text-muted-foreground">{m.hint}</span>
            </span>
            <span className="font-num text-lg font-semibold text-foreground">{val(m.key)}</span>
            <ChevronRight className="h-4 w-4 text-muted-foreground/60" />
          </button>
        ))}
      </div>

      <SectionLabel>At a glance</SectionLabel>
      <div className="m-group grid grid-cols-3 divide-x divide-border">
        {GLANCE.map((m) => (
          <button key={m.key} onClick={() => navigate(m.to)} className="px-3 py-4 text-left transition-colors active:bg-secondary" data-testid={`m-metric-${m.key.replace(/_/g, "-")}`}>
            <p className="font-num text-2xl font-semibold text-foreground">{val(m.key)}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">{m.label}</p>
          </button>
        ))}
      </div>

      <SectionLabel>Recent payments</SectionLabel>
      {!txns ? (
        <ListSkeleton rows={3} />
      ) : txns.length === 0 ? (
        <EmptyRow icon={ArrowUpRight} title="No payments yet" subtitle="Payments you record will show up here." testid="m-txn-empty" />
      ) : (
        <div className="m-group" data-testid="m-txn-list">
          {txns.slice(0, 5).map((t) => (
            <div key={t.id} className="m-group-row">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-secondary font-display text-[11px] font-bold text-foreground">
                {t.member_name?.slice(0, 2).toUpperCase()}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-foreground">{t.member_name}</p>
                <p className="text-xs capitalize text-muted-foreground">{formatDate(t.created_at)} · {t.method}</p>
              </div>
              <p className="font-num text-sm font-semibold text-success">+{inr(t.amount)}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SectionLabel({ children }) {
  return <h2 className="mb-2.5 mt-7 px-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">{children}</h2>;
}

// Getting-started checklist shown until the owner dismisses it or completes every step.
function MOnboarding({ onboarding, onDismiss }) {
  const navigate = useNavigate();
  const steps = [
    { key: "plan", label: "Create your first plan", to: "/m/manage?tab=plans" },
    { key: "member", label: "Add your first member", to: "/m/manage?add=member" },
    { key: "staff", label: "Add staff", to: "/m/manage?tab=staff" },
    { key: "payment", label: "Record a payment", to: "/m/manage?tab=members" },
  ];
  const done = steps.filter((s) => onboarding?.[s.key]).length;
  const next = steps.find((s) => !onboarding?.[s.key]);
  return (
    <div className="m-group mt-5 p-4" data-testid="m-onboarding">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-foreground">Set up your gym <span className="font-normal text-muted-foreground">· {done}/{steps.length}</span></p>
        <button onClick={onDismiss} data-testid="m-onboarding-dismiss" aria-label="Dismiss" className="-m-2 flex h-10 w-10 items-center justify-center rounded-full text-muted-foreground active:bg-secondary">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="mt-2 h-1 overflow-hidden rounded-full bg-secondary"><div className="h-full rounded-full bg-brand transition-[width] duration-500" style={{ width: `${(done / steps.length) * 100}%` }} /></div>
      <ul className="mt-3 space-y-1">
        {steps.map((s) => {
          const d = onboarding?.[s.key];
          return (
            <li key={s.key}>
              {d ? (
                <span className="flex items-center gap-2.5 py-1.5 text-sm text-muted-foreground line-through">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-success text-white"><Check className="h-3 w-3" strokeWidth={3.5} /></span>{s.label}
                </span>
              ) : (
                <button onClick={() => navigate(s.to)} data-testid={`m-onboarding-${s.key}`} className={`flex w-full items-center gap-2.5 py-1.5 text-left text-sm ${s === next ? "font-semibold text-foreground" : "text-muted-foreground"}`}>
                  <span className={`h-5 w-5 rounded-full border-2 ${s === next ? "border-brand" : "border-muted-foreground/30"}`} />{s.label}
                  {s === next && <ChevronRight className="ml-auto h-4 w-4 text-brand" />}
                </button>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
