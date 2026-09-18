import { useEffect, useState } from "react";
import { Users, RefreshCw, IndianRupee, MessageCircle, ChevronRight, ChevronLeft, Search, X, Receipt } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { inr, formatDate } from "../../lib/format";
import { useAuth } from "../../contexts/AuthContext";
import { waMe, buildReceiptMessage } from "../../lib/whatsapp";
import { buildReminderOptions } from "../reminders";
import { MButton, Field, TextInput, PhoneInput, Pills, BottomSheet, ListSkeleton, EmptyRow, StatusChip } from "../ui";
import { ModuleHeader } from "./ModuleHeader";

const EMPTY = { full_name: "", phone: "", gender: "Male", plan_id: "", batch: "", admission_amount: "", amount_paid: "", discount: "", payment_method: "Cash" };

export default function Members({ autoAdd }) {
  const { organisation } = useAuth();
  const [items, setItems] = useState(null);
  const [plans, setPlans] = useState([]);
  const [open, setOpen] = useState(autoAdd === "member");
  const [f, setF] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [q, setQ] = useState("");
  const [chip, setChip] = useState("all");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  // member actions
  const [active, setActive] = useState(null);
  const [detail, setDetail] = useState(null);
  const [view, setView] = useState(null); // menu | renew | payment | reminder
  const [remSel, setRemSel] = useState(null);
  const [rf, setRf] = useState({ plan_id: "", discount: "", amount_paid: "", payment_method: "Cash" });
  const [pf, setPf] = useState({ amount: "", method: "Cash" });
  const [abusy, setAbusy] = useState(false);
  const [receipt, setReceipt] = useState(null);
  const [editP, setEditP] = useState(null);
  const [editAmt, setEditAmt] = useState("");

  const load = (search = q) =>
    api.get(`/members?limit=100${search && search.trim() ? `&search=${encodeURIComponent(search.trim())}` : ""}`).then(({ data }) => setItems(data.items)).catch(() => setItems([]));
  useEffect(() => {
    load("");
    api.get("/plans?type=membership").then(({ data }) => setPlans(data)).catch(() => {});
  }, []);
  useEffect(() => {
    const t = setTimeout(() => load(q), 350);
    return () => clearTimeout(t);
  }, [q]);

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

  const openMember = (m) => {
    setActive(m);
    setDetail(null);
    setRemSel(null);
    setRf({ plan_id: "", discount: "", amount_paid: "", payment_method: "Cash" });
    setPf({ amount: String(m.due_amount || ""), method: "Cash" });
    setView("menu");
    api.get(`/members/${m.id}`).then(({ data }) => setDetail(data)).catch(() => {});
  };
  const closeActions = () => { setView(null); setActive(null); setDetail(null); setRemSel(null); setReceipt(null); setEditP(null); };

  const showReceipt = async (paymentId) => {
    try {
      const { data } = await api.get(`/payments/${paymentId}/receipt`);
      setReceipt(data);
      setView("receipt");
    } catch { closeActions(); }
  };

  const cur = detail?.member || active;

  const doRenew = async () => {
    if (!rf.plan_id) return toast.error("Please select a plan");
    setAbusy(true);
    try {
      await api.post(`/members/${active.id}/renew`, {
        plan_id: rf.plan_id,
        discount: Number(rf.discount) || 0,
        amount_paid: Number(rf.amount_paid) || 0,
        payment_method: rf.payment_method,
      });
      toast.success("Membership renewed");
      load();
      if (Number(rf.amount_paid) > 0) {
        const { data: fresh } = await api.get(`/members/${active.id}`);
        const pid = fresh.payments?.[0]?.id;
        if (pid) { await showReceipt(pid); return; }
      }
      closeActions();
    } catch (e) {
      toast.error(apiError(e, "Could not renew"));
    } finally {
      setAbusy(false);
    }
  };

  const doPayment = async () => {
    if (!(Number(pf.amount) > 0)) return toast.error("Enter a valid amount");
    setAbusy(true);
    try {
      const { data: payment } = await api.post("/payments", { member_id: active.id, amount: Number(pf.amount), method: pf.method });
      toast.success("Payment recorded");
      load();
      await showReceipt(payment.id);
    } catch (e) {
      toast.error(apiError(e, "Could not record payment"));
    } finally {
      setAbusy(false);
    }
  };

  const remOptions = buildReminderOptions(cur, organisation?.name, detail?.payments);
  const reloadDetail = async () => { const { data } = await api.get(`/members/${active.id}`); setDetail(data); };
  const reversePayment = async (pid) => {
    setAbusy(true);
    try { await api.delete(`/payments/${pid}`); toast.success("Payment reversed — due updated"); await reloadDetail(); load(); }
    catch (e) { toast.error(apiError(e, "Could not reverse payment")); } finally { setAbusy(false); }
  };
  const saveEditP = async () => {
    if (!Number(editAmt)) return toast.error("Enter an amount");
    setAbusy(true);
    try { await api.put(`/payments/${editP}`, { amount: Number(editAmt) }); toast.success("Payment updated — due recalculated"); setEditP(null); await reloadDetail(); load(); }
    catch (e) { toast.error(apiError(e, "Could not update payment")); } finally { setAbusy(false); }
  };
  const sheetTitle = { menu: cur?.full_name, renew: "Renew Membership", payment: "Record Payment", reminder: "Send WhatsApp Reminder", receipt: "Payment Receipt", history: "Payment History" }[view];

  const shown = (items || []).filter((m) =>
    chip === "all" ? true
      : chip === "active" ? m.status === "active"
      : chip === "expiring" ? m.status === "expiring_soon"
      : chip === "due" ? (m.due_amount || 0) > 0 : true);

  return (
    <div data-testid="m-members">
      <ModuleHeader title={items ? `${items.length} members` : "Members"} onAdd={() => setOpen(true)} addLabel="Add Member" testid="m-members-add" />
      <div className="relative mb-3">
        <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          data-testid="m-members-search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search by name, phone or ID"
          className="h-12 w-full rounded-xl border border-input bg-background pl-10 pr-10 text-[15px] text-foreground outline-none placeholder:text-muted-foreground focus:border-brand"
        />
        {q && (
          <button onClick={() => setQ("")} data-testid="m-members-search-clear" aria-label="Clear search"
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground">
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      <div className="no-scrollbar mb-3 flex gap-2 overflow-x-auto" data-testid="m-members-chips">
        {[{ k: "all", l: "All" }, { k: "active", l: "Active" }, { k: "expiring", l: "Expiring" }, { k: "due", l: "Due" }].map((c) => (
          <button key={c.k} data-testid={`m-chip-${c.k}`} onClick={() => setChip(c.k)}
            className={`shrink-0 rounded-full px-4 py-1.5 text-sm font-semibold transition-colors ${chip === c.k ? "bg-brand text-white" : "bg-secondary text-muted-foreground"}`}>
            {c.l}
          </button>
        ))}
      </div>

      {!items ? (
        <ListSkeleton />
      ) : shown.length === 0 ? (
        <EmptyRow icon={Users} title={q || chip !== "all" ? "No members found" : "No members yet"} subtitle={q || chip !== "all" ? "Try a different search or filter." : "Add your first member to get started."} testid="m-members-empty" />
      ) : (
        <div className="space-y-2.5">
          {shown.map((m) => (
            <button key={m.id} onClick={() => openMember(m)} data-testid={`m-member-${m.id}`}
              className="flex w-full items-center gap-3 rounded-2xl border border-border bg-card px-4 py-3 text-left active:scale-[0.99]">
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
              <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
            </button>
          ))}
        </div>
      )}

      {/* Add member */}
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

      {/* Member actions */}
      <BottomSheet open={!!view} onOpenChange={(o) => !o && closeActions()} title={sheetTitle}
        subtitle={view === "menu" && cur ? `${cur.member_code} · ${cur.plan_name}` : undefined} testid="m-member-actions">
        {view === "menu" && cur && (
          <>
            <div className="flex items-center justify-between rounded-2xl bg-secondary/60 px-4 py-3">
              <StatusChip status={cur.status} />
              <div className="text-right">
                <p className="text-[11px] text-muted-foreground">Expires {formatDate(cur.membership_expiry)}</p>
                {cur.due_amount > 0 && <p className="font-num text-xs font-bold text-danger">Due {inr(cur.due_amount)}</p>}
              </div>
            </div>
            <ActionRow icon={RefreshCw} tile="bg-brand/12 text-brand" title="Renew Membership" desc="Extend with a plan" onClick={() => setView("renew")} testid="m-action-renew" />
            <ActionRow icon={IndianRupee} tile="bg-success/12 text-success" title="Record Payment" desc={cur.due_amount > 0 ? `Collect towards ${inr(cur.due_amount)} due` : "Collect a payment"} onClick={() => setView("payment")} testid="m-action-payment" />
            <ActionRow icon={MessageCircle} tile="bg-[#25D366]/12 text-[#25D366]" title="Send WhatsApp Reminder" desc="Expiry, dues or invoice" onClick={() => setView("reminder")} testid="m-action-reminder" />
            <ActionRow icon={Receipt} tile="bg-secondary text-foreground" title="Payment History" desc="Edit or reverse payments" onClick={() => setView("history")} testid="m-action-history" />
          </>
        )}

        {view === "renew" && (
          <>
            <BackBtn onClick={() => setView("menu")} />
            <Field label="New plan">
              {plans.length === 0 ? (
                <p className="text-xs text-muted-foreground">No membership plans yet.</p>
              ) : (
                <Pills options={plans.map((p) => ({ value: p.id, label: `${p.name} · ${inr(p.price)}` }))} value={rf.plan_id} onChange={(v) => setRf({ ...rf, plan_id: v })} />
              )}
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Discount"><TextInput inputMode="numeric" value={rf.discount} onChange={(e) => setRf({ ...rf, discount: e.target.value })} placeholder="0" /></Field>
              <Field label="Amount collected"><TextInput inputMode="numeric" data-testid="m-renew-paid" value={rf.amount_paid} onChange={(e) => setRf({ ...rf, amount_paid: e.target.value })} placeholder="0" /></Field>
            </div>
            <Field label="Payment method"><Pills options={["Cash", "UPI", "Card"]} value={rf.payment_method} onChange={(v) => setRf({ ...rf, payment_method: v })} /></Field>
            <MButton onClick={doRenew} loading={abusy} disabled={!rf.plan_id} data-testid="m-renew-save">Renew Membership</MButton>
          </>
        )}

        {view === "payment" && (
          <>
            <BackBtn onClick={() => setView("menu")} />
            {cur?.due_amount > 0 && <p className="rounded-xl bg-danger/8 px-3 py-2 text-xs font-semibold text-danger">Outstanding due: {inr(cur.due_amount)}</p>}
            <Field label="Amount"><TextInput inputMode="numeric" data-testid="m-payment-amount" value={pf.amount} onChange={(e) => setPf({ ...pf, amount: e.target.value })} placeholder="0" /></Field>
            <Field label="Method"><Pills options={["Cash", "UPI", "Card", "Bank Transfer"]} value={pf.method} onChange={(v) => setPf({ ...pf, method: v })} /></Field>
            <MButton onClick={doPayment} loading={abusy} disabled={!(Number(pf.amount) > 0)} data-testid="m-payment-save">Record Payment</MButton>
          </>
        )}

        {view === "history" && (
          <>
            <BackBtn onClick={() => { setEditP(null); setView("menu"); }} />
            {!detail?.payments?.length ? (
              <p className="py-6 text-center text-sm text-muted-foreground" data-testid="m-history-empty">No transactions yet</p>
            ) : (
              <div className="space-y-2" data-testid="m-history-list">
                {detail.payments.map((p) => (
                  <div key={p.id} className="rounded-2xl border border-border bg-card p-3" data-testid={`m-history-${p.id}`}>
                    <div className="flex items-center justify-between">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-foreground">{p.plan_name || "Payment"}</p>
                        <p className="text-xs text-muted-foreground">{formatDate(p.created_at)} · {p.method} · {p.receipt_no}</p>
                      </div>
                      <p className="font-num text-sm font-bold text-success">{inr(p.amount)}</p>
                    </div>
                    {editP === p.id ? (
                      <div className="mt-2 flex items-center gap-2">
                        <TextInput inputMode="numeric" value={editAmt} onChange={(e) => setEditAmt(e.target.value)} data-testid={`m-history-edit-input-${p.id}`} />
                        <button onClick={saveEditP} disabled={abusy} className="shrink-0 rounded-lg bg-brand px-3 py-2 text-xs font-semibold text-white" data-testid={`m-history-save-${p.id}`}>Save</button>
                        <button onClick={() => setEditP(null)} className="shrink-0 rounded-lg border border-border px-3 py-2 text-xs">Cancel</button>
                      </div>
                    ) : (
                      <div className="mt-2 flex gap-4">
                        <button onClick={() => { setEditP(p.id); setEditAmt(String(p.amount)); }} className="text-xs font-semibold text-brand" data-testid={`m-history-edit-${p.id}`}>Edit amount</button>
                        <button onClick={() => reversePayment(p.id)} disabled={abusy} className="text-xs font-semibold text-danger" data-testid={`m-history-reverse-${p.id}`}>Reverse</button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {view === "reminder" && (
          <>
            <BackBtn onClick={() => (remSel ? setRemSel(null) : setView("menu"))} />
            {!remSel ? (
              remOptions.length === 0 ? (
                <p className="py-6 text-center text-sm text-muted-foreground">No reminders available for this member.</p>
              ) : (
                <div className="space-y-2.5">
                  {remOptions.map((opt) => (
                    <ActionRow key={opt.key} icon={opt.icon} tile={opt.tile} title={opt.title} desc={opt.desc} onClick={() => setRemSel(opt)} testid={`m-reminder-${opt.key}`} />
                  ))}
                </div>
              )
            ) : (
              <>
                <p className="mb-2 text-xs font-bold uppercase tracking-wider text-muted-foreground">{remSel.title} — preview</p>
                <div className="whitespace-pre-line rounded-2xl border border-border bg-secondary/50 p-4 text-sm leading-relaxed text-foreground" data-testid="m-reminder-preview">{remSel.message}</div>
                <a href={waMe(cur.phone, remSel.message)} target="_blank" rel="noopener noreferrer" onClick={closeActions}
                  className="mt-4 flex h-[52px] w-full items-center justify-center gap-2 rounded-2xl bg-[#25D366] text-[15px] font-semibold text-white active:scale-[0.98]"
                  data-testid="m-reminder-send">
                  <MessageCircle className="h-5 w-5" /> Send via WhatsApp
                </a>
              </>
            )}
          </>
        )}

        {view === "receipt" && receipt && (
          <>
            <div className="rounded-2xl border border-success/25 bg-success/10 p-5 text-center">
              <p className="text-sm font-bold text-success">Payment recorded</p>
              <p className="font-num mt-1 text-3xl font-extrabold text-foreground">{inr(receipt.payment.amount)}</p>
              <p className="mt-0.5 text-xs text-muted-foreground">Receipt {receipt.payment.receipt_no}</p>
            </div>
            <a href={waMe(receipt.member?.phone, buildReceiptMessage(receipt))} target="_blank" rel="noopener noreferrer" onClick={closeActions}
              className="mt-4 flex h-[52px] w-full items-center justify-center gap-2 rounded-2xl bg-[#25D366] text-[15px] font-semibold text-white active:scale-[0.98]"
              data-testid="m-receipt-whatsapp">
              <MessageCircle className="h-5 w-5" /> Send receipt on WhatsApp
            </a>
            <button onClick={closeActions} data-testid="m-receipt-done"
              className="mt-2 h-11 w-full rounded-2xl border border-border text-sm font-semibold text-muted-foreground">Done</button>
          </>
        )}
      </BottomSheet>
    </div>
  );
}

function ActionRow({ icon: Icon, tile, title, desc, onClick, testid }) {
  return (
    <button onClick={onClick} data-testid={testid}
      className="flex w-full items-center gap-3.5 rounded-2xl border border-border bg-card px-4 py-3.5 text-left active:scale-[0.99]">
      <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full ${tile}`}><Icon className="h-5 w-5" /></span>
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-bold text-foreground">{title}</span>
        <span className="block truncate text-xs text-muted-foreground">{desc}</span>
      </span>
      <ChevronRight className="h-4 w-4 text-muted-foreground" />
    </button>
  );
}

function BackBtn({ onClick }) {
  return (
    <button onClick={onClick} className="mb-1 inline-flex items-center gap-1 text-xs font-semibold text-muted-foreground" data-testid="m-action-back">
      <ChevronLeft className="h-3.5 w-3.5" /> Back
    </button>
  );
}
