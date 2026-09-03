import { useEffect, useMemo, useRef, useState } from "react";
import { Loader2, Check, Camera, Paperclip, X } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { uploadFile, fileUrl } from "../../lib/upload";
import { inr, formatDate } from "../../lib/format";
import { DateField } from "./ui";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/dialog";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Textarea } from "../ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";

const METHODS = ["Cash", "UPI", "Card", "Bank Transfer", "Other"];
const GENDERS = ["Male", "Female", "Other"];
const STEP_LABELS = ["Basic Details", "Optional Fields", "Membership"];

const today = () => new Date().toISOString().slice(0, 10);

function Stepper({ step, total }) {
  return (
    <div className="mb-6 flex items-start justify-center" data-testid="member-stepper">
      {Array.from({ length: total }).map((_, i) => {
        const n = i + 1;
        const done = n < step;
        const active = n === step;
        return (
          <div key={n} className="flex items-start">
            <div className="flex flex-col items-center">
              <div data-testid={`member-stepper-step-${n}`}
                   className={`flex h-9 w-9 items-center justify-center rounded-full font-num text-sm font-bold transition-colors ${
                     done ? "bg-success text-white" : active ? "bg-brand text-white" : "bg-slate-200 text-slate-500 dark:bg-secondary dark:text-muted-foreground"
                   }`}>
                {done ? <Check className="h-4 w-4" strokeWidth={3} /> : n}
              </div>
              <span className={`mt-1.5 hidden text-[11px] font-semibold sm:block ${active ? "text-brand" : done ? "text-success" : "text-muted-foreground"}`}>
                {STEP_LABELS[i]}
              </span>
            </div>
            {i < total - 1 && <div className={`mx-2 mt-4 h-0.5 w-10 sm:w-16 ${n < step ? "bg-success" : "bg-slate-200 dark:bg-secondary"}`} />}
          </div>
        );
      })}
    </div>
  );
}

function Field({ label, required, children }) {
  return (
    <div className="space-y-1.5">
      <Label>{label} {required && <span className="text-danger">*</span>}</Label>
      {children}
    </div>
  );
}

function addDuration(start, dtype, d) {
  const dt = new Date(`${start}T00:00:00`);
  if (Number.isNaN(dt.getTime())) return null;
  if (dtype === "days") dt.setDate(dt.getDate() + d);
  else if (dtype === "years") dt.setFullYear(dt.getFullYear() + d);
  else dt.setMonth(dt.getMonth() + d);
  return dt.toISOString().slice(0, 10);
}

export function MemberForm({ open, onClose, member, prefill, plans, outlets, onSaved }) {
  const editing = Boolean(member);
  const totalSteps = editing ? 2 : 3;
  const blank = {
    full_name: "", phone: "", gender: "", batch: "", new_batch: "",
    email: "", height: "", weight: "", address: "", notes: "", dob: "",
    joining_date: today(), payment_date: today(), plan_id: "",
    admission_amount: "", discount: "", payment_method: "Cash", amount_paid: "",
    outlet_id: "", photo_url: "", attachment_url: "", attachment_name: "",
  };
  const [step, setStep] = useState(1);
  const [form, setForm] = useState(blank);
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const [nextCode, setNextCode] = useState("");
  const [batches, setBatches] = useState([]);
  const [uploading, setUploading] = useState("");
  const photoInput = useRef(null);
  const attachInput = useRef(null);

  useEffect(() => {
    if (!open) return;
    setStep(1);
    setErrors({});
    if (member) {
      setForm({
        ...blank, ...member,
        email: member.email || "",
        phone: (member.phone || "").replace(/\D/g, "").slice(-10),
        dob: member.dob || "", address: member.address || "", notes: member.notes || "",
        batch: member.batch || "", gender: member.gender || "",
        height: member.height || "", weight: member.weight || "",
        photo_url: member.photo_url || "", attachment_url: member.attachment_url || "", attachment_name: member.attachment_name || "",
      });
    } else {
      setForm(prefill ? { ...blank, ...prefill, phone: (prefill.phone || "").replace(/\D/g, "").slice(-10) } : blank);
      api.get("/members/next-code").then(({ data }) => setNextCode(data.member_code)).catch(() => {});
    }
    api.get("/batches").then(({ data }) => setBatches(data)).catch(() => {});
  }, [open, member, prefill]);

  const set = (k) => (e) => {
    const v = e?.target ? e.target.value : e;
    setForm((f) => ({ ...f, [k]: v }));
    setErrors((prev) => ({ ...prev, [k]: undefined }));
  };

  const plan = useMemo(() => plans.find((p) => p.id === form.plan_id), [plans, form.plan_id]);
  const planAmount = plan?.price || 0;
  const admission = Number(form.admission_amount || 0);
  const discount = Number(form.discount || 0);
  const collected = Number(form.amount_paid || 0);
  const payable = Math.max(0, planAmount + admission - discount);
  const due = Math.max(0, payable - collected);
  const payStatus = due === 0 && payable > 0 ? "Paid" : collected > 0 ? "Partially Paid" : "Due";
  const expiryPreview = plan ? addDuration(form.joining_date, plan.duration_type || "months", plan.duration || 1) : null;

  const next = () => {
    const errs = {};
    if (step === 1) {
      if (form.full_name.trim().length < 2) errs.full_name = "Enter the member's name";
      if (!/^\d{10}$/.test(form.phone.replace(/\D/g, "").slice(-10))) errs.phone = "Enter a valid 10-digit mobile number";
    }
    setErrors(errs);
    if (!Object.keys(errs).length) setStep(step + 1);
  };

  const pickPhoto = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setUploading("photo");
    try {
      const res = await uploadFile(file, "photo");
      setForm((f) => ({ ...f, photo_url: res.url }));
    } catch (err) {
      toast.error(apiError(err, "Photo upload failed"));
    } finally {
      setUploading("");
    }
  };

  const pickAttachment = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setUploading("attachment");
    try {
      const res = await uploadFile(file, "attachment");
      setForm((f) => ({ ...f, attachment_url: res.url, attachment_name: res.filename }));
    } catch (err) {
      toast.error(apiError(err, "Attachment upload failed"));
    } finally {
      setUploading("");
    }
  };

  const submit = async () => {
    setBusy(true);
    try {
      const batch = form.batch === "__new" ? form.new_batch.trim() : form.batch;
      if (editing) {
        await api.put(`/members/${member.id}`, {
          full_name: form.full_name, phone: form.phone, email: form.email || null,
          gender: form.gender || null, dob: form.dob || null, address: form.address || null,
          batch: batch || null, trainer: form.trainer || null, notes: form.notes || null,
          outlet_id: form.outlet_id || null, height: form.height || null, weight: form.weight || null,
          photo_url: form.photo_url || null, attachment_url: form.attachment_url || null, attachment_name: form.attachment_name || null,
        });
        toast.success("Member updated successfully");
      } else {
        if (!form.plan_id) { toast.error("Select a membership plan"); setBusy(false); return; }
        await api.post("/members", {
          full_name: form.full_name, phone: form.phone, email: form.email || null,
          gender: form.gender || null, dob: form.dob || null, address: form.address || null,
          batch: batch || null, notes: form.notes || null, height: form.height || null, weight: form.weight || null,
          photo_url: form.photo_url || null, attachment_url: form.attachment_url || null, attachment_name: form.attachment_name || null,
          joining_date: form.joining_date, payment_date: form.payment_date || undefined,
          plan_id: form.plan_id, membership_start: form.joining_date,
          admission_amount: admission, discount, amount_paid: collected,
          payment_method: form.payment_method, outlet_id: form.outlet_id || undefined,
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
      <DialogContent className="max-h-[92vh] max-w-2xl overflow-y-auto" data-testid="member-form-modal">
        <DialogHeader>
          <DialogTitle className="font-display text-lg">{editing ? "Edit Member" : "Add Member"}</DialogTitle>
        </DialogHeader>
        <Stepper step={step} total={totalSteps} />

        {step === 1 && (
          <div className="space-y-4" data-testid="member-step-1">
            <div className="flex items-center gap-4">
              <button type="button" onClick={() => photoInput.current?.click()} data-testid="member-photo-upload"
                      className="relative flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-full border-2 border-dashed border-border bg-secondary/50 text-muted-foreground transition-colors hover:border-brand hover:text-brand">
                {form.photo_url ? (
                  <img src={fileUrl(form.photo_url)} alt="Member" className="h-full w-full object-cover" />
                ) : uploading === "photo" ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Camera className="h-6 w-6" />
                )}
              </button>
              <input ref={photoInput} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={pickPhoto} />
              <div>
                <p className="text-sm font-semibold text-foreground">Profile Photo</p>
                <p className="text-xs text-muted-foreground">Tap to upload (JPG, PNG or WebP)</p>
              </div>
              <div className="ml-auto text-right">
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Member ID</p>
                <p className="font-num text-sm font-bold text-brand" data-testid="member-form-code">{editing ? member.member_code : nextCode || "…"}</p>
              </div>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="Name" required>
                <Input value={form.full_name} onChange={set("full_name")} placeholder="Enter full name" data-testid="member-form-name" />
                {errors.full_name && <p className="text-xs text-danger" data-testid="error-full-name">{errors.full_name}</p>}
              </Field>
              <Field label="Phone Number" required>
                <div className="flex">
                  <span className="inline-flex items-center gap-1.5 rounded-l-lg border border-r-0 border-input bg-secondary px-3 text-sm font-medium text-muted-foreground">+91</span>
                  <Input inputMode="numeric" className="rounded-l-none" placeholder="98765 43210" value={form.phone} onChange={set("phone")} data-testid="member-form-phone" />
                </div>
                {errors.phone && <p className="text-xs text-danger" data-testid="error-phone">{errors.phone}</p>}
              </Field>
              <Field label="Gender">
                <Select value={form.gender} onValueChange={set("gender")}>
                  <SelectTrigger data-testid="member-form-gender"><SelectValue placeholder="Select gender" /></SelectTrigger>
                  <SelectContent>{GENDERS.map((g) => <SelectItem key={g} value={g}>{g}</SelectItem>)}</SelectContent>
                </Select>
              </Field>
              <Field label="Batch">
                <Select value={form.batch} onValueChange={set("batch")}>
                  <SelectTrigger data-testid="member-form-batch"><SelectValue placeholder="Select batch" /></SelectTrigger>
                  <SelectContent>
                    {batches.map((b) => <SelectItem key={b.id} value={b.name} data-testid={`batch-option-${b.id}`}>{b.name}</SelectItem>)}
                    <SelectItem value="__new" data-testid="batch-option-new">+ New batch</SelectItem>
                  </SelectContent>
                </Select>
              </Field>
              {form.batch === "__new" && (
                <Field label="New Batch Name">
                  <Input value={form.new_batch} onChange={set("new_batch")} placeholder="e.g., Morning 6–8 AM" data-testid="member-form-new-batch" />
                </Field>
              )}
              {outlets.length > 1 && (
                <Field label="Outlet">
                  <Select value={form.outlet_id || outlets[0]?.id} onValueChange={set("outlet_id")}>
                    <SelectTrigger data-testid="member-form-outlet"><SelectValue /></SelectTrigger>
                    <SelectContent>{outlets.map((o) => <SelectItem key={o.id} value={o.id}>{o.name}</SelectItem>)}</SelectContent>
                  </Select>
                </Field>
              )}
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4" data-testid="member-step-2">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="Email"><Input type="email" value={form.email} onChange={set("email")} placeholder="member@email.com" data-testid="member-form-email" /></Field>
              <Field label="Date of Birth"><DateField value={form.dob} onChange={(v) => setForm((f) => ({ ...f, dob: v }))} testid="member-form-dob" /></Field>
              <Field label="Height (cm)"><Input type="number" min="0" value={form.height} onChange={set("height")} placeholder="e.g., 170" data-testid="member-form-height" /></Field>
              <Field label="Weight (kg)"><Input type="number" min="0" value={form.weight} onChange={set("weight")} placeholder="e.g., 68" data-testid="member-form-weight" /></Field>
              <div className="sm:col-span-2"><Field label="Address"><Input value={form.address} onChange={set("address")} placeholder="Full address" data-testid="member-form-address" /></Field></div>
              <div className="sm:col-span-2"><Field label="Notes"><Textarea rows={2} value={form.notes} onChange={set("notes")} placeholder="Health conditions, goals, anything relevant" data-testid="member-form-notes" /></Field></div>
            </div>
            <div>
              <Label>Attachment</Label>
              <div className="mt-1.5">
                {form.attachment_url ? (
                  <div className="flex items-center justify-between rounded-lg border border-border bg-secondary/50 px-3 py-2.5" data-testid="attachment-chip">
                    <a href={fileUrl(form.attachment_url)} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-sm font-medium text-brand hover:underline">
                      <Paperclip className="h-4 w-4" />{form.attachment_name || "Attachment"}
                    </a>
                    <button type="button" onClick={() => setForm((f) => ({ ...f, attachment_url: "", attachment_name: "" }))} className="text-muted-foreground hover:text-danger" aria-label="Remove attachment">
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ) : (
                  <button type="button" onClick={() => attachInput.current?.click()} disabled={uploading === "attachment"} data-testid="member-attachment-upload"
                          className="flex w-full items-center justify-center gap-2 rounded-lg border-2 border-dashed border-border px-4 py-5 text-sm font-medium text-muted-foreground transition-colors hover:border-brand hover:text-brand">
                    {uploading === "attachment" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Paperclip className="h-4 w-4" />}
                    Upload document (image or PDF, max 10 MB)
                  </button>
                )}
                <input ref={attachInput} type="file" accept="image/jpeg,image/png,image/webp,image/gif,application/pdf" className="hidden" onChange={pickAttachment} />
              </div>
            </div>
          </div>
        )}

        {step === 3 && !editing && (
          <div className="space-y-4" data-testid="member-step-3">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field label="Joining Date" required><DateField value={form.joining_date} onChange={(v) => setForm((f) => ({ ...f, joining_date: v }))} testid="member-form-joining" /></Field>
              <Field label="Payment Date"><DateField value={form.payment_date} onChange={(v) => setForm((f) => ({ ...f, payment_date: v }))} testid="member-form-payment-date" /></Field>
              <Field label="Select Plan" required>
                <Select value={form.plan_id} onValueChange={set("plan_id")}>
                  <SelectTrigger data-testid="member-form-plan"><SelectValue placeholder="Select plan" /></SelectTrigger>
                  <SelectContent>
                    {plans.length === 0 && <SelectItem value="__none" disabled>No plans yet — create one in Plans & Catalogue</SelectItem>}
                    {plans.map((p) => (
                      <SelectItem key={p.id} value={p.id} data-testid={`plan-option-${p.id}`}>{p.name} — {inr(p.price)} / {p.duration} {p.duration_type}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
              <Field label="Admission Amount (₹)"><Input type="number" min="0" value={form.admission_amount} onChange={set("admission_amount")} placeholder="0" data-testid="member-form-admission" /></Field>
              <Field label="Discount Amount (₹)"><Input type="number" min="0" value={form.discount} onChange={set("discount")} placeholder="0" data-testid="member-form-discount" /></Field>
              <Field label="Amount Collected (₹)"><Input type="number" min="0" value={form.amount_paid} onChange={set("amount_paid")} placeholder="0" data-testid="member-form-amount-paid" /></Field>
              <Field label="Payment Mode">
                <Select value={form.payment_method} onValueChange={set("payment_method")}>
                  <SelectTrigger data-testid="member-form-method"><SelectValue /></SelectTrigger>
                  <SelectContent>{METHODS.map((m) => <SelectItem key={m} value={m}>{m}</SelectItem>)}</SelectContent>
                </Select>
              </Field>
            </div>
            <div className="rounded-xl border border-border bg-secondary/40 p-4" data-testid="payment-summary">
              <div className="flex items-center justify-between">
                <p className="font-display text-sm font-bold text-foreground">Payment Summary</p>
                <span className={`badge-status ${payStatus === "Paid" ? "badge-active" : payStatus === "Partially Paid" ? "badge-expiring" : "badge-expired"}`} data-testid="payment-status-badge">{payStatus}</span>
              </div>
              <div className="mt-3 space-y-1.5 text-sm">
                <div className="flex justify-between"><span className="text-muted-foreground">Plan Amount</span><span className="font-num font-medium text-foreground" data-testid="summary-plan-amount">{inr(planAmount)}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Admission Amount</span><span className="font-num font-medium text-foreground" data-testid="summary-admission">{inr(admission)}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Discount</span><span className="font-num font-medium text-success" data-testid="summary-discount">− {inr(discount)}</span></div>
                <div className="flex justify-between border-t border-border pt-1.5"><span className="font-semibold text-foreground">Amount Payable</span><span className="font-num font-bold text-foreground" data-testid="summary-payable">{inr(payable)}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Amount Collected</span><span className="font-num font-medium text-foreground" data-testid="summary-collected">{inr(collected)}</span></div>
                <div className="flex justify-between"><span className="font-semibold text-foreground">Due Amount</span><span className={`font-num font-bold ${due > 0 ? "text-danger" : "text-success"}`} data-testid="summary-due">{inr(due)}</span></div>
              </div>
              {plan && expiryPreview && (
                <p className="mt-3 border-t border-border pt-2.5 text-xs text-muted-foreground" data-testid="membership-window-preview">
                  Membership: <span className="font-num font-semibold text-foreground">{formatDate(form.joining_date)}</span> → <span className="font-num font-semibold text-foreground">{formatDate(expiryPreview)}</span> ({plan.duration} {plan.duration_type})
                </p>
              )}
            </div>
          </div>
        )}

        <div className="mt-6 flex justify-between gap-3">
          {step > 1 ? (
            <Button type="button" variant="outline" onClick={() => setStep(step - 1)} data-testid="member-form-prev">Previous</Button>
          ) : <span />}
          {step < totalSteps ? (
            <Button type="button" className="bg-brand hover:bg-brand-hover" onClick={next} data-testid="member-form-next">Next</Button>
          ) : (
            <Button type="button" className="bg-success font-semibold text-white hover:bg-success/90" onClick={submit} disabled={busy} data-testid="member-form-submit">
              {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}{editing ? "Save Changes" : "Save Member"}
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
