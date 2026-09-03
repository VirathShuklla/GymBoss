import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ShieldCheck, LogOut, Building2, IndianRupee, TrendingUp, Users, Power, Eye, Settings as SettingsIcon, ScrollText } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../lib/api";
import { inr, formatDate } from "../lib/format";
import { useAuth } from "../contexts/AuthContext";
import { Logo } from "../components/Logo";
import { DataTable, StatusBadge, EmptyState, SearchInput, ConfirmDialog } from "../components/app/ui";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "../components/ui/sheet";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";

export default function SuperAdmin() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [overview, setOverview] = useState(null);
  const [gyms, setGyms] = useState(null);
  const [search, setSearch] = useState("");
  const [detail, setDetail] = useState(null);
  const [toggleGym, setToggleGym] = useState(null);
  const [busy, setBusy] = useState(false);
  const [settings, setSettings] = useState({ whatsapp_number: "", support_email: "", play_store_url: "", app_store_url: "" });
  const [logs, setLogs] = useState([]);

  const loadOverview = async () => {
    const { data } = await api.get("/admin/overview");
    setOverview(data);
  };
  const loadGyms = async () => {
    const { data } = await api.get("/admin/gyms", { params: { search: search || undefined } });
    setGyms(data);
  };
  useEffect(() => {
    loadOverview(); loadGyms();
    api.get("/admin/settings").then(({ data }) => setSettings((s) => ({ ...s, ...data })));
    api.get("/admin/audit-logs").then(({ data }) => setLogs(data));
  }, []);
  useEffect(() => {
    const t = setTimeout(loadGyms, 350);
    return () => clearTimeout(t);
  }, [search]);

  const openDetail = async (g) => {
    const { data } = await api.get(`/admin/gyms/${g.id}`);
    setDetail(data);
  };

  const doToggle = async () => {
    setBusy(true);
    try {
      await api.post(`/admin/gyms/${toggleGym.id}/toggle`);
      toast.success(toggleGym.disabled ? "Account reactivated" : "Account disabled");
      setToggleGym(null);
      loadGyms(); loadOverview();
      api.get("/admin/audit-logs").then(({ data }) => setLogs(data));
    } catch (e) {
      toast.error(apiError(e));
    } finally {
      setBusy(false);
    }
  };

  const saveSettings = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.put("/admin/settings", settings);
      toast.success("Platform settings saved");
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setBusy(false);
    }
  };

  const cards = [
    { label: "Total Gyms", value: overview?.total_gyms, icon: Building2, color: "text-brand", tile: "bg-brand/12" },
    { label: "On Trial", value: overview?.trial, icon: Users, color: "text-info", tile: "bg-info/12" },
    { label: "Paying", value: overview?.paying, icon: ShieldCheck, color: "text-success", tile: "bg-success/12" },
    { label: "Expired", value: overview?.expired, icon: Power, color: "text-warning", tile: "bg-warning/12" },
    { label: "MRR", value: overview ? inr(overview.mrr) : "—", icon: IndianRupee, color: "text-brand", tile: "bg-brand/12" },
    { label: "Subscription Revenue", value: overview ? inr(overview.subscription_revenue) : "—", icon: IndianRupee, color: "text-success", tile: "bg-success/12" },
    { label: "Trial → Paid", value: overview ? `${overview.trial_to_paid}%` : "—", icon: TrendingUp, color: "text-info", tile: "bg-info/12" },
    { label: "New Signups (30d)", value: overview?.new_signups_30d, icon: Users, color: "text-warning", tile: "bg-warning/12" },
  ];

  const gymColumns = [
    { key: "name", label: "Gym", render: (g) => (
      <div>
        <p className="font-medium text-foreground">{g.name} {g.is_demo && <span className="ml-1 rounded-full bg-secondary px-2 py-0.5 text-[10px] font-bold text-muted-foreground">DEMO</span>}</p>
        <p className="text-xs text-muted-foreground">{g.city || "—"}</p>
      </div>
    )},
    { key: "owner", label: "Owner", render: (g) => (
      <div><p className="text-foreground">{g.owner?.full_name || "—"}</p><p className="text-xs text-muted-foreground">{g.owner?.phone || g.owner?.email || ""}</p></div>
    )},
    { key: "created_at", label: "Registered", render: (g) => formatDate(g.created_at) },
    { key: "member_count", label: "Members", align: "right", render: (g) => <span className="font-num">{g.member_count}</span> },
    { key: "subscription", label: "Trial/Sub Ends", render: (g) => formatDate(g.subscription.status === "active" ? g.subscription.subscription_ends_at : g.subscription.trial_ends_at) },
    { key: "status", label: "Status", render: (g) => (
      g.disabled ? <StatusBadge status="disabled" /> :
      g.subscription.status === "trial" ? <span className="badge-status badge-frozen">Trial · {g.subscription.trial_days_left}d left</span> :
      <StatusBadge status={g.subscription.status} label={g.subscription.status === "active" ? "Paying" : g.subscription.status === "expired" ? "Expired" : g.subscription.status} />
    )},
    { key: "actions", label: "", align: "right", render: (g) => (
      <div className="flex justify-end gap-1">
        <button onClick={(e) => { e.stopPropagation(); openDetail(g); }} className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground" data-testid={`admin-view-${g.id}`} aria-label="View"><Eye className="h-4 w-4" /></button>
        <button onClick={(e) => { e.stopPropagation(); setToggleGym(g); }} className={`rounded-md p-1.5 ${g.disabled ? "text-success hover:bg-success/10" : "text-danger hover:bg-danger/10"}`} data-testid={`admin-toggle-${g.id}`} aria-label="Toggle"><Power className="h-4 w-4" /></button>
      </div>
    )},
  ];

  return (
    <div className="min-h-screen bg-background" data-testid="superadmin-console">
      <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border bg-card px-4 sm:px-8">
        <div className="flex items-center gap-4">
          <Logo />
          <span className="rounded-full bg-brand/12 px-3 py-1 text-xs font-bold text-brand">BuildVVO Super Admin</span>
        </div>
        <button onClick={async () => { await logout(); navigate("/login"); }} data-testid="admin-logout"
                className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-semibold text-foreground hover:bg-secondary">
          <LogOut className="h-4 w-4" />Logout
        </button>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-8">
        <h1 className="font-display text-2xl font-bold tracking-tight text-foreground">Platform Overview</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">GymBoss_VVO registrations, trials and revenue.</p>

        <div className="mt-6 grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4" data-testid="admin-overview-cards">
          {cards.map((c) => (
            <div key={c.label} className="rounded-xl border border-border bg-card p-4 shadow-card" data-testid={`admin-kpi-${c.label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
              <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${c.tile}`}><c.icon className={`h-[18px] w-[18px] ${c.color}`} /></div>
              <p className="mt-3 text-xs font-medium text-muted-foreground">{c.label}</p>
              <p className={`font-num mt-1 text-xl font-bold ${c.color}`}>{c.value ?? "—"}</p>
            </div>
          ))}
        </div>

        <Tabs defaultValue="gyms" className="mt-8">
          <TabsList data-testid="admin-tabs">
            <TabsTrigger value="gyms" data-testid="admin-tab-gyms"><Building2 className="mr-1.5 h-4 w-4" />Gyms</TabsTrigger>
            <TabsTrigger value="settings" data-testid="admin-tab-settings"><SettingsIcon className="mr-1.5 h-4 w-4" />Platform Settings</TabsTrigger>
            <TabsTrigger value="audit" data-testid="admin-tab-audit"><ScrollText className="mr-1.5 h-4 w-4" />Audit Logs</TabsTrigger>
          </TabsList>

          <TabsContent value="gyms" className="mt-5">
            <div className="mb-4 w-full sm:w-72"><SearchInput value={search} onChange={setSearch} placeholder="Search gyms" testid="admin-gym-search" /></div>
            <DataTable testid="admin-gyms-table" columns={gymColumns} rows={gyms || []} loading={!gyms} onRowClick={openDetail}
                       empty={<EmptyState icon={Building2} title="No gyms registered yet" testid="admin-gyms-empty" />} />
          </TabsContent>

          <TabsContent value="settings" className="mt-5">
            <form onSubmit={saveSettings} className="max-w-lg space-y-4 rounded-xl border border-border bg-card p-6 shadow-card" data-testid="admin-settings-form">
              <p className="text-sm text-muted-foreground">These power the public website's floating WhatsApp button, support page and app store links.</p>
              <div className="space-y-1.5"><Label>Support WhatsApp Number</Label><Input value={settings.whatsapp_number} onChange={(e) => setSettings({ ...settings, whatsapp_number: e.target.value })} placeholder="e.g., 919876543210" data-testid="settings-whatsapp" /></div>
              <div className="space-y-1.5"><Label>Support Email</Label><Input type="email" value={settings.support_email} onChange={(e) => setSettings({ ...settings, support_email: e.target.value })} placeholder="support@buildvvo.com" data-testid="settings-support-email" /></div>
              <div className="space-y-1.5"><Label>Google Play URL <span className="font-normal text-muted-foreground">(when live)</span></Label><Input value={settings.play_store_url} onChange={(e) => setSettings({ ...settings, play_store_url: e.target.value })} data-testid="settings-play-store" /></div>
              <div className="space-y-1.5"><Label>App Store URL <span className="font-normal text-muted-foreground">(when live)</span></Label><Input value={settings.app_store_url} onChange={(e) => setSettings({ ...settings, app_store_url: e.target.value })} data-testid="settings-app-store" /></div>
              <Button className="bg-brand hover:bg-brand-hover" disabled={busy} data-testid="admin-settings-save">Save Settings</Button>
            </form>
          </TabsContent>

          <TabsContent value="audit" className="mt-5">
            <div className="rounded-xl border border-border bg-card shadow-card" data-testid="admin-audit-logs">
              {logs.length === 0 ? (
                <EmptyState icon={ScrollText} title="No audit events yet" testid="audit-empty" />
              ) : (
                <div className="divide-y divide-border/60">
                  {logs.map((log) => (
                    <div key={log.id} className="flex items-center justify-between px-5 py-3 text-sm" data-testid={`audit-${log.id}`}>
                      <div>
                        <p className="font-medium text-foreground">{log.action}</p>
                        <p className="font-num text-xs text-muted-foreground">{log.target}</p>
                      </div>
                      <span className="text-xs text-muted-foreground">{formatDate(log.created_at)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </main>

      <Sheet open={Boolean(detail)} onOpenChange={(o) => !o && setDetail(null)}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-md" data-testid="admin-gym-detail">
          {detail && (
            <div>
              <SheetHeader><SheetTitle className="font-display text-lg">{detail.organisation.name}</SheetTitle></SheetHeader>
              <div className="mt-4 space-y-4">
                <div className="rounded-xl border border-border p-4 text-sm">
                  <p className="pb-2 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Owner</p>
                  <p className="font-semibold text-foreground">{detail.owner?.full_name}</p>
                  <p className="text-muted-foreground">{detail.owner?.email}</p>
                  <p className="font-num text-muted-foreground">{detail.owner?.phone}</p>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center">
                  {[["Members", detail.stats.members], ["Staff", detail.stats.staff], ["Collections", inr(detail.stats.collection_total)]].map(([l, v]) => (
                    <div key={l} className="rounded-lg border border-border p-3">
                      <p className="text-[10px] font-bold uppercase text-muted-foreground">{l}</p>
                      <p className="font-num mt-1 font-bold text-foreground">{v}</p>
                    </div>
                  ))}
                </div>
                <div className="rounded-xl border border-border p-4 text-sm">
                  <p className="pb-2 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Subscription</p>
                  <div className="flex items-center justify-between">
                    <StatusBadge status={detail.subscription.status} label={detail.subscription.status} />
                    <span className="font-num text-xs text-muted-foreground">
                      {detail.subscription.status === "trial" ? `${detail.subscription.trial_days_left} days left` : detail.subscription.subscription_ends_at ? `until ${formatDate(detail.subscription.subscription_ends_at)}` : ""}
                    </span>
                  </div>
                </div>
                <div className="rounded-xl border border-border p-4 text-sm">
                  <p className="pb-2 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Outlets</p>
                  {detail.outlets.map((o) => (
                    <p key={o.id} className="py-0.5 text-foreground">{o.name} <span className="text-xs text-muted-foreground">{o.city || ""}</span></p>
                  ))}
                </div>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>

      <ConfirmDialog open={Boolean(toggleGym)} onClose={() => setToggleGym(null)} onConfirm={doToggle} busy={busy}
                     testid="admin-toggle-confirm"
                     title={toggleGym?.disabled ? `Reactivate ${toggleGym?.name}?` : `Disable ${toggleGym?.name}?`}
                     description={toggleGym?.disabled ? "The gym's team will regain access immediately." : "The gym's team will lose access to the app. Their data remains safe and untouched."}
                     confirmLabel={toggleGym?.disabled ? "Reactivate" : "Disable Account"} />
    </div>
  );
}
