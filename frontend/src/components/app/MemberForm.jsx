import { useEffect, useMemo, useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { inr } from "../../lib/format";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/dialog";
import { DateField } from "./ui";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Textarea } from "../ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";

const METHODS = ["Cash", "UPI", "Card", "Bank Transfer", "Other"];

function Field({ label, children, optional }) {
  return (
    <div className="space-y-1.5">
      <Label>{label} {optional && <span className="font-normal text-muted-foreground">(optional)</span>}</Label>
      {children}
    </div>
  );
}

export function MemberForm({ open, onClose, member, prefill, plans, outlets, onSaved }) {
  const editing = Boolean(member);
  const blank = {
    full_name: "", phone: "", email: "", gender: "", dob: "", address: "",
    joining_date: new Date().toISOString().slice(0, 10), plan_id: "",
    membership_start: new Date().toISOString().slice(0, 10), batch: "", trainer: "",
    discount: 0, amount_paid: 0, payment_method: "Cash", notes: "", outlet_id: "",
  };
  const [form, setForm] = useState(blank);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    if (member) {
      setForm({
        ...blank, ...member,
        phone: (member.phone || "").replace(/\D/g, "").slice(-10),
        dob: member.dob || "", address: member.address || "", notes: member.notes || "",
        batch: member.batch || "", trainer: member.trainer || "", gender: member.gender || "",
      });
    } else if (prefill) {
      setForm({ ...blank, ...prefill, phone: (prefill.phone || "").replace(/\D/g, "").slice(-10) });
    } else {
      setForm(blank);
    }
  }, [open, member, prefill]);

  const set = (k) => (e) => setForm({ ...form, [k]: e?.target ? e.target.value : e });
  const plan = useMemo(() => plans.find((p) => p.id === form.plan_id), [plans, form.plan_id]);
  const duePreview = plan ? Math.max(0, plan.price - Number(form.discount || 0) - Number(form.amount_paid || 0)) : 0;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (editing) {
        await api.put(`/members/${member.id}`, {
          full_name: form.full_name, phone: form.phone, email: form.email || null,
          gender: form.gender || null, dob: form.dob || null, address: form.address || null,
          batch: form.batch || null, trainer: form.trainer || null, notes: form.notes || null,
          outlet_id: form.outlet_id || null,
        });
        toast.success("Member updated successfully");
      } else {
        if (!form.plan_id) { toast.error("Select a membership plan"); setBusy(false); return; }
        await api.post("/members", {
          ...form,
          discount: Number(form.discount || 0),
          amount_paid: Number(form.amount_paid || 0),
          enquiry_id: undefined,
        }, prefill?.enquiry_id ? { params: { enquiry_id: prefill.enquiry_id } } : undefined);
        toast.success("Member added successfully");
      }
      onSaved();
      onClose();
    } catch (err) {
      toast.error(apiError(err, "Could not save member"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto" data-testid="member-form-modal">
        <DialogHeader>
          <DialogTitle className="font-display text-lg">{editing ? "Edit Member" : "Add Member"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={submit} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="Full Name"><Input required value={form.full_name} onChange={set("full_name")} data-testid="member-form-name" /></Field>
          <Field label="Mobile Number">
            <div className="flex">
              <span className="inline-flex items-center rounded-l-lg border border-r-0 border-input bg-secondary px-3 text-sm text-muted-foreground">+91</span>
              <Input required inputMode="numeric" className="rounded-l-none" value={form.phone} onChange={set("phone")} data-testid="member-form-phone" />
            </div>
          </Field>
          <Field label="Email" optional><Input type="email" value={form.email || ""} onChange={set("email")} data-testid="member-form-email" /></Field>
          <Field label="Gender" optional>
            <Select value={form.gender || ""} onValueChange={set("gender")}>
              <SelectTrigger data-testid="member-form-gender"><SelectValue placeholder="Select" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="Male">Male</SelectItem>
                <SelectItem value="Female">Female</SelectItem>
                <SelectItem value="Other">Other</SelectItem>
              </SelectContent>
            </Select>
          </Field>
          <Field label="Date of Birth" optional><DateField value={form.dob || ""} onChange={(v) => setForm({ ...form, dob: v })} testid="member-form-dob" /></Field>
          <Field label="Joining Date"><DateField value={form.joining_date || ""} onChange={(v) => setForm({ ...form, joining_date: v })} testid="member-form-joining" /></Field>
          {!editing && (
            <>
              <Field label="Membership Plan">
                <Select value={form.plan_id} onValueChange={set("plan_id")}>
                  <SelectTrigger data-testid="member-form-plan"><SelectValue placeholder="Select plan" /></SelectTrigger>
                  <SelectContent>
                    {plans.length === 0 && (
                      <SelectItem value="__none" disabled>No plans yet — create one in Plans & Catalogue</SelectItem>
                    )}
                    {plans.map((p) => (
                      <SelectItem key={p.id} value={p.id} data-testid={`plan-option-${p.id}`}>
                        {p.name} — {inr(p.price)} / {p.duration} {p.duration_type}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
              <Field label="Membership Start Date"><DateField value={form.membership_start} onChange={(v) => setForm({ ...form, membership_start: v })} testid="member-form-start" /></Field>
              <Field label="Discount (₹)" optional><Input type="number" min="0" value={form.discount} onChange={set("discount")} data-testid="member-form-discount" /></Field>
              <Field label="Amount Paid (₹)"><Input type="number" min="0" value={form.amount_paid} onChange={set("amount_paid")} data-testid="member-form-amount-paid" /></Field>
              <Field label="Payment Method">
                <Select value={form.payment_method} onValueChange={set("payment_method")}>
                  <SelectTrigger data-testid="member-form-method"><SelectValue /></SelectTrigger>
                  <SelectContent>{METHODS.map((m) => <SelectItem key={m} value={m}>{m}</SelectItem>)}</SelectContent>
                </Select>
              </Field>
              {plan && (
                <div className="flex items-end rounded-lg bg-secondary/60 px-3 py-2 text-sm" data-testid="member-form-due-preview">
                  <span className="text-muted-foreground">Due after this payment:&nbsp;</span>
                  <span className={`font-num font-bold ${duePreview > 0 ? "text-danger" : "text-success"}`}>{inr(duePreview)}</span>
                </div>
              )}
            </>
          )}
          {outlets.length > 1 && (
            <Field label="Outlet">
              <Select value={form.outlet_id || outlets[0]?.id} onValueChange={set("outlet_id")}>
                <SelectTrigger data-testid="member-form-outlet"><SelectValue /></SelectTrigger>
                <SelectContent>{outlets.map((o) => <SelectItem key={o.id} value={o.id}>{o.name}</SelectItem>)}</SelectContent>
              </Select>
            </Field>
          )}
          <Field label="Batch" optional><Input value={form.batch || ""} onChange={set("batch")} placeholder="e.g., Morning 6–8 AM" data-testid="member-form-batch" /></Field>
          <Field label="Trainer" optional><Input value={form.trainer || ""} onChange={set("trainer")} data-testid="member-form-trainer" /></Field>
          <div className="sm:col-span-2">
            <Field label="Address" optional><Input value={form.address || ""} onChange={set("address")} data-testid="member-form-address" /></Field>
          </div>
          <div className="sm:col-span-2">
            <Field label="Notes" optional><Textarea rows={2} value={form.notes || ""} onChange={set("notes")} data-testid="member-form-notes" /></Field>
          </div>
          <div className="flex justify-end gap-3 sm:col-span-2">
            <Button type="button" variant="outline" onClick={onClose} data-testid="member-form-cancel">Cancel</Button>
            <Button type="submit" className="bg-brand hover:bg-brand-hover" disabled={busy} data-testid="member-form-submit">
              {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}{editing ? "Save Changes" : "Add Member"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
