import { useEffect, useState } from "react";
import { Plus, UserCog, Pencil, Power, Loader2 } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { inr, formatDate, formatPhone } from "../../lib/format";
import { useAuth } from "../../contexts/AuthContext";
import { PageHeader, DataTable, StatusBadge, EmptyState, ConfirmDialog, DateField } from "../../components/app/ui";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../../components/ui/dialog";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";

const ROLES = ["Admin", "Manager", "Receptionist", "Trainer", "Sales"];

export default function Staff() {
  const { outlets } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editStaff, setEditStaff] = useState(null);
  const [toggleStaff, setToggleStaff] = useState(null);
  const [busy, setBusy] = useState(false);
  const blank = { name: "", role: "Trainer", email: "", phone: "", address: "", joining_date: new Date().toISOString().slice(0, 10), outlet_id: "", salary: "", password: "" };
  const [form, setForm] = useState(blank);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/staff");
      setItems(data);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  useEffect(() => {
    if (dialogOpen) setForm(editStaff ? { ...blank, ...editStaff, phone: (editStaff.phone || "").replace(/\D/g, "").slice(-10), password: "" } : blank);
  }, [dialogOpen, editStaff]);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const payload = { ...form, salary: form.salary ? Number(form.salary) : null, outlet_id: form.outlet_id || undefined };
      if (!payload.password) delete payload.password;
      if (editStaff) {
        delete payload.password;
        await api.put(`/staff/${editStaff.id}`, payload);
        toast.success("Staff member updated");
      } else {
        await api.post("/staff", payload);
        toast.success("Staff member created");
      }
      setDialogOpen(false); setEditStaff(null);
      load();
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setBusy(false);
    }
  };

  const doToggle = async () => {
    setBusy(true);
    try {
      await api.post(`/staff/${toggleStaff.id}/toggle`);
      toast.success(toggleStaff.status === "active" ? "Staff member disabled" : "Staff member enabled");
      setToggleStaff(null);
      load();
    } catch (e) {
      toast.error(apiError(e));
    } finally {
      setBusy(false);
    }
  };

  const columns = [
    { key: "name", label: "Staff Member", render: (s) => (
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand/12 font-display text-xs font-bold text-brand">
          {s.name.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase()}
        </div>
        <div>
          <p className="font-medium text-foreground">{s.name}</p>
          <p className="font-num text-xs text-muted-foreground">{formatPhone(s.phone)}</p>
        </div>
      </div>
    )},
    { key: "role", label: "Role", render: (s) => <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs font-semibold capitalize text-foreground">{s.role}</span> },
    { key: "email", label: "Email", render: (s) => <span className="text-muted-foreground">{s.email || "—"}</span> },
    { key: "joining_date", label: "Joined", render: (s) => formatDate(s.joining_date) },
    { key: "salary", label: "Salary", align: "right", render: (s) => <span className="font-num">{s.salary ? inr(s.salary) : "—"}</span> },
    { key: "has_login", label: "Login", render: (s) => (s.has_login ? <span className="text-xs font-semibold text-success">Enabled</span> : <span className="text-xs text-muted-foreground">No</span>) },
    { key: "status", label: "Status", render: (s) => <StatusBadge status={s.status} label={s.status === "active" ? "Active" : "Disabled"} /> },
    { key: "actions", label: "", align: "right", render: (s) => (
      <div className="flex justify-end gap-1">
        <button onClick={() => { setEditStaff(s); setDialogOpen(true); }} className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground" data-testid={`staff-edit-${s.id}`} aria-label="Edit"><Pencil className="h-4 w-4" /></button>
        <button onClick={() => setToggleStaff(s)} className={`rounded-md p-1.5 ${s.status === "active" ? "text-danger hover:bg-danger/10" : "text-success hover:bg-success/10"}`} data-testid={`staff-toggle-${s.id}`} aria-label="Toggle"><Power className="h-4 w-4" /></button>
      </div>
    )},
  ];

  return (
    <div data-testid="staff-page">
      <PageHeader title="Staff" subtitle="Your team and their access." testid="staff-header">
        <Button className="bg-brand hover:bg-brand-hover" onClick={() => { setEditStaff(null); setDialogOpen(true); }} data-testid="add-staff-button">
          <Plus className="mr-1.5 h-4 w-4" />Add Staff
        </Button>
      </PageHeader>
      <DataTable testid="staff-table" columns={columns} rows={items} loading={loading}
                 empty={<EmptyState icon={UserCog} title="No staff yet" description="Add trainers, receptionists and managers — optionally with their own login."
                                    action={<Button className="bg-brand hover:bg-brand-hover" onClick={() => setDialogOpen(true)} data-testid="empty-add-staff"><Plus className="mr-1.5 h-4 w-4" />Add Staff</Button>} testid="staff-empty" />} />

      <Dialog open={dialogOpen} onOpenChange={(o) => { if (!o) { setDialogOpen(false); setEditStaff(null); } }}>
        <DialogContent className="max-w-md" data-testid="staff-form-modal">
          <DialogHeader><DialogTitle className="font-display text-lg">{editStaff ? "Edit Staff Member" : "Add Staff Member"}</DialogTitle></DialogHeader>
          <form onSubmit={submit} className="space-y-4">
            <div className="space-y-1.5"><Label>Name</Label><Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="staff-form-name" /></div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Role</Label>
                <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
                  <SelectTrigger data-testid="staff-form-role"><SelectValue /></SelectTrigger>
                  <SelectContent>{ROLES.map((r) => <SelectItem key={r} value={r}>{r}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Phone</Label>
                <div className="flex">
                  <span className="inline-flex items-center rounded-l-lg border border-r-0 border-input bg-secondary px-3 text-sm text-muted-foreground">+91</span>
                  <Input required inputMode="numeric" className="rounded-l-none" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} data-testid="staff-form-phone" />
                </div>
              </div>
            </div>
            <div className="space-y-1.5"><Label>Email</Label><Input type="email" value={form.email || ""} onChange={(e) => setForm({ ...form, email: e.target.value })} data-testid="staff-form-email" /></div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5"><Label>Joining Date</Label><DateField value={form.joining_date || ""} onChange={(v) => setForm({ ...form, joining_date: v })} testid="staff-form-joining" /></div>
              <div className="space-y-1.5"><Label>Salary (₹) <span className="font-normal text-muted-foreground">(optional)</span></Label><Input type="number" min="0" value={form.salary || ""} onChange={(e) => setForm({ ...form, salary: e.target.value })} /></div>
            </div>
            {outlets.length > 1 && (
              <div className="space-y-1.5">
                <Label>Outlet</Label>
                <Select value={form.outlet_id || outlets[0]?.id} onValueChange={(v) => setForm({ ...form, outlet_id: v })}>
                  <SelectTrigger data-testid="staff-form-outlet"><SelectValue /></SelectTrigger>
                  <SelectContent>{outlets.map((o) => <SelectItem key={o.id} value={o.id}>{o.name}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            )}
            {!editStaff && (
              <div className="space-y-1.5">
                <Label>Login Password <span className="font-normal text-muted-foreground">(optional — creates a staff login)</span></Label>
                <Input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder="Minimum 8 characters" data-testid="staff-form-password" />
                <p className="text-xs text-muted-foreground">Requires an email. The password is never stored in plaintext and cannot be viewed later.</p>
              </div>
            )}
            <div className="flex justify-end gap-3">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
              <Button type="submit" className="bg-brand hover:bg-brand-hover" disabled={busy} data-testid="staff-form-submit">
                {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}{editStaff ? "Save" : "Create Staff"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
      <ConfirmDialog open={Boolean(toggleStaff)} onClose={() => setToggleStaff(null)} onConfirm={doToggle} busy={busy}
                     testid="staff-toggle-confirm" title={toggleStaff?.status === "active" ? `Disable ${toggleStaff?.name}?` : `Enable ${toggleStaff?.name}?`}
                     description={toggleStaff?.status === "active" ? "They will lose access to the app immediately. Their records remain intact." : "They will regain access."}
                     confirmLabel={toggleStaff?.status === "active" ? "Disable" : "Enable"} />
    </div>
  );
}
