import { useEffect, useState } from "react";
import { Plus, Megaphone, Loader2, MessageCircle, Trash2, Eye } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { formatDate } from "../../lib/format";
import { waMe } from "../../lib/whatsapp";
import { useAuth } from "../../contexts/AuthContext";
import { PageHeader, DataTable, StatusBadge, EmptyState, DateField } from "../../components/app/ui";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../../components/ui/dialog";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "../../components/ui/sheet";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";

const AUDIENCES = [
  { value: "all_active", label: "All Active Members" },
  { value: "all", label: "All Members" },
  { value: "outlet", label: "Selected Outlet" },
  { value: "plan", label: "Selected Plan" },
  { value: "expiring_soon", label: "Memberships Expiring Soon (7 days)" },
];

const PLACEHOLDERS = ["{member_name}", "{gym_name}", "{outlet_name}", "{plan_name}", "{expiry_date}"];

export default function Announcements() {
  const { outlets } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [plans, setPlans] = useState([]);
  const [composerOpen, setComposerOpen] = useState(false);
  const [preview, setPreview] = useState(null);
  const [detail, setDetail] = useState(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ title: "", message: "", audience: "all_active", outlet_id: "", plan_id: "", scheduled_at: "" });

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/announcements");
      setItems(data);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);
  useEffect(() => { api.get("/plans", { params: { type: "membership" } }).then(({ data }) => setPlans(data)); }, []);

  const openPreview = async () => {
    if (form.title.trim().length < 2 || form.message.trim().length < 2) return toast.error("Enter a title and message");
    setBusy(true);
    try {
      const { data } = await api.post("/announcements/audience-count", {
        audience: form.audience,
        outlet_id: form.audience === "outlet" ? form.outlet_id : undefined,
        plan_id: form.audience === "plan" ? form.plan_id : undefined,
      });
      setPreview({ ...form, count: data.count });
    } catch (e) {
      toast.error(apiError(e));
    } finally {
      setBusy(false);
    }
  };

  const send = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/announcements", {
        title: form.title, message: form.message, audience: form.audience,
        outlet_id: form.audience === "outlet" ? form.outlet_id || undefined : undefined,
        plan_id: form.audience === "plan" ? form.plan_id || undefined : undefined,
        scheduled_at: form.scheduled_at || undefined,
      });
      const status = data.announcement.status;
      if (status === "scheduled") {
        toast.success("Announcement scheduled");
      } else if (status === "integration_required") {
        toast.warning("WhatsApp integration is required to send bulk announcements. Open Settings → Integrations to connect the official WhatsApp Business API.", { duration: 6000 });
      } else {
        toast.success("Announcement queued for delivery");
      }
      setPreview(null); setComposerOpen(false);
      setForm({ title: "", message: "", audience: "all_active", outlet_id: "", plan_id: "", scheduled_at: "" });
      load();
    } catch (e) {
      toast.error(apiError(e));
    } finally {
      setBusy(false);
    }
  };

  const openDetail = async (a) => {
    const { data } = await api.get(`/announcements/${a.id}`);
    setDetail(data);
  };

  const cancel = async (a) => {
    try {
      await api.delete(`/announcements/${a.id}`);
      toast.success("Announcement cancelled");
      load();
    } catch (e) {
      toast.error(apiError(e));
    }
  };

  const columns = [
    { key: "title", label: "Announcement", render: (a) => (
      <div><p className="font-medium text-foreground">{a.title}</p><p className="max-w-xs truncate text-xs text-muted-foreground">{a.message}</p></div>
    )},
    { key: "created_at", label: "Created", render: (a) => formatDate(a.created_at) },
    { key: "audience", label: "Audience", render: (a) => AUDIENCES.find((x) => x.value === a.audience)?.label || a.audience },
    { key: "channel", label: "Channel", render: () => "WhatsApp" },
    { key: "recipient_count", label: "Recipients", align: "right", render: (a) => <span className="font-num font-bold text-foreground">{a.recipient_count}</span> },
    { key: "created_by_name", label: "Created By", render: (a) => a.created_by_name || "—" },
    { key: "status", label: "Status", render: (a) => <StatusBadge status={a.status} /> },
  ];

  return (
    <div data-testid="announcements-page">
      <PageHeader title="Announcements" subtitle="Send updates to your members over WhatsApp." testid="announcements-header">
        <Button className="bg-brand hover:bg-brand-hover" onClick={() => setComposerOpen(true)} data-testid="create-announcement-button">
          <Plus className="mr-1.5 h-4 w-4" />Create Announcement
        </Button>
      </PageHeader>
      <DataTable testid="announcements-table" columns={columns} rows={items} loading={loading} onRowClick={openDetail}
                 empty={<EmptyState icon={Megaphone} title="No announcements yet" description="Create your first announcement — e.g., a holiday notice."
                                    action={<Button className="bg-brand hover:bg-brand-hover" onClick={() => setComposerOpen(true)} data-testid="empty-create-announcement"><Plus className="mr-1.5 h-4 w-4" />Create Announcement</Button>} testid="announcements-empty" />} />

      <Dialog open={composerOpen} onOpenChange={setComposerOpen}>
        <DialogContent className="max-w-lg" data-testid="announcement-composer">
          <DialogHeader><DialogTitle className="font-display text-lg">Create Announcement</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5"><Label>Title</Label><Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="e.g., Holiday Announcement" data-testid="announcement-title" /></div>
            <div className="space-y-1.5">
              <Label>Message</Label>
              <Textarea rows={4} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })}
                        placeholder="Dear members, the gym will remain closed tomorrow due to the holiday." data-testid="announcement-message" />
              <div className="flex flex-wrap gap-1.5">
                {PLACEHOLDERS.map((p) => (
                  <button key={p} type="button" onClick={() => setForm({ ...form, message: form.message + " " + p })}
                          className="rounded-md bg-secondary px-2 py-1 font-num text-[11px] text-muted-foreground hover:bg-elevated hover:text-foreground" data-testid={`placeholder-${p.slice(1, -1)}`}>
                    {p}
                  </button>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Audience</Label>
                <Select value={form.audience} onValueChange={(v) => setForm({ ...form, audience: v })}>
                  <SelectTrigger data-testid="announcement-audience"><SelectValue /></SelectTrigger>
                  <SelectContent>{AUDIENCES.map((a) => <SelectItem key={a.value} value={a.value} data-testid={`audience-${a.value}`}>{a.label}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Channel</Label>
                <Select value="whatsapp" disabled>
                  <SelectTrigger data-testid="announcement-channel"><SelectValue placeholder="WhatsApp" /></SelectTrigger>
                  <SelectContent><SelectItem value="whatsapp">WhatsApp</SelectItem></SelectContent>
                </Select>
              </div>
            </div>
            {form.audience === "outlet" && (
              <div className="space-y-1.5">
                <Label>Outlet</Label>
                <Select value={form.outlet_id} onValueChange={(v) => setForm({ ...form, outlet_id: v })}>
                  <SelectTrigger data-testid="announcement-outlet"><SelectValue placeholder="Select outlet" /></SelectTrigger>
                  <SelectContent>{outlets.map((o) => <SelectItem key={o.id} value={o.id}>{o.name}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            )}
            {form.audience === "plan" && (
              <div className="space-y-1.5">
                <Label>Plan</Label>
                <Select value={form.plan_id} onValueChange={(v) => setForm({ ...form, plan_id: v })}>
                  <SelectTrigger data-testid="announcement-plan"><SelectValue placeholder="Select plan" /></SelectTrigger>
                  <SelectContent>{plans.map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            )}
            <div className="space-y-1.5">
              <Label>Schedule <span className="font-normal text-muted-foreground">(leave empty to send now)</span></Label>
              <div className="grid grid-cols-2 gap-3">
                <DateField value={form.scheduled_at ? form.scheduled_at.slice(0, 10) : ""} onChange={(v) => setForm({ ...form, scheduled_at: v ? `${v}T${form.scheduled_at?.slice(11) || "09:00"}` : "" })} testid="announcement-schedule-date" placeholder="Select date" />
                <Input type="time" value={form.scheduled_at ? form.scheduled_at.slice(11, 16) : "09:00"} onChange={(e) => setForm({ ...form, scheduled_at: form.scheduled_at ? `${form.scheduled_at.slice(0, 10)}T${e.target.value}` : `${new Date().toISOString().slice(0, 10)}T${e.target.value}` })} data-testid="announcement-schedule" className="h-9" />
              </div>
            </div>
            <div className="flex justify-end gap-3">
              <Button variant="outline" onClick={() => setComposerOpen(false)}>Cancel</Button>
              <Button className="bg-brand hover:bg-brand-hover" onClick={openPreview} disabled={busy} data-testid="announcement-preview-button">
                {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Preview
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(preview)} onOpenChange={() => setPreview(null)}>
        <DialogContent className="max-w-md" data-testid="announcement-preview-modal">
          <DialogHeader><DialogTitle className="font-display text-lg">{preview?.title}</DialogTitle></DialogHeader>
          {preview && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><p className="text-xs text-muted-foreground">Channel</p><p className="font-semibold text-foreground">WhatsApp</p></div>
                <div><p className="text-xs text-muted-foreground">Audience</p><p className="font-semibold text-foreground">{AUDIENCES.find((a) => a.value === preview.audience)?.label}</p></div>
                <div><p className="text-xs text-muted-foreground">Eligible Recipients</p><p className="font-num text-lg font-bold text-brand" data-testid="preview-recipient-count">{preview.count}</p></div>
                <div><p className="text-xs text-muted-foreground">Delivery</p><p className="font-semibold text-foreground">{preview.scheduled_at ? "Scheduled" : "Send now"}</p></div>
              </div>
              <div>
                <p className="mb-1.5 text-xs text-muted-foreground">Message Preview</p>
                <div className="rounded-lg border border-border bg-secondary/40 p-3 text-sm text-foreground" data-testid="preview-message">{preview.message}</div>
              </div>
              <div className="flex justify-end gap-3">
                <Button variant="outline" onClick={() => setPreview(null)} data-testid="preview-cancel">Cancel</Button>
                <Button className="bg-brand hover:bg-brand-hover" onClick={send} disabled={busy} data-testid="preview-send">
                  {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}{preview.scheduled_at ? "Schedule" : "Send Now"}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <Sheet open={Boolean(detail)} onOpenChange={(o) => !o && setDetail(null)}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-md" data-testid="announcement-detail">
          {detail && (
            <div>
              <SheetHeader><SheetTitle className="font-display">{detail.title}</SheetTitle></SheetHeader>
              <div className="mt-4 space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <StatusBadge status={detail.status} />
                  <span className="text-xs text-muted-foreground">{formatDate(detail.created_at)} · by {detail.created_by_name}</span>
                </div>
                <div className="rounded-lg border border-border bg-secondary/40 p-3 text-sm text-foreground">{detail.message}</div>
                <p className="text-sm text-muted-foreground" data-testid="detail-recipient-count">
                  <span className="font-num font-bold text-foreground">{detail.recipient_count}</span> recipients · {AUDIENCES.find((a) => a.value === detail.audience)?.label}
                </p>
                {detail.status === "integration_required" && (
                  <div className="rounded-lg border border-warning/30 bg-warning/10 p-3 text-xs text-warning" data-testid="integration-required-note">
                    Official WhatsApp Business API is not connected, so bulk delivery could not start. Connect it under Settings → Integrations, or message members individually below.
                  </div>
                )}
                {["scheduled", "integration_required"].includes(detail.status) && (
                  <Button variant="outline" className="w-full text-danger hover:text-danger" onClick={() => { cancel(detail); setDetail(null); }} data-testid="announcement-cancel">
                    <Trash2 className="mr-1.5 h-4 w-4" />Cancel Announcement
                  </Button>
                )}
                <div>
                  <p className="pb-2 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Recipients</p>
                  <div className="space-y-1.5">
                    {(detail.recipients || []).slice(0, 100).map((r) => (
                      <div key={r.member_id} className="flex items-center justify-between rounded-lg border border-border px-3 py-2 text-sm" data-testid={`recipient-${r.member_id}`}>
                        <span className="font-medium text-foreground">{r.name}</span>
                        <a href={waMe(r.phone, detail.message.replace(/{member_name}/g, r.name.split(" ")[0]))} target="_blank" rel="noopener noreferrer"
                           className="inline-flex items-center gap-1 text-xs font-semibold text-[#25D366] hover:underline" data-testid={`recipient-wa-${r.member_id}`}>
                          <MessageCircle className="h-3.5 w-3.5" />WhatsApp
                        </a>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
