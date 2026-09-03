import { useEffect, useState } from "react";
import { Plus, Layers, Pencil, Trash2, Loader2 } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { inr } from "../../lib/format";
import { PageHeader, DataTable, StatusBadge, EmptyState, ConfirmDialog } from "../../components/app/ui";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../../components/ui/dialog";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";

const TABS = [
  { value: "membership", label: "Membership" },
  { value: "pt", label: "PT" },
  { value: "service", label: "Service" },
  { value: "product", label: "Product" },
];

function PlanDialog({ open, onClose, type, plan, onSaved }) {
  const blank = { name: "", category: "", duration_type: "months", duration: 1, price: "", sessions: "", inventory: "", trainer: "", description: "", status: "active" };
  const [form, setForm] = useState(blank);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (open) setForm(plan ? { ...blank, ...plan } : blank);
  }, [open, plan]);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    const payload = {
      name: form.name, type, category: form.category || null,
      duration_type: form.duration_type, duration: Number(form.duration || 1),
      price: Number(form.price || 0),
      sessions: form.sessions ? Number(form.sessions) : null,
      inventory: form.inventory !== "" ? Number(form.inventory) : null,
      trainer: form.trainer || null, description: form.description || null, status: form.status,
    };
    try {
      if (plan) {
        await api.put(`/plans/${plan.id}`, payload);
        toast.success("Updated successfully");
      } else {
        await api.post("/plans", payload);
        toast.success("Created successfully");
      }
      onSaved(); onClose();
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setBusy(false);
    }
  };

  const nameLabel = { membership: "Plan Name", pt: "Plan Name", service: "Service Name", product: "Product Name" }[type];

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md" data-testid="plan-form-modal">
        <DialogHeader><DialogTitle className="font-display text-lg">{plan ? "Edit" : "Add"} {TABS.find((t) => t.value === type).label}</DialogTitle></DialogHeader>
        <form onSubmit={submit} className="space-y-4">
          <div className="space-y-1.5"><Label>{nameLabel}</Label><Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="plan-form-name" /></div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5"><Label>Category</Label><Input value={form.category || ""} onChange={(e) => setForm({ ...form, category: e.target.value })} placeholder="e.g., General" data-testid="plan-form-category" /></div>
            <div className="space-y-1.5"><Label>Price (₹)</Label><Input required type="number" min="0" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} data-testid="plan-form-price" /></div>
          </div>
          {(type === "membership" || type === "pt") && (
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Duration Type</Label>
                <Select value={form.duration_type} onValueChange={(v) => setForm({ ...form, duration_type: v })}>
                  <SelectTrigger data-testid="plan-form-duration-type"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="days">Days</SelectItem>
                    <SelectItem value="months">Months</SelectItem>
                    <SelectItem value="years">Years</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5"><Label>Duration</Label><Input type="number" min="1" value={form.duration} onChange={(e) => setForm({ ...form, duration: e.target.value })} data-testid="plan-form-duration" /></div>
            </div>
          )}
          {type === "pt" && (
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5"><Label>Sessions</Label><Input type="number" min="1" value={form.sessions} onChange={(e) => setForm({ ...form, sessions: e.target.value })} data-testid="plan-form-sessions" /></div>
              <div className="space-y-1.5"><Label>Trainer</Label><Input value={form.trainer || ""} onChange={(e) => setForm({ ...form, trainer: e.target.value })} data-testid="plan-form-trainer" /></div>
            </div>
          )}
          {type === "product" && (
            <div className="space-y-1.5"><Label>Inventory Quantity</Label><Input type="number" min="0" value={form.inventory} onChange={(e) => setForm({ ...form, inventory: e.target.value })} data-testid="plan-form-inventory" /></div>
          )}
          <div className="space-y-1.5"><Label>Description</Label><Textarea rows={2} value={form.description || ""} onChange={(e) => setForm({ ...form, description: e.target.value })} data-testid="plan-form-description" /></div>
          <div className="space-y-1.5">
            <Label>Status</Label>
            <Select value={form.status} onValueChange={(v) => setForm({ ...form, status: v })}>
              <SelectTrigger data-testid="plan-form-status"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="disabled">Disabled</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex justify-end gap-3">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" className="bg-brand hover:bg-brand-hover" disabled={busy} data-testid="plan-form-submit">
              {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}{plan ? "Save Changes" : "Create"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function PlanTable({ type }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editPlan, setEditPlan] = useState(null);
  const [deletePlan, setDeletePlan] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/plans", { params: { type } });
      setItems(data);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, [type]);

  const doDelete = async () => {
    setBusy(true);
    try {
      await api.delete(`/plans/${deletePlan.id}`);
      toast.success("Deleted successfully");
      setDeletePlan(null);
      load();
    } catch (e) {
      toast.error(apiError(e));
    } finally {
      setBusy(false);
    }
  };

  const columns = [
    { key: "name", label: "Name", render: (p) => <span className="font-medium text-foreground">{p.name}</span> },
    { key: "category", label: "Category", render: (p) => p.category || "—" },
    ...(type === "membership" || type === "pt" ? [{ key: "duration", label: "Duration", render: (p) => `${p.duration} ${p.duration_type}` }] : []),
    ...(type === "pt" ? [{ key: "sessions", label: "Sessions", render: (p) => p.sessions || "—" }] : []),
    ...(type === "product" ? [{ key: "inventory", label: "Inventory", align: "right", render: (p) => <span className="font-num">{p.inventory ?? "—"}</span> }] : []),
    { key: "price", label: "Price", align: "right", render: (p) => <span className="font-num font-semibold text-foreground">{inr(p.price)}</span> },
    { key: "status", label: "Status", render: (p) => <StatusBadge status={p.status} label={p.status === "active" ? "Active" : "Disabled"} /> },
    { key: "actions", label: "", render: (p) => (
      <div className="flex justify-end gap-1">
        <button onClick={(e) => { e.stopPropagation(); setEditPlan(p); setDialogOpen(true); }} className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground" data-testid={`plan-edit-${p.id}`} aria-label="Edit">
          <Pencil className="h-4 w-4" />
        </button>
        <button onClick={(e) => { e.stopPropagation(); setDeletePlan(p); }} className="rounded-md p-1.5 text-danger hover:bg-danger/10" data-testid={`plan-delete-${p.id}`} aria-label="Delete">
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    )},
  ];

  return (
    <div>
      <div className="mb-4 flex justify-end">
        <Button className="bg-brand hover:bg-brand-hover" onClick={() => { setEditPlan(null); setDialogOpen(true); }} data-testid={`add-${type}-button`}>
          <Plus className="mr-1.5 h-4 w-4" />Add {TABS.find((t) => t.value === type).label}
        </Button>
      </div>
      <DataTable testid={`${type}-table`} columns={columns} rows={items} loading={loading}
                 empty={<EmptyState icon={Layers} title={`No ${TABS.find((t) => t.value === type).label.toLowerCase()} items yet`} description="Create one to get started." testid={`${type}-empty`} />} />
      <PlanDialog open={dialogOpen} onClose={() => setDialogOpen(false)} type={type} plan={editPlan} onSaved={load} />
      <ConfirmDialog open={Boolean(deletePlan)} onClose={() => setDeletePlan(null)} onConfirm={doDelete} busy={busy}
                     testid="plan-delete-confirm" title={`Delete ${deletePlan?.name}?`}
                     description="This item will be removed from your catalogue. Existing member records are not affected." confirmLabel="Delete" />
    </div>
  );
}

export default function Plans() {
  return (
    <div data-testid="plans-page">
      <PageHeader title="Plans & Catalogue" subtitle="Membership plans, personal training, services and products." testid="plans-header" />
      <Tabs defaultValue="membership">
        <TabsList className="mb-5" data-testid="plans-tabs">
          {TABS.map((t) => <TabsTrigger key={t.value} value={t.value} data-testid={`tab-${t.value}`}>{t.label}</TabsTrigger>)}
        </TabsList>
        {TABS.map((t) => (
          <TabsContent key={t.value} value={t.value}><PlanTable type={t.value} /></TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
