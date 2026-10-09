import { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  Building2, Settings as SettingsIcon, ScrollText, Eye, Power, LogOut, LayoutDashboard, Users,
  TrendingUp, TrendingDown, IndianRupee, Activity, AlertTriangle, CreditCard, Repeat, Zap, X, Minus, Download, Loader2,
} from "lucide-react";
import {
  ResponsiveContainer, AreaChart, Area, LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
} from "recharts";
import { toast } from "sonner";
import api from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { inr } from "../lib/format";
import { DataTable, SearchInput, ConfirmDialog } from "../components/app/ui";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Switch } from "../components/ui/switch";
import { ThemeToggle } from "../components/ThemeToggle";
import { downloadBlob } from "../lib/files";
import { FunnelTab } from "../components/admin/FunnelTab";

const fmtMonth = (k) => { const [y, m] = k.split("-"); return new Date(y, m - 1, 1).toLocaleDateString("en-IN", { month: "short", year: "2-digit" }); };
const pct = (v) => `${v > 0 ? "+" : ""}${v}%`;

function Delta({ value, inverse = false }) {
  if (value === null || value === undefined) return null;
  const good = inverse ? value <= 0 : value >= 0;
  const Icon = value > 0 ? TrendingUp : value < 0 ? TrendingDown : Minus;
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-semibold ${good ? "text-success" : "text-danger"}`}>
      <Icon className="h-3.5 w-3.5" />{pct(value)}
    </span>
  );
}

function KPI({ label, value, delta, inverse, hint, Icon, primary, testid }) {
  return (
    <div className={`rounded-2xl border bg-card p-5 shadow-card transition-shadow hover:shadow-lg ${primary ? "border-brand/30" : "border-border"}`} data-testid={testid}>
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</p>
        {Icon && <span className={`flex h-8 w-8 items-center justify-center rounded-lg ${primary ? "bg-brand/12 text-brand" : "bg-secondary text-muted-foreground"}`}><Icon className="h-4 w-4" /></span>}
      </div>
      <p className={`font-num mt-2 font-extrabold text-foreground ${primary ? "text-3xl" : "text-2xl"}`}>{value}</p>
      <div className="mt-1 flex items-center gap-2">
        {delta !== undefined && <Delta value={delta} inverse={inverse} />}
        {hint && <span className="text-xs text-muted-foreground">{hint}</span>}
      </div>
    </div>
  );
}

function Card({ title, subtitle, children, action, testid }) {
  return (
    <div className="rounded-2xl border border-border bg-card p-5 shadow-card" data-testid={testid}>
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h3 className="font-display text-base font-bold text-foreground">{title}</h3>
          {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </div>
  );
}

const HEALTH = {
  healthy: { label: "Healthy", cls: "bg-success/15 text-success", dot: "🟢" },
  at_risk: { label: "At Risk", cls: "bg-warning/15 text-warning", dot: "🟡" },
  high_risk: { label: "High Risk", cls: "bg-danger/15 text-danger", dot: "🔴" },
  churned: { label: "Churned", cls: "bg-muted text-muted-foreground", dot: "⚪" },
};
const STATUS_CLS = {
  active: "bg-success/15 text-success", trial: "bg-brand/15 text-brand",
  expired: "bg-danger/15 text-danger", payment_due: "bg-warning/15 text-warning", cancelled: "bg-muted text-muted-foreground",
};
function Badge({ cls, children, testid }) { return <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${cls}`} data-testid={testid}>{children}</span>; }

const RANGES = [{ v: 3, l: "3M" }, { v: 6, l: "6M" }, { v: 12, l: "1Y" }, { v: 99, l: "All" }];
const METRICS = [{ v: "revenue", l: "Revenue" }, { v: "new_customers", l: "New Customers" }, { v: "total_customers", l: "Total Customers" }];

export default function SuperAdmin() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [a, setA] = useState(null);
  const [tab, setTab] = useState("overview");
  const [gyms, setGyms] = useState(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [healthFilter, setHealthFilter] = useState("all");
  const [detail, setDetail] = useState(null);
  const [toggleGym, setToggleGym] = useState(null);
  const [busy, setBusy] = useState(false);
  const [range, setRange] = useState(12);
  const [metric, setMetric] = useState("revenue");
  const [settings, setSettings] = useState({ whatsapp_number: "", support_email: "", play_store_url: "", app_store_url: "", plan_price_inr: 999, razorpay_key_id: "", razorpay_key_secret: "", razorpay_webhook_secret: "" });
  const [logs, setLogs] = useState([]);

  const loadAnalytics = () => api.get("/admin/analytics").then(({ data }) => setA(data)).catch(() => {});
  const loadGyms = () => api.get("/admin/gyms", { params: { search: search || undefined, status: statusFilter === "all" ? undefined : statusFilter, health: healthFilter === "all" ? undefined : healthFilter } }).then(({ data }) => setGyms(data));

  useEffect(() => { loadAnalytics(); api.get("/admin/settings").then(({ data }) => setSettings((s) => ({ ...s, ...data }))); api.get("/admin/audit-logs").then(({ data }) => setLogs(data)); }, []);
  useEffect(() => { setGyms(null); const t = setTimeout(loadGyms, 300); return () => clearTimeout(t); }, [search, statusFilter, healthFilter]);

  const openDetail = async (g) => { const { data } = await api.get(`/admin/gyms/${g.id}`); setDetail(data); };
  const doToggle = async () => {
    setBusy(true);
    try { await api.post(`/admin/gyms/${toggleGym.id}/toggle`); setToggleGym(null); loadGyms(); api.get("/admin/audit-logs").then(({ data }) => setLogs(data)); }
    finally { setBusy(false); }
  };
  const saveSettings = async (e) => {
    e.preventDefault(); setBusy(true);
    const { plan_price_inr, ...rest } = settings;
    const pricing_plans = (settings.pricing_plans || []).map((p) => ({ id: p.id, name: p.name, price: Number(p.price), offer_price: p.offer_price ? Number(p.offer_price) : null, offer_label: p.offer_label || "", active: p.active }));
    try { const { data } = await api.put("/admin/settings", { ...rest, pricing_plans }); setSettings((s) => ({ ...s, ...data })); toast.success("Settings saved. New prices are live everywhere."); loadAnalytics(); }
    catch (err) { toast.error(err?.response?.data?.detail || "Could not save"); } finally { setBusy(false); }
  };

  const [exporting, setExporting] = useState(false);
  const exportChurn = async (level = "high_risk") => {
    setExporting(true);
    try {
      const res = await api.get("/admin/churn-export", { params: { health: level }, responseType: "blob" });
      downloadBlob(res.data, `churn-watchlist-${level}-${new Date().toISOString().slice(0, 10)}.csv`);
      toast.success("Churn watchlist downloaded");
    } catch { toast.error("Export failed"); } finally { setExporting(false); }
  };
  const setPlan = (id, patch) => setSettings((s) => ({ ...s, pricing_plans: s.pricing_plans.map((p) => (p.id === id ? { ...p, ...patch } : p)) }));

  const goToCustomers = (status = "all", health = "all") => { setStatusFilter(status); setHealthFilter(health); setTab("customers"); };

  const chartData = useMemo(() => (a?.series || []).slice(-range).map((p) => ({ ...p, name: fmtMonth(p.month) })), [a, range]);
  const k = a?.kpis; const rev = a?.revenue; const pay = a?.payments; const use = a?.usage; const tr = a?.trials;

  const funnel = a ? [
    { label: "Registered", value: a.funnel.registered },
    { label: "Trial Started", value: a.funnel.trial_started },
    { label: "Paid Customer", value: a.funnel.paid },
    { label: "Active (Retained)", value: a.funnel.retained_30d },
  ] : [];

  const actions = a ? [
    { n: tr.ending_3d, text: "trials expiring within 3 days", go: () => goToCustomers("trial"), danger: false },
    { n: pay.failed, text: "subscription payments failed", go: () => setTab("customers"), danger: true },
    { n: gyms ? gyms.filter((g) => g.health === "high_risk").length : (k.expired), text: "gyms at high churn risk", go: () => goToCustomers("all", "high_risk"), danger: true },
    { n: pay.renewals_this_week, text: "subscriptions renew this week", go: () => goToCustomers("active"), danger: false },
  ].filter((x) => x.n > 0) : [];

  const gymColumns = [
    { key: "name", label: "Gym", render: (g) => (<div><p className="font-semibold text-foreground">{g.name}{g.is_demo && <span className="ml-1.5 rounded bg-brand/10 px-1.5 py-0.5 text-[10px] font-semibold text-brand">DEMO</span>}</p><p className="text-xs text-muted-foreground">{g.owner?.full_name || "—"} · {g.owner?.email || g.owner?.phone || "—"}</p></div>) },
    { key: "status", label: "Status", render: (g) => <Badge cls={STATUS_CLS[g.subscription.status] || "bg-secondary"}>{g.subscription.status}</Badge> },
    { key: "health", label: "Health", render: (g) => <Badge cls={HEALTH[g.health].cls} testid={`gym-health-${g.id}`}>{HEALTH[g.health].label}</Badge> },
    { key: "mrr", label: "MRR", align: "right", render: (g) => <span className="font-num font-semibold text-foreground">{inr(g.monthly_revenue)}</span> },
    { key: "members", label: "Members", align: "right", render: (g) => <span className="font-num text-muted-foreground">{g.member_count}</span> },
    { key: "activity", label: "Last Activity", render: (g) => <span className="text-xs text-muted-foreground">{g.last_activity_days === null ? "—" : g.last_activity_days === 0 ? "Today" : `${g.last_activity_days}d ago`}</span> },
    { key: "actions", label: "", align: "right", render: (g) => (
      <div className="flex items-center justify-end gap-1">
        <button onClick={(e) => { e.stopPropagation(); openDetail(g); }} className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground" data-testid={`admin-view-${g.id}`} aria-label="View"><Eye className="h-4 w-4" /></button>
        <button onClick={(e) => { e.stopPropagation(); setToggleGym(g); }} className={`rounded-md p-1.5 ${g.disabled ? "text-success hover:bg-success/10" : "text-danger hover:bg-danger/10"}`} data-testid={`admin-toggle-${g.id}`} aria-label="Toggle"><Power className="h-4 w-4" /></button>
      </div>
    ) },
  ];

  return (
    <div className="min-h-screen bg-background" data-testid="superadmin-console">
      <header className="sticky top-0 z-20 border-b border-border bg-card/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3.5 sm:px-6">
          <div className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand text-white"><Zap className="h-5 w-5" /></span>
            <div><p className="font-display text-sm font-bold text-foreground">BuildVVO Admin</p><p className="text-xs text-muted-foreground">GymBoss_VVO Control Center</p></div>
          </div>
          <div className="flex items-center gap-2">
          <ThemeToggle testid="admin-theme-toggle" />
          <button onClick={async () => { await logout(); navigate("/login"); }} data-testid="admin-logout" className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-sm font-medium text-muted-foreground hover:text-foreground"><LogOut className="h-4 w-4" />Logout</button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList data-testid="admin-tabs">
            <TabsTrigger value="overview" data-testid="admin-tab-overview"><LayoutDashboard className="mr-1.5 h-4 w-4" />Overview</TabsTrigger>
            <TabsTrigger value="funnel" data-testid="admin-tab-funnel"><TrendingUp className="mr-1.5 h-4 w-4" />Funnel</TabsTrigger>
            <TabsTrigger value="customers" data-testid="admin-tab-customers"><Building2 className="mr-1.5 h-4 w-4" />Customers</TabsTrigger>
            <TabsTrigger value="settings" data-testid="admin-tab-settings"><SettingsIcon className="mr-1.5 h-4 w-4" />Settings</TabsTrigger>
            <TabsTrigger value="audit" data-testid="admin-tab-audit"><ScrollText className="mr-1.5 h-4 w-4" />Audit</TabsTrigger>
          </TabsList>

          {/* ---------------- OVERVIEW ---------------- */}
          <TabsContent value="overview" className="mt-6 space-y-6">
            {!a ? (
              <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">{Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-28 animate-pulse rounded-2xl bg-secondary" />)}</div>
            ) : (
              <>
                {/* Row 1 — Core metrics */}
                <div className="grid grid-cols-2 gap-4 lg:grid-cols-5" data-testid="admin-core-kpis">
                  <KPI primary label="MRR" value={inr(k.mrr)} delta={rev.growth} hint="vs last month" Icon={IndianRupee} testid="admin-kpi-mrr" />
                  <KPI primary label="Paying Customers" value={k.paying} Icon={Users} testid="admin-kpi-paying" />
                  <KPI primary label="Retention" value={`${k.retention_rate}%`} Icon={Activity} testid="admin-kpi-retention" />
                  <KPI primary label="Churn" value={`${k.churn_rate}%`} inverse Icon={TrendingDown} testid="admin-kpi-churn" />
                  <KPI primary label="Trial → Paid" value={`${k.trial_to_paid}%`} Icon={Repeat} testid="admin-kpi-trial-paid" />
                </div>

                {/* Secondary KPIs */}
                <div className="grid grid-cols-2 gap-4 lg:grid-cols-6" data-testid="admin-secondary-kpis">
                  <KPI label="ARR" value={inr(k.arr)} testid="admin-kpi-arr" />
                  <KPI label="Total Gyms" value={k.total_customers} testid="admin-kpi-total" />
                  <KPI label="On Free Trial" value={k.trial} testid="admin-kpi-trial" />
                  <KPI label="New This Month" value={k.new_this_month} delta={k.signup_growth} testid="admin-kpi-new" />
                  <KPI label="ARPU" value={inr(k.arpu)} testid="admin-kpi-arpu" />
                  <KPI label="Avg Lifetime" value={k.avg_lifetime_months ? `${k.avg_lifetime_months} mo` : "—"} testid="admin-kpi-lifetime" />
                </div>

                {/* Row 2 — Growth charts */}
                <div className="grid gap-4 lg:grid-cols-5">
                  <div className="lg:col-span-3">
                    <Card title="Revenue & Growth" subtitle="Collected SaaS revenue by month" testid="admin-revenue-chart"
                      action={<div className="flex flex-wrap items-center gap-1.5">
                        {METRICS.map((m) => <button key={m.v} onClick={() => setMetric(m.v)} data-testid={`admin-metric-${m.v}`} className={`rounded-full px-2.5 py-1 text-xs font-semibold ${metric === m.v ? "bg-brand text-white" : "bg-secondary text-muted-foreground"}`}>{m.l}</button>)}
                        <span className="mx-1 h-4 w-px bg-border" />
                        {RANGES.map((r) => <button key={r.v} onClick={() => setRange(r.v)} data-testid={`admin-range-${r.l}`} className={`rounded-full px-2.5 py-1 text-xs font-semibold ${range === r.v ? "bg-foreground text-background" : "bg-secondary text-muted-foreground"}`}>{r.l}</button>)}
                      </div>}>
                      <ResponsiveContainer width="100%" height={260}>
                        <AreaChart data={chartData} margin={{ left: -10, right: 8, top: 4 }}>
                          <defs><linearGradient id="gRev" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#7C3AED" stopOpacity={0.35} /><stop offset="100%" stopColor="#7C3AED" stopOpacity={0} /></linearGradient></defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-border" vertical={false} />
                          <XAxis dataKey="name" tick={{ fontSize: 11 }} stroke="currentColor" className="text-muted-foreground" />
                          <YAxis tick={{ fontSize: 11 }} stroke="currentColor" className="text-muted-foreground" width={54} tickFormatter={(v) => metric === "revenue" ? `₹${v >= 1000 ? (v / 1000) + "k" : v}` : v} />
                          <Tooltip formatter={(v) => metric === "revenue" ? inr(v) : v} contentStyle={{ borderRadius: 12, border: "1px solid var(--border)", background: "var(--card)" }} />
                          <Area type="monotone" dataKey={metric} stroke="#7C3AED" strokeWidth={2.5} fill="url(#gRev)" />
                        </AreaChart>
                      </ResponsiveContainer>
                      <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                        <div><p className="text-xs text-muted-foreground">This Month</p><p className="font-num text-sm font-bold text-foreground">{inr(rev.this_month)}</p></div>
                        <div><p className="text-xs text-muted-foreground">Growth</p><p className="font-num text-sm font-bold"><Delta value={rev.growth} /></p></div>
                        <div><p className="text-xs text-muted-foreground">Lifetime</p><p className="font-num text-sm font-bold text-foreground">{inr(rev.lifetime)}</p></div>
                      </div>
                    </Card>
                  </div>
                  <div className="lg:col-span-2">
                    <Card title="Customer Growth" subtitle="Total gyms over time" testid="admin-growth-chart">
                      <ResponsiveContainer width="100%" height={260}>
                        <LineChart data={chartData} margin={{ left: -18, right: 8, top: 4 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-border" vertical={false} />
                          <XAxis dataKey="name" tick={{ fontSize: 11 }} stroke="currentColor" className="text-muted-foreground" />
                          <YAxis tick={{ fontSize: 11 }} stroke="currentColor" className="text-muted-foreground" width={30} />
                          <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid var(--border)", background: "var(--card)" }} />
                          <Line type="monotone" dataKey="total_customers" stroke="#10b981" strokeWidth={2.5} dot={false} name="Total" />
                          <Line type="monotone" dataKey="new_customers" stroke="#7C3AED" strokeWidth={2} dot={false} name="New" />
                        </LineChart>
                      </ResponsiveContainer>
                    </Card>
                  </div>
                </div>

                {/* Row 3 — Trial funnel */}
                <Card title="Trial → Paid Funnel" subtitle={`Converted ${a.funnel.converted_trials} · ${tr.ending_today} ending today · ${tr.ending_7d} in 7 days`} testid="admin-funnel">
                  <div className="space-y-2.5">
                    {funnel.map((s, i) => { const top = funnel[0].value || 1; const w = Math.round(100 * s.value / top); const conv = i === 0 ? 100 : Math.round(100 * s.value / (funnel[i - 1].value || 1));
                      return (
                        <div key={s.label} data-testid={`funnel-${i}`}>
                          <div className="mb-1 flex items-center justify-between text-sm"><span className="font-medium text-foreground">{s.label}</span><span className="text-muted-foreground"><span className="font-num font-bold text-foreground">{s.value}</span> · {conv}%</span></div>
                          <div className="h-3 overflow-hidden rounded-full bg-secondary"><div className="h-full rounded-full bg-gradient-to-r from-brand to-[#5B21B6]" style={{ width: `${w}%` }} /></div>
                        </div>
                      ); })}
                  </div>
                </Card>

                {/* Row 4 — Payments + Row 5 usage */}
                <div className="grid gap-4 lg:grid-cols-2">
                  <Card title="Payment Analytics" subtitle="Subscription billing (Razorpay)" testid="admin-payments">
                    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                      {[
                        { l: "Successful", v: pay.successful, c: "text-success" },
                        { l: "Failed", v: pay.failed, c: "text-danger" },
                        { l: "Pending", v: pay.pending, c: "text-warning" },
                        { l: "Success Rate", v: `${pay.success_rate}%`, c: "text-foreground" },
                        { l: "Renews This Week", v: pay.renewals_this_week, c: "text-foreground" },
                        { l: "Expired Subs", v: pay.expired_subscriptions, c: "text-muted-foreground" },
                      ].map((x) => <div key={x.l} className="rounded-xl border border-border p-3"><p className="text-xs text-muted-foreground">{x.l}</p><p className={`font-num text-lg font-bold ${x.c}`}>{x.v}</p></div>)}
                    </div>
                    <p className="mt-3 text-xs text-muted-foreground">Revenue collected (lifetime): <span className="font-num font-semibold text-foreground">{inr(pay.revenue_collected)}</span></p>
                  </Card>

                  <Card title="Product Usage" subtitle="Active gyms by recent payment activity (login tracking not available)" testid="admin-usage">
                    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                      {[
                        { l: "Daily Active", v: use.dau }, { l: "Weekly Active", v: use.wau }, { l: "Monthly Active", v: use.mau },
                        { l: "Members Managed", v: use.total_members }, { l: "Members (mo)", v: use.members_this_month }, { l: "Payments Logged", v: use.member_payments },
                        { l: "Check-ins Today", v: use.attendance_today }, { l: "Check-ins (mo)", v: use.attendance_month }, { l: "Biometric Devices", v: use.biometric_devices },
                      ].map((x) => <div key={x.l} className="rounded-xl border border-border p-3"><p className="text-xs text-muted-foreground">{x.l}</p><p className="font-num text-lg font-bold text-foreground">{x.v}</p></div>)}
                    </div>
                  </Card>
                </div>

                {/* Row 6 — Action required */}
                <Card title="Action Required" subtitle="Things needing your attention today" testid="admin-actions"
                  action={<Button size="sm" variant="outline" onClick={() => exportChurn("high_risk")} disabled={exporting} data-testid="admin-actions-export">{exporting ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : <Download className="mr-1.5 h-3.5 w-3.5" />}Churn CSV</Button>}>
                  {actions.length === 0 ? (
                    <p className="py-6 text-center text-sm text-muted-foreground" data-testid="admin-actions-empty">All clear — nothing needs attention right now.</p>
                  ) : (
                    <div className="space-y-2">
                      {actions.map((x, i) => (
                        <button key={i} onClick={x.go} data-testid={`admin-action-${i}`} className="flex w-full items-center justify-between rounded-xl border border-border px-4 py-3 text-left transition-colors hover:bg-secondary">
                          <span className="flex items-center gap-2.5 text-sm font-medium text-foreground"><AlertTriangle className={`h-4 w-4 ${x.danger ? "text-danger" : "text-warning"}`} /><span className="font-num font-bold">{x.n}</span> {x.text}</span>
                          <Eye className="h-4 w-4 text-muted-foreground" />
                        </button>
                      ))}
                    </div>
                  )}
                </Card>

                <p className="text-center text-xs text-muted-foreground">Not tracked yet: marketing source / CAC, website visitors, per-user logins, WhatsApp-sent & retention cohorts. These need event tracking to be added before they can be shown accurately.</p>
              </>
            )}
          </TabsContent>

          {/* ---------------- CUSTOMERS ---------------- */}
          <TabsContent value="customers" className="mt-6">
            <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex flex-wrap items-center gap-2">
                <SearchInput value={search} onChange={setSearch} placeholder="Search gyms…" testid="admin-search" />
                <Button size="sm" className="bg-brand hover:bg-brand-hover" onClick={() => exportChurn("high_risk")} disabled={exporting} data-testid="admin-export-churn">
                  {exporting ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : <Download className="mr-1.5 h-3.5 w-3.5" />}Export churn watchlist
                </Button>
                <Button size="sm" variant="outline" onClick={() => exportChurn("all_risk")} disabled={exporting} data-testid="admin-export-churn-all">Incl. at-risk</Button>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {[["all", "All"], ["active", "Active"], ["trial", "Trial"], ["expired", "Expired"], ["cancelled", "Cancelled"]].map(([v, l]) => (
                  <button key={v} onClick={() => setStatusFilter(v)} data-testid={`filter-status-${v}`} className={`rounded-full px-3 py-1.5 text-xs font-semibold ${statusFilter === v ? "bg-brand text-white" : "border border-border bg-card text-muted-foreground"}`}>{l}</button>
                ))}
                <span className="mx-1 h-6 w-px bg-border" />
                {[["all", "All Health"], ["healthy", "Healthy"], ["at_risk", "At Risk"], ["high_risk", "High Risk"], ["churned", "Churned"]].map(([v, l]) => (
                  <button key={v} onClick={() => setHealthFilter(v)} data-testid={`filter-health-${v}`} className={`rounded-full px-3 py-1.5 text-xs font-semibold ${healthFilter === v ? "bg-foreground text-background" : "border border-border bg-card text-muted-foreground"}`}>{l}</button>
                ))}
              </div>
            </div>
            <DataTable testid="admin-gyms-table" columns={gymColumns} rows={gyms || []} loading={!gyms} onRowClick={openDetail} empty="No gyms match these filters" />
          </TabsContent>

          {/* ---------------- SETTINGS ---------------- */}
          <TabsContent value="funnel" className="mt-6"><FunnelTab /></TabsContent>
          <TabsContent value="settings" className="mt-6">
            <form onSubmit={saveSettings} className="max-w-lg space-y-4 rounded-2xl border border-border bg-card p-6 shadow-card" data-testid="admin-settings-form">
              <div className="space-y-1.5"><Label>Support WhatsApp Number</Label><Input value={settings.whatsapp_number} onChange={(e) => setSettings({ ...settings, whatsapp_number: e.target.value })} placeholder="e.g., 919876543210" data-testid="settings-whatsapp" /></div>
              <div className="space-y-1.5"><Label>Support Email</Label><Input type="email" value={settings.support_email} onChange={(e) => setSettings({ ...settings, support_email: e.target.value })} placeholder="support@buildvvo.com" data-testid="settings-support-email" /></div>
              <div className="space-y-1.5"><Label>Google Play URL</Label><Input value={settings.play_store_url} onChange={(e) => setSettings({ ...settings, play_store_url: e.target.value })} data-testid="settings-play-store" /></div>
              <div className="space-y-1.5"><Label>App Store URL</Label><Input value={settings.app_store_url} onChange={(e) => setSettings({ ...settings, app_store_url: e.target.value })} data-testid="settings-app-store" /></div>
              <div className="rounded-xl border border-border p-4" data-testid="settings-pricing">
                <p className="text-sm font-semibold text-foreground">Subscription Plans & Offers</p>
                <p className="mb-3 text-xs text-muted-foreground">Changes update the landing page, the gym app, the mobile app and Razorpay checkout instantly.</p>
                <div className="space-y-3">
                  {(settings.pricing_plans || []).map((p) => (
                    <div key={p.id} className="rounded-lg bg-secondary/50 p-3" data-testid={`settings-plan-${p.id}`}>
                      <div className="mb-2 flex items-center justify-between">
                        <p className="text-sm font-bold text-foreground">{p.name} <span className="font-normal text-muted-foreground">· {p.months} month{p.months > 1 ? "s" : ""}</span></p>
                        {p.id !== "monthly" && <label className="flex items-center gap-2 text-xs text-muted-foreground">Show<Switch checked={p.active} onCheckedChange={(v) => setPlan(p.id, { active: v })} data-testid={`settings-plan-active-${p.id}`} /></label>}
                      </div>
                      <div className="grid grid-cols-3 gap-2">
                        <div className="space-y-1"><Label className="text-xs">Price (₹)</Label><Input type="number" min="1" value={p.price} onChange={(e) => setPlan(p.id, { price: e.target.value })} data-testid={`settings-plan-price-${p.id}`} /></div>
                        <div className="space-y-1"><Label className="text-xs">Offer price</Label><Input type="number" min="1" value={p.offer_price || ""} placeholder="None" onChange={(e) => setPlan(p.id, { offer_price: e.target.value })} data-testid={`settings-plan-offer-${p.id}`} /></div>
                        <div className="space-y-1"><Label className="text-xs">Offer label</Label><Input value={p.offer_label || ""} maxLength={40} placeholder="e.g. Launch offer" onChange={(e) => setPlan(p.id, { offer_label: e.target.value })} data-testid={`settings-plan-label-${p.id}`} /></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded-xl border border-border p-4">
                <p className="mb-3 text-sm font-semibold text-foreground">Razorpay</p>
                <div className="space-y-3">
                  <div className="space-y-1.5"><Label>Key ID</Label><Input value={settings.razorpay_key_id} onChange={(e) => setSettings({ ...settings, razorpay_key_id: e.target.value })} placeholder="rzp_test_..." data-testid="settings-razorpay-key-id" /></div>
                  <div className="space-y-1.5"><Label>Key Secret</Label><Input type="password" value={settings.razorpay_key_secret} onChange={(e) => setSettings({ ...settings, razorpay_key_secret: e.target.value })} placeholder="••••••••" data-testid="settings-razorpay-secret" /></div>
                  <div className="space-y-1.5"><Label>Webhook Secret</Label><Input type="password" value={settings.razorpay_webhook_secret} onChange={(e) => setSettings({ ...settings, razorpay_webhook_secret: e.target.value })} placeholder="••••••••" data-testid="settings-razorpay-webhook" /></div>
                </div>
              </div>
              <Button className="bg-brand hover:bg-brand-hover" disabled={busy} data-testid="admin-settings-save">Save Settings</Button>
            </form>
          </TabsContent>

          {/* ---------------- AUDIT ---------------- */}
          <TabsContent value="audit" className="mt-6">
            <div className="rounded-2xl border border-border bg-card shadow-card" data-testid="admin-audit-logs">
              {logs.length === 0 ? <p className="py-10 text-center text-sm text-muted-foreground">No activity yet</p> : logs.map((log) => (
                <div key={log.id} className="flex items-center justify-between border-b border-border px-5 py-3 text-sm last:border-0" data-testid={`audit-${log.id}`}>
                  <span className="font-medium text-foreground">{log.action}</span>
                  <span className="text-xs text-muted-foreground">{log.created_at ? new Date(log.created_at).toLocaleString("en-IN") : ""}</span>
                </div>
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </main>

      {/* Gym detail */}
      <Dialog open={!!detail} onOpenChange={(o) => !o && setDetail(null)}>
        <DialogContent className="max-w-lg" data-testid="admin-gym-detail">
          {detail && (
            <>
              <DialogHeader><DialogTitle className="font-display text-lg">{detail.organisation?.name}</DialogTitle></DialogHeader>
              <div className="space-y-3 text-sm">
                <div className="flex flex-wrap gap-2">
                  <Badge cls={STATUS_CLS[detail.subscription.status] || "bg-secondary"}>{detail.subscription.status}</Badge>
                  {detail.subscription.trial_days_left > 0 && <Badge cls="bg-brand/15 text-brand">{detail.subscription.trial_days_left} trial days left</Badge>}
                </div>
                <Row label="Owner" value={`${detail.owner?.full_name || "—"} · ${detail.owner?.email || "—"}`} />
                <Row label="Phone" value={detail.owner?.phone || "—"} />
                <Row label="City" value={detail.organisation?.city || "—"} />
                <Row label="Members / Staff" value={`${detail.stats?.members} / ${detail.stats?.staff}`} />
                <Row label="Member collection" value={inr(detail.stats?.collection_total || 0)} />
                <Row label="Signed up" value={detail.organisation?.created_at ? new Date(detail.organisation.created_at).toLocaleDateString("en-IN") : "—"} />
                {detail.subscription_payments?.length > 0 && (
                  <div>
                    <p className="mb-1 mt-2 text-xs font-semibold uppercase text-muted-foreground">Subscription payments</p>
                    <div className="max-h-40 space-y-1 overflow-y-auto">
                      {detail.subscription_payments.map((p, i) => (
                        <div key={i} className="flex justify-between rounded-lg bg-secondary px-3 py-1.5 text-xs"><span>{inr(p.amount)} · {p.status}</span><span className="text-muted-foreground">{p.paid_at ? new Date(p.paid_at).toLocaleDateString("en-IN") : "—"}</span></div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>

      <ConfirmDialog open={!!toggleGym} onClose={() => setToggleGym(null)} onConfirm={doToggle} busy={busy}
        testid="admin-toggle-confirm" title={toggleGym?.disabled ? `Reactivate ${toggleGym?.name}?` : `Disable ${toggleGym?.name}?`}
        description={toggleGym?.disabled ? "The gym will regain access immediately." : "The gym's owner and staff will lose access until reactivated."}
        confirmLabel={toggleGym?.disabled ? "Reactivate" : "Disable"} />
    </div>
  );
}

function Row({ label, value }) {
  return <div className="flex justify-between gap-4"><span className="text-muted-foreground">{label}</span><span className="text-right font-medium text-foreground">{value}</span></div>;
}
