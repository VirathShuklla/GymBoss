import { useEffect, useState } from "react";
import { Plus, Receipt, Pencil, Trash2, Loader2 } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { inr, formatDate } from "../../lib/format";
import { useAuth } from "../../contexts/AuthContext";
import { PageHeader, DataTable, EmptyState, ConfirmDialog, DateField } from "../../components/app/ui";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../../components/ui/dialog";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";

const CATEGORIES = ["Rent", "Utilities", "Salary", "Maintenance", "Housekeeping", "Marketing", "Equipment", "General"];
const METHODS = ["Cash", "UPI", "Card", "Bank Transfer", "Other"];
const MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];

export default function Expenses() {
  const { outlets } = useAuth();
  const now = new Date();
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [year, setYear] = useState(now.getFullYear());
  const [category, setCategory] = useState("all");
  const [outletId, setOutletId] = useState("all");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editExpense, setEditExpense] = useState(null);
  const [deleteExpense, setDeleteExpense] = useState(null);
  const [busy, setBusy] = useState(false);
  const blank = { name: "", category: "General", date: now.toISOString().slice(0, 10), amount: "", method: "Cash", notes: "", outlet_id: "" };
  const [form, setForm] = useState(blank);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/expenses", { params: { month, year, category, outlet_id: outletId === "all" ? undefined : outletId } });
      setItems(data.items);
      setTotal(data.total_amount);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, [month, year, category, outletId]);

  useEffect(() => {
    if (dialogOpen) setForm(editExpense ? { ...editExpense, amount: editExpense.amount } : blank);
  }, [dialogOpen, editExpense]);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const payload = { ...form, amount: Number(form.amount || 0) };
      if (editExpense) {
        await api.put(`/expenses/${editExpense.id}`, payload);
        toast.success("Expense updated");
      } else {
        await api.post("/expenses", payload);
        toast.success("Expense added");
      }
      setDialogOpen(false); setEditExpense(null);
      load();
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setBusy(false);
    }
  };

  const doDelete = async () => {
    setBusy(true);
    try {
      await api.delete(`/expenses/${deleteExpense.id}`);
      toast.success("Expense deleted");
      setDeleteExpense(null);
      load();
    } catch (e) {
      toast.error(apiError(e));
    } finally {
      setBusy(false);
    }
  };

  const columns = [
    { key: "name", label: "Expense", render: (e) => <span className="font-medium text-foreground">{e.name}</span> },
    { key: "category", label: "Category" },
    { key: "date", label: "Date", render: (e) => formatDate(e.date) },
    { key: "amount", label: "Amount", align: "right", render: (e) => <span className="font-num font-bold text-danger">{inr(e.amount)}</span> },
    { key: "method", label: "Method" },
    { key: "notes", label: "Notes", render: (e) => <span className="text-muted-foreground">{e.notes || "—"}</span> },
    { key: "actions", label: "", align: "right", render: (e) => (
      <div className="flex justify-end gap-1">
        <button onClick={() => { setEditExpense(e); setDialogOpen(true); }} className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground" data-testid={`expense-edit-${e.id}`} aria-label="Edit"><Pencil className="h-4 w-4" /></button>
        <button onClick={() => setDeleteExpense(e)} className="rounded-md p-1.5 text-danger hover:bg-danger/10" data-testid={`expense-delete-${e.id}`} aria-label="Delete"><Trash2 className="h-4 w-4" /></button>
      </div>
    )},
  ];

  return (
    <div data-testid="expenses-page">
      <PageHeader title="Expenses" subtitle="Track gym expenses and operating costs." testid="expenses-header">
        <Button className="bg-brand hover:bg-brand-hover" onClick={() => { setEditExpense(null); setDialogOpen(true); }} data-testid="add-expense-button">
          <Plus className="mr-1.5 h-4 w-4" />Add Expense
        </Button>
      </PageHeader>
      <div className="mb-4 flex flex-wrap items-center gap-2.5">
        <Select value={String(month)} onValueChange={(v) => setMonth(Number(v))}>
          <SelectTrigger className="h-9 w-36" data-testid="expenses-month"><SelectValue /></SelectTrigger>
          <SelectContent>{MONTHS.map((m, i) => <SelectItem key={m} value={String(i + 1)}>{m}</SelectItem>)}</SelectContent>
        </Select>
        <Select value={String(year)} onValueChange={(v) => setYear(Number(v))}>
          <SelectTrigger className="h-9 w-28" data-testid="expenses-year"><SelectValue /></SelectTrigger>
          <SelectContent>{[year - 1, year, year + 1].map((y) => <SelectItem key={y} value={String(y)}>{y}</SelectItem>)}</SelectContent>
        </Select>
        <Select value={category} onValueChange={setCategory}>
          <SelectTrigger className="h-9 w-40" data-testid="expenses-category"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            {CATEGORIES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
          </SelectContent>
        </Select>
        {outlets.length > 1 && (
          <Select value={outletId} onValueChange={setOutletId}>
            <SelectTrigger className="h-9 w-40" data-testid="expenses-outlet"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Outlets</SelectItem>
              {outlets.map((o) => <SelectItem key={o.id} value={o.id}>{o.name}</SelectItem>)}
            </SelectContent>
          </Select>
        )}
        <span className="ml-auto text-sm text-muted-foreground" data-testid="expenses-total">Total: <span className="font-num font-bold text-danger">{inr(total)}</span></span>
      </div>
      <DataTable testid="expenses-table" columns={columns} rows={items} loading={loading}
                 empty={<EmptyState icon={Receipt} title="No expenses recorded" description="Add rent, salaries, utilities and other costs to track your gym's profitability."
                                    action={<Button className="bg-brand hover:bg-brand-hover" onClick={() => setDialogOpen(true)} data-testid="empty-add-expense"><Plus className="mr-1.5 h-4 w-4" />Add Expense</Button>} testid="expenses-empty" />} />

      <Dialog open={dialogOpen} onOpenChange={(o) => { if (!o) { setDialogOpen(false); setEditExpense(null); } }}>
        <DialogContent className="max-w-md" data-testid="expense-form-modal">
          <DialogHeader><DialogTitle className="font-display text-lg">{editExpense ? "Edit Expense" : "Add Expense"}</DialogTitle></DialogHeader>
          <form onSubmit={submit} className="space-y-4">
            <div className="space-y-1.5"><Label>Expense Name</Label><Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g., Electricity Bill" data-testid="expense-form-name" /></div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Category</Label>
                <Select value={form.category} onValueChange={(v) => setForm({ ...form, category: v })}>
                  <SelectTrigger data-testid="expense-form-category"><SelectValue /></SelectTrigger>
                  <SelectContent>{CATEGORIES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5"><Label>Date</Label><DateField value={form.date} onChange={(v) => setForm({ ...form, date: v })} testid="expense-form-date" /></div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5"><Label>Amount (₹)</Label><Input required type="number" min="1" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} data-testid="expense-form-amount" /></div>
              <div className="space-y-1.5">
                <Label>Payment Method</Label>
                <Select value={form.method} onValueChange={(v) => setForm({ ...form, method: v })}>
                  <SelectTrigger data-testid="expense-form-method"><SelectValue /></SelectTrigger>
                  <SelectContent>{METHODS.map((m) => <SelectItem key={m} value={m}>{m}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-1.5"><Label>Notes</Label><Input value={form.notes || ""} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>
            <div className="flex justify-end gap-3">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
              <Button type="submit" className="bg-brand hover:bg-brand-hover" disabled={busy} data-testid="expense-form-submit">
                {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}{editExpense ? "Save" : "Add Expense"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
      <ConfirmDialog open={Boolean(deleteExpense)} onClose={() => setDeleteExpense(null)} onConfirm={doDelete} busy={busy}
                     testid="expense-delete-confirm" title={`Delete ${deleteExpense?.name}?`}
                     description="Are you sure you want to delete this expense? This action cannot be undone." confirmLabel="Delete" />
    </div>
  );
}
