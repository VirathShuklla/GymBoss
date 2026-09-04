import { useEffect, useState } from "react";
import { Users } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { inr } from "../../lib/format";
import { MButton, Field, TextInput, PhoneInput, Pills, BottomSheet, ListSkeleton, EmptyRow, StatusChip } from "../ui";
import { ModuleHeader } from "./ModuleHeader";

const EMPTY = { full_name: "", phone: "", gender: "Male", plan_id: "", batch: "", admission_amount: "", amount_paid: "", discount: "", payment_method: "Cash" };

export default function Members({ autoAdd }) {
  const [items, setItems] = useState(null);
  const [plans, setPlans] = useState([]);
  const [open, setOpen] = useState(autoAdd === "member");
  const [f, setF] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const load = () => api.get("/members?limit=100").then(({ data }) => setItems(data.items)).catch(() => setItems([]));
  useEffect(() => {
    load();
    api.get("/plans?type=membership").then(({ data }) => setPlans(data)).catch(() => {});
  }, []);

  const submit = async () => {
    if (!f.plan_id) return toast.error("Please select a membership plan");
    setBusy(true);
    try {
      await api.post("/members", {
        full_name: f.full_name.trim(),
        phone: f.phone.replace(/\D/g, ""),
        gender: f.gender,
        plan_id: f.plan_id,
        batch: f.batch || undefined,
        admission_amount: Number(f.admission_amount) || 0,
        amount_paid: Number(f.amount_paid) || 0,
        discount: Number(f.discount) || 0,
        payment_method: f.payment_method,
      });
      toast.success("Member added");
      setOpen(false);
      setF(EMPTY);
      load();
    } catch (e) {
      toast.error(apiError(e, "Could not add member"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid="m-members">
      <ModuleHeader title={items ? `${items.length} members` : "Members"} onAdd={() => setOpen(true)} addLabel="Add Member" testid="m-members-add" />
      {!items ? (
        <ListSkeleton />
      ) : items.length === 0 ? (
        <EmptyRow icon={Users} title="No members yet" subtitle="Add your first member to get started." testid="m-members-empty" />
      ) : (
        <div className="space-y-2.5">
          {items.map((m) => (
            <div key={m.id} className="flex items-center gap-3 rounded-2xl border border-border bg-card px-4 py-3" data-testid={`m-member-${m.id}`}>
              <div className="flex h-11 w-11 items-center justify-center rounded-full bg-brand/12 font-display text-sm font-bold text-brand">
                {m.full_name?.slice(0, 2).toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-foreground">{m.full_name}</p>
                <p className="truncate text-xs text-muted-foreground">{m.member_code} · {m.plan_name}</p>
              </div>
              <div className="flex flex-col items-end gap-1">
                <StatusChip status={m.status} />
                {m.due_amount > 0 && <span className="font-num text-[11px] font-bold text-danger">Due {inr(m.due_amount)}</span>}
              </div>
            </div>
          ))}
        </div>
      )}

      <BottomSheet open={open} onOpenChange={setOpen} title="Add New Member" subtitle="Add member profile." testid="m-member-sheet">
        <Field label="Full name"><TextInput data-testid="m-member-name" value={f.full_name} onChange={set("full_name")} placeholder="Member name" /></Field>
        <Field label="Mobile number"><PhoneInput data-testid="m-member-phone" value={f.phone} onChange={set("phone")} /></Field>
        <Field label="Gender"><Pills options={["Male", "Female"]} value={f.gender} onChange={(v) => setF({ ...f, gender: v })} /></Field>
        <Field label="Membership plan">
          {plans.length === 0 ? (
            <p className="text-xs text-muted-foreground">No membership plans yet. Add one in the Plan / Catalogue tab.</p>
          ) : (
            <Pills options={plans.map((p) => ({ value: p.id, label: `${p.name} · ${inr(p.price)}` }))} value={f.plan_id} onChange={(v) => setF({ ...f, plan_id: v })} />
          )}
        </Field>
        <Field label="Batch (optional)"><TextInput value={f.batch} onChange={set("batch")} placeholder="Morning / Evening" /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Admission fee"><TextInput inputMode="numeric" value={f.admission_amount} onChange={set("admission_amount")} placeholder="0" /></Field>
          <Field label="Discount"><TextInput inputMode="numeric" value={f.discount} onChange={set("discount")} placeholder="0" /></Field>
        </div>
        <Field label="Amount collected"><TextInput inputMode="numeric" data-testid="m-member-paid" value={f.amount_paid} onChange={set("amount_paid")} placeholder="0" /></Field>
        <Field label="Payment method"><Pills options={["Cash", "UPI", "Card"]} value={f.payment_method} onChange={(v) => setF({ ...f, payment_method: v })} /></Field>
        <MButton onClick={submit} loading={busy} disabled={f.full_name.trim().length < 2 || f.phone.replace(/\D/g, "").length !== 10} data-testid="m-member-save">Add Member</MButton>
      </BottomSheet>
    </div>
  );
}
