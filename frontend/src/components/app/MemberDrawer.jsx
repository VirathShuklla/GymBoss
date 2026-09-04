import { useEffect, useState } from "react";
import {
  Phone, MessageCircle, Snowflake, Info, Pencil, Trash2, ClipboardCheck,
  RefreshCw, IndianRupee, BellRing, Receipt, ChevronRight, X, Loader2,
} from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { inr, formatDate, formatPhone } from "../../lib/format";
import { waMe, WA_TEMPLATES, fillTemplate } from "../../lib/whatsapp";
import { useAuth } from "../../contexts/AuthContext";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "../ui/sheet";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/dialog";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Textarea } from "../ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { StatusBadge, ConfirmDialog, DateField } from "./ui";
import { ReceiptModal } from "./ReceiptModal";
import { ReminderModal } from "./ReminderModal";

const METHODS = ["Cash", "UPI", "Card", "Bank Transfer", "Other"];

function ActionRow({ icon: Icon, label, onClick, danger, highlight, testid }) {
  return (
    <button onClick={onClick} data-testid={testid}
            className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left transition-colors ${
              danger ? "hover:bg-danger/10" : highlight ? "bg-brand/8 hover:bg-brand/12" : "hover:bg-secondary"
            }`}>
      <span className={`flex h-9 w-9 items-center justify-center rounded-full ${danger ? "bg-danger/12 text-danger" : highlight ? "bg-brand/12 text-brand" : "bg-secondary text-foreground"}`}>
        <Icon className="h-[18px] w-[18px]" />
      </span>
      <span className={`flex-1 text-sm font-semibold ${danger ? "text-danger" : "text-foreground"}`}>{label}</span>
      <ChevronRight className={`h-4 w-4 ${danger ? "text-danger" : "text-muted-foreground"}`} />
    </button>
  );
}

export function MemberDrawer({ memberId, onClose, onChanged, onEdit, plans }) {
  const { organisation, user } = useAuth();
  const readOnly = user?.permission === "view" && user?.role !== "owner";
  const [data, setData] = useState(null);
  const [view, setView] = useState("actions");
  const [freezeOpen, setFreezeOpen] = useState(false);
  const [renewOpen, setRenewOpen] = useState(false);
  const [payOpen, setPayOpen] = useState(false);
  const [waOpen, setWaOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [reminderOpen, setReminderOpen] = useState(false);
  const [receipt, setReceipt] = useState(null);
  const [busy, setBusy] = useState(false);
  const defaultFreezeUntil = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10);
  const [freezeForm, setFreezeForm] = useState({ freeze_from: new Date().toISOString().slice(0, 10), freeze_until: defaultFreezeUntil, reason: "" });
  const [renewForm, setRenewForm] = useState({ plan_id: "", discount: 0, amount_paid: 0, payment_method: "Cash" });
  const [payForm, setPayForm] = useState({ amount: "", method: "Cash", notes: "" });
  const [waTemplate, setWaTemplate] = useState("payment_reminder");
  const [waCustom, setWaCustom] = useState("");

  const load = async () => {
    if (!memberId) return;
    const { data } = await api.get(`/members/${memberId}`);
    setData(data);
  };

  useEffect(() => {
    setView("actions");
    setData(null);
    load();
  }, [memberId]);

  const m = data?.member;
  const openWa = (templateKey) => {
    const tpl = WA_TEMPLATES.find((t) => t.key === (templateKey || waTemplate));
    const body = tpl.key === "custom" ? waCustom : fillTemplate(tpl.body, {
      member_name: m.full_name.split(" ")[0],
      gym_name: organisation?.name,
      plan_name: m.plan_name,
      expiry_date: formatDate(m.membership_expiry),
      due_amount: inr(m.due_amount),
    });
    window.open(waMe(m.phone, body), "_blank");
    setWaOpen(false);
  };

  const doFreeze = async () => {
    if (!freezeForm.freeze_until) return toast.error("Select freeze-until date");
    setBusy(true);
    try {
      await api.post(`/members/${m.id}/freeze`, freezeForm);
      toast.success("Membership frozen");
      setFreezeOpen(false);
      load(); onChanged();
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };

  const doUnfreeze = async () => {
    setBusy(true);
    try {
      await api.post(`/members/${m.id}/unfreeze`);
      toast.success("Membership unfrozen");
      load(); onChanged();
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };

  const doRenew = async () => {
    if (!renewForm.plan_id) return toast.error("Select a plan");
    setBusy(true);
    try {
      await api.post(`/members/${m.id}/renew`, { ...renewForm, discount: Number(renewForm.discount || 0), amount_paid: Number(renewForm.amount_paid || 0) });
      toast.success("Membership renewed");
      setRenewOpen(false);
      await load(); onChanged();
      if (Number(renewForm.amount_paid) > 0) {
        const { data: fresh } = await api.get(`/members/${m.id}`);
        if (fresh.payments[0]) viewReceipt(fresh.payments[0].id);
      }
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };

  const doPay = async () => {
    if (!Number(payForm.amount)) return toast.error("Enter an amount");
    setBusy(true);
    try {
      const { data: payment } = await api.post("/payments", { member_id: m.id, amount: Number(payForm.amount), method: payForm.method, notes: payForm.notes || null });
      toast.success("Payment recorded");
      setPayOpen(false);
      setPayForm({ amount: "", method: "Cash", notes: "" });
      load(); onChanged();
      viewReceipt(payment.id);
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };

  const doDelete = async () => {
    setBusy(true);
    try {
      await api.delete(`/members/${m.id}`);
      toast.success("Member deleted");
      setDeleteOpen(false);
      onClose(); onChanged();
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };

  const viewReceipt = async (paymentId) => {
    const { data } = await api.get(`/payments/${paymentId}/receipt`);
    setReceipt(data);
  };

  return (
    <>
      <Sheet open={Boolean(memberId)} onOpenChange={(o) => !o && onClose()}>
        <SheetContent className="w-full overflow-y-auto p-0 sm:max-w-md" data-testid="member-detail-drawer">
          <SheetHeader className="sr-only"><SheetTitle>Member Details</SheetTitle></SheetHeader>
          {!m ? (
            <div className="flex h-64 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-brand" /></div>
          ) : (
            <div>
              <div className="border-b border-border p-5">
                <div className="flex items-start gap-3.5">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-brand/15 font-display text-base font-bold text-brand">
                    {m.full_name.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase()}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-display text-lg font-bold text-foreground" data-testid="drawer-member-name">{m.full_name}</p>
                    <p className="font-num text-xs text-muted-foreground">{m.member_code} · {formatPhone(m.phone)}</p>
                    {m.email && <p className="truncate text-xs text-muted-foreground">{m.email}</p>}
                  </div>
                  <div className="flex gap-1.5">
                    <a href={`tel:${m.phone}`} className="flex h-9 w-9 items-center justify-center rounded-full bg-secondary text-foreground hover:bg-elevated" data-testid="drawer-call" aria-label="Call member">
                      <Phone className="h-4 w-4" />
                    </a>
                    <button onClick={() => setWaOpen(true)} className="flex h-9 w-9 items-center justify-center rounded-full bg-[#25D366]/15 text-[#25D366] hover:bg-[#25D366]/25" data-testid="drawer-whatsapp" aria-label="WhatsApp member">
                      <MessageCircle className="h-4 w-4" />
                    </button>
                  </div>
                </div>
                <div className="mt-4 rounded-xl border border-border bg-secondary/40 p-4" data-testid="drawer-membership-summary">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-display text-sm font-bold text-foreground">{m.plan_name}</p>
                      <p className="font-num text-xs text-muted-foreground">{inr(m.plan_price)}</p>
                    </div>
                    <StatusBadge status={m.status} />
                  </div>
                  <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
                    <div><p className="text-muted-foreground">Start</p><p className="font-num mt-0.5 font-semibold text-foreground">{formatDate(m.membership_start)}</p></div>
                    <div><p className="text-muted-foreground">Expiry</p><p className="font-num mt-0.5 font-semibold text-foreground">{formatDate(m.membership_expiry)}</p></div>
                    <div><p className="text-muted-foreground">Days Left</p><p className={`font-num mt-0.5 font-bold ${(m.days_left ?? 0) < 0 ? "text-danger" : (m.days_left ?? 99) <= 7 ? "text-warning" : "text-success"}`}>{m.days_left ?? "—"}</p></div>
                  </div>
                  {m.due_amount > 0 && (
                    <div className="mt-3 flex items-center justify-between rounded-lg bg-danger/10 px-3 py-2 text-xs">
                      <span className="font-medium text-danger">Due Amount</span>
                      <span className="font-num font-bold text-danger" data-testid="drawer-due-amount">{inr(m.due_amount)}</span>
                    </div>
                  )}
                </div>
              </div>

              {view === "actions" && (
                <div className="p-4" data-testid="member-action-sheet">
                  <p className="px-2 pb-2 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Member</p>
                  <div className="space-y-1">
                    {!readOnly && (m.status === "frozen"
                      ? <ActionRow icon={Snowflake} label="Unfreeze Membership" onClick={doUnfreeze} testid="action-unfreeze" />
                      : <ActionRow icon={Snowflake} label="Freeze" onClick={() => setFreezeOpen(true)} testid="action-freeze" />)}
                    <ActionRow icon={Info} label="Show More Info" onClick={() => setView("info")} testid="action-more-info" />
                    {!readOnly && <ActionRow icon={Pencil} label="Edit Member" onClick={() => onEdit(m)} testid="action-edit-member" />}
                    {!readOnly && <ActionRow icon={Trash2} label="Delete Member" danger onClick={() => setDeleteOpen(true)} testid="action-delete-member" />}
                    <ActionRow icon={ClipboardCheck} label="Attendance History" highlight onClick={() => setView("attendance")} testid="action-attendance-history" />
                  </div>
                  {!readOnly && (
                    <>
                      <p className="px-2 pb-2 pt-4 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Payments</p>
                      <div className="space-y-1">
                        <ActionRow icon={RefreshCw} label="Renew Membership" onClick={() => { setRenewForm({ ...renewForm, plan_id: m.plan_id }); setRenewOpen(true); }} testid="action-renew" />
                        <ActionRow icon={IndianRupee} label="Record Payment" onClick={() => setPayOpen(true)} testid="action-record-payment" />
                      </div>
                    </>
                  )}
                  <div className="space-y-1 pt-1">
                    <ActionRow icon={BellRing} label="Send Payment Reminder" onClick={() => setReminderOpen(true)} testid="action-payment-reminder" />
                    <ActionRow icon={Receipt} label="Transaction History" onClick={() => setView("payments")} testid="action-transaction-history" />
                  </div>
                  <button onClick={onClose} data-testid="action-sheet-close"
                          className="mt-5 w-full rounded-xl border border-border py-3 text-sm font-semibold text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground">
                    Close
                  </button>
                </div>
              )}

              {view === "attendance" && (
                <DrawerList title="Attendance History" onBack={() => setView("actions")} testid="drawer-attendance-list"
                            empty="No check-ins recorded yet"
                            items={data.attendance.map((a) => ({
                              id: a.id,
                              title: formatDate(a.check_in),
                              sub: `Check-in ${new Date(a.check_in).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}${a.check_out ? ` · Out ${new Date(a.check_out).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}` : ""}`,
                            }))} />
              )}

              {view === "payments" && (
                <div className="p-4">
                  <DrawerTitle title="Transaction History" onBack={() => setView("actions")} />
                  {data.payments.length === 0 ? (
                    <p className="py-8 text-center text-sm text-muted-foreground">No transactions yet</p>
                  ) : (
                    <div className="space-y-2" data-testid="drawer-payments-list">
                      {data.payments.map((p) => (
                        <div key={p.id} className="flex items-center justify-between rounded-lg border border-border px-3 py-2.5" data-testid={`drawer-payment-${p.id}`}>
                          <div>
                            <p className="text-sm font-semibold text-foreground">{p.plan_name || "Payment"}</p>
                            <p className="text-xs text-muted-foreground">{formatDate(p.created_at)} · {p.method} · {p.receipt_no}</p>
                          </div>
                          <div className="text-right">
                            <p className="font-num text-sm font-bold text-success">{inr(p.amount)}</p>
                            <button onClick={() => viewReceipt(p.id)} className="text-xs font-medium text-brand hover:underline" data-testid={`receipt-view-${p.id}`}>Receipt</button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {view === "info" && (
                <div className="p-4" data-testid="drawer-more-info">
                  <DrawerTitle title="Member Information" onBack={() => setView("actions")} />
                  <div className="space-y-2.5 rounded-xl border border-border p-4 text-sm">
                    {[["Member ID", m.member_code], ["Phone", formatPhone(m.phone)], ["Email", m.email], ["Gender", m.gender],
                      ["Date of Birth", formatDate(m.dob)], ["Address", m.address], ["Batch", m.batch], ["Trainer", m.trainer],
                      ["Joined", formatDate(m.joining_date)], ["Notes", m.notes]].map(([k, v]) => (
                      <div key={k} className="flex justify-between gap-4">
                        <span className="shrink-0 text-muted-foreground">{k}</span>
                        <span className="text-right font-medium text-foreground">{v || "—"}</span>
                      </div>
                    ))}
                  </div>
                  {m.freeze_history?.length > 0 && (
                    <div className="mt-4">
                      <p className="pb-2 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Freeze History</p>
                      {m.freeze_history.map((f, i) => (
                        <div key={i} className="mb-2 rounded-lg border border-border px-3 py-2 text-xs">
                          <p className="font-medium text-foreground">{formatDate(f.freeze_from)} → {formatDate(f.freeze_until)} ({f.days} days)</p>
                          {f.reason && <p className="text-muted-foreground">{f.reason}</p>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </SheetContent>
      </Sheet>

      <Dialog open={freezeOpen} onOpenChange={setFreezeOpen}>
        <DialogContent className="max-w-sm" data-testid="freeze-modal">
          <DialogHeader><DialogTitle className="font-display">Freeze Membership</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5"><Label>Freeze From</Label><DateField value={freezeForm.freeze_from} onChange={(v) => setFreezeForm({ ...freezeForm, freeze_from: v })} testid="freeze-from" /></div>
            <div className="space-y-1.5"><Label>Freeze Until</Label><DateField value={freezeForm.freeze_until} onChange={(v) => setFreezeForm({ ...freezeForm, freeze_until: v })} testid="freeze-until" /></div>
            <div className="space-y-1.5"><Label>Reason <span className="font-normal text-muted-foreground">(optional)</span></Label><Input value={freezeForm.reason} onChange={(e) => setFreezeForm({ ...freezeForm, reason: e.target.value })} placeholder="e.g., Travelling" data-testid="freeze-reason" /></div>
            <p className="text-xs text-muted-foreground">Membership expiry will be extended by the freeze duration.</p>
            <Button className="w-full bg-brand hover:bg-brand-hover" onClick={doFreeze} disabled={busy} data-testid="freeze-submit">
              {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Freeze Membership
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={renewOpen} onOpenChange={setRenewOpen}>
        <DialogContent className="max-w-sm" data-testid="renew-modal">
          <DialogHeader><DialogTitle className="font-display">Renew Membership</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label>Plan</Label>
              <Select value={renewForm.plan_id} onValueChange={(v) => setRenewForm({ ...renewForm, plan_id: v })}>
                <SelectTrigger data-testid="renew-plan"><SelectValue placeholder="Select plan" /></SelectTrigger>
                <SelectContent>
                  {plans.length === 0 && <SelectItem value="__none" disabled>No plans yet — create one in Plans & Catalogue</SelectItem>}
                  {plans.map((p) => <SelectItem key={p.id} value={p.id}>{p.name} — {inr(p.price)}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5"><Label>Discount (₹)</Label><Input type="number" min="0" value={renewForm.discount} onChange={(e) => setRenewForm({ ...renewForm, discount: e.target.value })} data-testid="renew-discount" /></div>
              <div className="space-y-1.5"><Label>Amount Paid (₹)</Label><Input type="number" min="0" value={renewForm.amount_paid} onChange={(e) => setRenewForm({ ...renewForm, amount_paid: e.target.value })} data-testid="renew-amount" /></div>
            </div>
            <div className="space-y-1.5">
              <Label>Payment Method</Label>
              <Select value={renewForm.payment_method} onValueChange={(v) => setRenewForm({ ...renewForm, payment_method: v })}>
                <SelectTrigger data-testid="renew-method"><SelectValue /></SelectTrigger>
                <SelectContent>{METHODS.map((x) => <SelectItem key={x} value={x}>{x}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <Button className="w-full bg-brand hover:bg-brand-hover" onClick={doRenew} disabled={busy} data-testid="renew-submit">
              {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Renew Membership
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={payOpen} onOpenChange={setPayOpen}>
        <DialogContent className="max-w-sm" data-testid="payment-modal">
          <DialogHeader><DialogTitle className="font-display">Record Payment</DialogTitle></DialogHeader>
          <div className="space-y-4">
            {m?.due_amount > 0 && <p className="rounded-lg bg-danger/10 px-3 py-2 text-xs font-medium text-danger">Outstanding due: {inr(m.due_amount)}</p>}
            <div className="space-y-1.5"><Label>Amount (₹)</Label><Input type="number" min="1" value={payForm.amount} onChange={(e) => setPayForm({ ...payForm, amount: e.target.value })} data-testid="payment-amount" /></div>
            <div className="space-y-1.5">
              <Label>Payment Method</Label>
              <Select value={payForm.method} onValueChange={(v) => setPayForm({ ...payForm, method: v })}>
                <SelectTrigger data-testid="payment-method"><SelectValue /></SelectTrigger>
                <SelectContent>{METHODS.map((x) => <SelectItem key={x} value={x}>{x}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5"><Label>Notes <span className="font-normal text-muted-foreground">(optional)</span></Label><Input value={payForm.notes} onChange={(e) => setPayForm({ ...payForm, notes: e.target.value })} data-testid="payment-notes" /></div>
            <Button className="w-full bg-brand hover:bg-brand-hover" onClick={doPay} disabled={busy} data-testid="payment-submit">
              {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Record Payment
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={waOpen} onOpenChange={setWaOpen}>
        <DialogContent className="max-w-sm" data-testid="whatsapp-modal">
          <DialogHeader><DialogTitle className="font-display">WhatsApp Message</DialogTitle></DialogHeader>
          {m && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">To <span className="font-semibold text-foreground">{m.full_name}</span> ({formatPhone(m.phone)})</p>
              <div className="space-y-1.5">
                <Label>Template</Label>
                <Select value={waTemplate} onValueChange={setWaTemplate}>
                  <SelectTrigger data-testid="wa-template"><SelectValue /></SelectTrigger>
                  <SelectContent>{WA_TEMPLATES.map((t) => <SelectItem key={t.key} value={t.key} data-testid={`wa-template-${t.key}`}>{t.label}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              {waTemplate === "custom" ? (
                <Textarea rows={4} value={waCustom} onChange={(e) => setWaCustom(e.target.value)} placeholder="Type your message" data-testid="wa-custom-message" />
              ) : (
                <div className="rounded-lg border border-border bg-secondary/40 p-3 text-sm text-muted-foreground" data-testid="wa-preview">
                  {fillTemplate(WA_TEMPLATES.find((t) => t.key === waTemplate).body, {
                    member_name: m.full_name.split(" ")[0], gym_name: organisation?.name,
                    plan_name: m.plan_name, expiry_date: formatDate(m.membership_expiry), due_amount: inr(m.due_amount),
                  })}
                </div>
              )}
              <Button className="w-full bg-[#25D366] font-semibold text-white hover:bg-[#1fb857]" onClick={() => openWa()} data-testid="wa-send-button">
                <MessageCircle className="mr-2 h-4 w-4" />Open in WhatsApp
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <ConfirmDialog open={deleteOpen} onClose={() => setDeleteOpen(false)} onConfirm={doDelete} busy={busy}
                     testid="delete-member-confirm" title="Delete Member?"
                     description={`Are you sure you want to delete ${m?.full_name}? This action cannot be undone.`}
                     confirmLabel="Delete Member" />
      <ReceiptModal receipt={receipt} onClose={() => setReceipt(null)} />
      {m && (
        <ReminderModal member={m} gymName={organisation?.name} payments={data?.payments}
                       open={reminderOpen} onClose={() => setReminderOpen(false)} />
      )}
    </>
  );
}

function DrawerTitle({ title, onBack }) {
  return (
    <div className="mb-3 flex items-center gap-2">
      <button onClick={onBack} className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground" data-testid="drawer-back" aria-label="Back">
        <X className="h-4 w-4" />
      </button>
      <p className="font-display text-sm font-bold text-foreground">{title}</p>
    </div>
  );
}

function DrawerList({ title, onBack, items, empty, testid }) {
  return (
    <div className="p-4">
      <DrawerTitle title={title} onBack={onBack} />
      {items.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">{empty}</p>
      ) : (
        <div className="space-y-2" data-testid={testid}>
          {items.map((item) => (
            <div key={item.id} className="rounded-lg border border-border px-3 py-2.5">
              <p className="text-sm font-semibold text-foreground">{item.title}</p>
              <p className="text-xs text-muted-foreground">{item.sub}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
