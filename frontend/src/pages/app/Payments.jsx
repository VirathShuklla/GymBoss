import { useEffect, useState } from "react";
import { Plus, IndianRupee, Loader2, Receipt, Pencil, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { inr, formatDate } from "../../lib/format";
import { useAuth } from "../../contexts/AuthContext";
import { PageHeader, DataTable, StatusBadge, EmptyState, SearchInput, Pagination, MemberPicker } from "../../components/app/ui";
import { ReceiptModal } from "../../components/app/ReceiptModal";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../../components/ui/dialog";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";

const METHODS = ["Cash", "UPI", "Card", "Bank Transfer", "Other"];

export default function Payments() {
  const { user } = useAuth();
  const readOnly = user?.permission === "view" && user?.role !== "owner";
  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [method, setMethod] = useState("all");
  const [type, setType] = useState("all");
  const [page, setPage] = useState(1);
  const [payOpen, setPayOpen] = useState(false);
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState({ amount: "", method: "Cash", notes: "" });
  const [busy, setBusy] = useState(false);
  const [receipt, setReceipt] = useState(null);
  const [editOpen, setEditOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [editForm, setEditForm] = useState({ amount: "", method: "Cash", notes: "" });
  const [reverseTarget, setReverseTarget] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/payments", {
        params: { search: search || undefined, method: method === "all" ? undefined : method, type: type === "all" ? undefined : type, page, limit: 20 },
      });
      setData(data);
    } catch {
      toast.error("We couldn't load payments.");
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, [method, type, page]);
  useEffect(() => {
    const t = setTimeout(() => { setPage(1); load(); }, 350);
    return () => clearTimeout(t);
  }, [search]);

  const record = async () => {
    if (!selected) return toast.error("Select a member");
    if (!Number(form.amount)) return toast.error("Enter an amount");
    setBusy(true);
    try {
      const { data: payment } = await api.post("/payments", { member_id: selected.id, amount: Number(form.amount), method: form.method, notes: form.notes || null });
      toast.success("Payment recorded");
      setPayOpen(false); setSelected(null); setForm({ amount: "", method: "Cash", notes: "" });
      load();
      const { data: rc } = await api.get(`/payments/${payment.id}/receipt`);
      setReceipt(rc);
    } catch (e) {
      toast.error(apiError(e));
    } finally {
      setBusy(false);
    }
  };

  const viewReceipt = async (id) => {
    const { data } = await api.get(`/payments/${id}/receipt`);
    setReceipt(data);
  };

  const openEdit = (p) => {
    setEditing(p);
    setEditForm({ amount: String(p.amount), method: p.method || "Cash", notes: p.notes || "" });
    setEditOpen(true);
  };
  const saveEdit = async () => {
    if (!Number(editForm.amount)) return toast.error("Enter an amount");
    setBusy(true);
    try {
      await api.put(`/payments/${editing.id}`, { amount: Number(editForm.amount), method: editForm.method, notes: editForm.notes || null });
      toast.success("Payment updated — member due recalculated");
      setEditOpen(false); setEditing(null); load();
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };
  const doReverse = async () => {
    setBusy(true);
    try {
      await api.delete(`/payments/${reverseTarget.id}`);
      toast.success("Payment reversed — member due updated");
      setReverseTarget(null); load();
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };

  const columns = [
    { key: "created_at", label: "Date", render: (p) => formatDate(p.created_at) },
    { key: "member_name", label: "Member", render: (p) => <span className="font-medium text-foreground">{p.member_name}</span> },
    { key: "receipt_no", label: "Receipt", render: (p) => <span className="font-num text-xs text-muted-foreground">{p.receipt_no}</span> },
    { key: "type", label: "Type", render: (p) => <StatusBadge status={p.type} /> },
    { key: "plan_name", label: "Plan", render: (p) => p.plan_name || "—" },
    { key: "amount", label: "Amount", align: "right", render: (p) => <span className="font-num font-bold text-success">{inr(p.amount)}</span> },
    { key: "method", label: "Method" },
    { key: "actions", label: "", align: "right", render: (p) => (
      <div className="flex items-center justify-end gap-3">
        <button onClick={() => viewReceipt(p.id)} className="inline-flex items-center gap-1 text-xs font-medium text-brand hover:underline" data-testid={`payment-receipt-${p.id}`}>
          <Receipt className="h-3.5 w-3.5" />Receipt
        </button>
        {!readOnly && (
          <button onClick={() => openEdit(p)} className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground" data-testid={`payment-edit-${p.id}`}>
            <Pencil className="h-3.5 w-3.5" />Edit
          </button>
        )}
        {!readOnly && (
          <button onClick={() => setReverseTarget(p)} className="inline-flex items-center gap-1 text-xs font-medium text-danger hover:underline" data-testid={`payment-reverse-${p.id}`}>
            <RotateCcw className="h-3.5 w-3.5" />Reverse
          </button>
        )}
      </div>
    )},
  ];

  const hasFilters = search || method !== "all" || type !== "all";
  return (
    <div data-testid="payments-page">
      <PageHeader title="Payments" subtitle="Member payments and receipts." testid="payments-header">
        {!readOnly && (
          <Button className="bg-brand hover:bg-brand-hover" onClick={() => setPayOpen(true)} data-testid="record-payment-button">
            <Plus className="mr-1.5 h-4 w-4" />Record Payment
          </Button>
        )}
      </PageHeader>

      <div className="mb-4 flex flex-wrap gap-2.5">
        <div className="w-full sm:w-64"><SearchInput value={search} onChange={setSearch} placeholder="Member or receipt no." testid="payments-search" /></div>
        <Select value={method} onValueChange={setMethod}>
          <SelectTrigger className="h-9 w-36" data-testid="payments-method-filter"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Methods</SelectItem>
            {METHODS.map((m) => <SelectItem key={m} value={m}>{m}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={type} onValueChange={setType}>
          <SelectTrigger className="h-9 w-36" data-testid="payments-type-filter"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="admission">Admission</SelectItem>
            <SelectItem value="renewal">Renewal</SelectItem>
            <SelectItem value="due">Due Payment</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <DataTable testid="payments-table" columns={columns} rows={data.items} loading={loading}
                 empty={hasFilters
                   ? <EmptyState icon={IndianRupee} title="No payments match your filters" description="Try a different search or clear the filters."
                                 action={<Button variant="outline" onClick={() => { setSearch(""); setMethod("all"); setType("all"); }} data-testid="payments-clear-filters">Clear Filters</Button>} testid="payments-filtered-empty" />
                   : <EmptyState icon={IndianRupee} title="No payments yet" description="Payments you record will appear here."
                                 action={<Button className="bg-brand hover:bg-brand-hover" onClick={() => setPayOpen(true)} data-testid="empty-record-payment"><Plus className="mr-1.5 h-4 w-4" />Record Payment</Button>} testid="payments-empty" />} />
      <Pagination page={page} total={data.total} limit={20} onPage={setPage} testid="payments-pagination" />

      <Dialog open={payOpen} onOpenChange={setPayOpen}>
        <DialogContent className="max-w-md" data-testid="record-payment-modal">
          <DialogHeader><DialogTitle className="font-display text-lg">Record Payment</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5"><Label>Member</Label><MemberPicker selected={selected} onSelect={setSelected} testid="payment-member-search" /></div>
            {selected?.due_amount > 0 && (
              <p className="rounded-lg bg-danger/10 px-3 py-2 text-xs font-medium text-danger" data-testid="payment-member-due">Outstanding due: {inr(selected.due_amount)}</p>
            )}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5"><Label>Amount (₹)</Label><Input type="number" min="1" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} data-testid="payment-amount-input" /></div>
              <div className="space-y-1.5">
                <Label>Method</Label>
                <Select value={form.method} onValueChange={(v) => setForm({ ...form, method: v })}>
                  <SelectTrigger data-testid="payment-method-select"><SelectValue /></SelectTrigger>
                  <SelectContent>{METHODS.map((m) => <SelectItem key={m} value={m}>{m}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-1.5"><Label>Notes <span className="font-normal text-muted-foreground">(optional)</span></Label><Input value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>
            <Button className="w-full bg-brand hover:bg-brand-hover" onClick={record} disabled={busy} data-testid="payment-submit-button">
              {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Record Payment
            </Button>
          </div>
        </DialogContent>
      </Dialog>
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="max-w-md" data-testid="edit-payment-modal">
          <DialogHeader><DialogTitle className="font-display text-lg">Edit Payment</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <p className="text-xs text-muted-foreground">Editing {editing?.receipt_no} for {editing?.member_name}. Changing the amount recalculates the member's outstanding due.</p>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5"><Label>Amount (₹)</Label><Input type="number" min="1" value={editForm.amount} onChange={(e) => setEditForm({ ...editForm, amount: e.target.value })} data-testid="edit-payment-amount" /></div>
              <div className="space-y-1.5">
                <Label>Method</Label>
                <Select value={editForm.method} onValueChange={(v) => setEditForm({ ...editForm, method: v })}>
                  <SelectTrigger data-testid="edit-payment-method"><SelectValue /></SelectTrigger>
                  <SelectContent>{METHODS.map((m) => <SelectItem key={m} value={m}>{m}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-1.5"><Label>Notes <span className="font-normal text-muted-foreground">(optional)</span></Label><Input value={editForm.notes} onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })} data-testid="edit-payment-notes" /></div>
            <Button className="w-full bg-brand hover:bg-brand-hover" onClick={saveEdit} disabled={busy} data-testid="edit-payment-save">
              {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Save Changes
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={!!reverseTarget} onOpenChange={(o) => !o && setReverseTarget(null)}>
        <DialogContent className="max-w-sm" data-testid="reverse-payment-modal">
          <DialogHeader><DialogTitle className="font-display text-lg">Reverse Payment?</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              This permanently removes the {reverseTarget ? inr(reverseTarget.amount) : ""} payment ({reverseTarget?.receipt_no}) for {reverseTarget?.member_name} and adds the amount back to their outstanding due.
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setReverseTarget(null)} data-testid="reverse-cancel">Cancel</Button>
              <Button className="bg-danger text-white hover:bg-danger/90" onClick={doReverse} disabled={busy} data-testid="reverse-confirm">
                {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Reverse Payment
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <ReceiptModal receipt={receipt} onClose={() => setReceipt(null)} />
    </div>
  );
}
