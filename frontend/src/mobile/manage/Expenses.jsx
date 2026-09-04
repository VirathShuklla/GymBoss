import { useEffect, useState } from "react";
import { Receipt } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { inr, formatDate } from "../../lib/format";
import { MButton, Field, TextInput, Pills, BottomSheet, ListSkeleton, EmptyRow } from "../ui";
import { ModuleHeader } from "./ModuleHeader";

const today = () => new Date().toISOString().slice(0, 10);
const EMPTY = () => ({ name: "", category: "General", date: today(), amount: "", method: "Cash" });
const CATS = ["Rent", "Salary", "Utilities", "Equipment", "Marketing", "General"];

export default function Expenses() {
  const [items, setItems] = useState(null);
  const [total, setTotal] = useState(0);
  const [open, setOpen] = useState(false);
  const [f, setF] = useState(EMPTY());
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const load = () => api.get("/expenses").then(({ data }) => { setItems(data.items); setTotal(data.total_amount); }).catch(() => setItems([]));
  useEffect(() => { load(); }, []);

  const submit = async () => {
    setBusy(true);
    try {
      await api.post("/expenses", {
        name: f.name.trim(),
        category: f.category,
        date: f.date,
        amount: Number(f.amount) || 0,
        method: f.method,
      });
      toast.success("Expense added");
      setOpen(false);
      setF(EMPTY());
      load();
    } catch (e) {
      toast.error(apiError(e, "Could not add expense"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid="m-expenses">
      <ModuleHeader title={items ? `Total ${inr(total)}` : "Expenses"} onAdd={() => setOpen(true)} addLabel="Add Expense" testid="m-expenses-add" />
      {!items ? (
        <ListSkeleton />
      ) : items.length === 0 ? (
        <EmptyRow icon={Receipt} title="No expenses yet" subtitle="Record rent, salaries and more." testid="m-expenses-empty" />
      ) : (
        <div className="space-y-2.5">
          {items.map((e) => (
            <div key={e.id} className="flex items-center justify-between rounded-2xl border border-border bg-card px-4 py-3.5" data-testid={`m-expense-${e.id}`}>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-foreground">{e.name}</p>
                <p className="text-xs text-muted-foreground">{e.category} · {formatDate(e.date)}</p>
              </div>
              <p className="font-num text-sm font-bold text-danger">−{inr(e.amount)}</p>
            </div>
          ))}
        </div>
      )}

      <BottomSheet open={open} onOpenChange={setOpen} title="Add Expense" subtitle="Add an expense for the outlet." testid="m-expense-sheet">
        <Field label="Expense name"><TextInput data-testid="m-expense-name" value={f.name} onChange={set("name")} placeholder="Eg. Rent" /></Field>
        <Field label="Category"><Pills options={CATS} value={f.category} onChange={(v) => setF({ ...f, category: v })} /></Field>
        <Field label="Date"><TextInput type="date" value={f.date} onChange={set("date")} /></Field>
        <Field label="Amount"><TextInput inputMode="numeric" data-testid="m-expense-amount" value={f.amount} onChange={set("amount")} placeholder="0" /></Field>
        <Field label="Method"><Pills options={["Cash", "UPI", "Card", "Bank Transfer"]} value={f.method} onChange={(v) => setF({ ...f, method: v })} /></Field>
        <MButton onClick={submit} loading={busy} disabled={f.name.trim().length < 2 || !(Number(f.amount) > 0)} data-testid="m-expense-save">Add Expense</MButton>
      </BottomSheet>
    </div>
  );
}
