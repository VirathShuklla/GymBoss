import { useEffect, useState } from "react";
import { Plus, Building2, Pencil, Power, Loader2 } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { useAuth } from "../../contexts/AuthContext";
import { PageHeader, DataTable, StatusBadge, EmptyState, ConfirmDialog } from "../../components/app/ui";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../../components/ui/dialog";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";

export default function Outlets() {
  const { reload } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editOutlet, setEditOutlet] = useState(null);
  const [toggleOutlet, setToggleOutlet] = useState(null);
  const [busy, setBusy] = useState(false);
  const blank = { name: "", address: "", phone: "", email: "", city: "", state: "", pin_code: "", manager: "" };
  const [form, setForm] = useState(blank);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/outlets");
      setItems(data);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  useEffect(() => {
    if (dialogOpen) setForm(editOutlet ? { ...blank, ...editOutlet } : blank);
  }, [dialogOpen, editOutlet]);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (editOutlet) {
        await api.put(`/outlets/${editOutlet.id}`, form);
        toast.success("Outlet updated");
      } else {
        await api.post("/outlets", form);
        toast.success("Outlet created");
      }
      setDialogOpen(false); setEditOutlet(null);
      load(); reload();
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setBusy(false);
    }
  };

  const doToggle = async () => {
    setBusy(true);
    try {
      await api.post(`/outlets/${toggleOutlet.id}/toggle`);
      toast.success(toggleOutlet.status === "active" ? "Outlet disabled" : "Outlet enabled");
      setToggleOutlet(null);
      load(); reload();
    } catch (e) {
      toast.error(apiError(e));
    } finally {
      setBusy(false);
    }
  };

  const columns = [
    { key: "name", label: "Outlet", render: (o) => (
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand/12 font-display text-xs font-bold text-brand">
          {o.name.slice(0, 2).toUpperCase()}
        </div>
        <div>
          <p className="font-medium text-foreground">{o.name} {o.is_primary && <span className="ml-1 rounded-full bg-secondary px-2 py-0.5 text-[10px] font-bold text-muted-foreground">PRIMARY</span>}</p>
          <p className="text-xs text-muted-foreground">{o.address || o.city || ""}</p>
        </div>
      </div>
    )},
    { key: "city", label: "Location", render: (o) => [o.city, o.state].filter(Boolean).join(", ") || "—" },
    { key: "manager", label: "Manager", render: (o) => o.manager || "—" },
    { key: "status", label: "Status", render: (o) => <StatusBadge status={o.status} label={o.status === "active" ? "Active" : "Disabled"} /> },
    { key: "actions", label: "", align: "right", render: (o) => (
      <div className="flex justify-end gap-1">
        <button onClick={() => { setEditOutlet(o); setDialogOpen(true); }} className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground" data-testid={`outlet-edit-${o.id}`} aria-label="Edit"><Pencil className="h-4 w-4" /></button>
        <button onClick={() => setToggleOutlet(o)} className={`rounded-md p-1.5 ${o.status === "active" ? "text-danger hover:bg-danger/10" : "text-success hover:bg-success/10"}`} data-testid={`outlet-toggle-${o.id}`} aria-label="Toggle"><Power className="h-4 w-4" /></button>
      </div>
    )},
  ];

  return (
    <div data-testid="outlets-page">
      <PageHeader title="Outlets" subtitle="Manage your gym branches and locations." testid="outlets-header">
        <Button className="bg-brand hover:bg-brand-hover" onClick={() => { setEditOutlet(null); setDialogOpen(true); }} data-testid="add-outlet-button">
          <Plus className="mr-1.5 h-4 w-4" />Add Outlet
        </Button>
      </PageHeader>
      <DataTable testid="outlets-table" columns={columns} rows={items} loading={loading}
                 empty={<EmptyState icon={Building2} title="No outlets yet" testid="outlets-empty" />} />

      <Dialog open={dialogOpen} onOpenChange={(o) => { if (!o) { setDialogOpen(false); setEditOutlet(null); } }}>
        <DialogContent className="max-w-md" data-testid="outlet-form-modal">
          <DialogHeader><DialogTitle className="font-display text-lg">{editOutlet ? "Edit Outlet" : "Add Outlet"}</DialogTitle></DialogHeader>
          <form onSubmit={submit} className="space-y-4">
            <div className="space-y-1.5"><Label>Outlet Name</Label><Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g., HSR Layout" data-testid="outlet-form-name" /></div>
            <div className="space-y-1.5"><Label>Address</Label><Input value={form.address || ""} onChange={(e) => setForm({ ...form, address: e.target.value })} placeholder="Full address" data-testid="outlet-form-address" /></div>
            <div className="flex justify-end gap-3">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
              <Button type="submit" className="bg-brand hover:bg-brand-hover" disabled={busy} data-testid="outlet-form-submit">
                {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}{editOutlet ? "Save" : "Create Outlet"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
      <ConfirmDialog open={Boolean(toggleOutlet)} onClose={() => setToggleOutlet(null)} onConfirm={doToggle} busy={busy}
                     testid="outlet-toggle-confirm" title={toggleOutlet?.status === "active" ? `Disable ${toggleOutlet?.name}?` : `Enable ${toggleOutlet?.name}?`}
                     description={toggleOutlet?.status === "active" ? "Members and data remain safe. The outlet will stop appearing in filters and switchers." : "The outlet will become active again."}
                     confirmLabel={toggleOutlet?.status === "active" ? "Disable Outlet" : "Enable Outlet"} />
    </div>
  );
}
