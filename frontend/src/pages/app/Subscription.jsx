import { useEffect, useState } from "react";
import { Crown, Loader2, Check, ShieldCheck, Sparkles } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { inr, formatDate } from "../../lib/format";
import { useAuth } from "../../contexts/AuthContext";
import { usePublicConfig, waLink } from "../../hooks/usePublicConfig";
import { PageHeader, DataTable, StatusBadge, EmptyState } from "../../components/app/ui";
import { Button } from "../../components/ui/button";

const INCLUDED = [
  "Unlimited members & staff",
  "All modules included",
  "Multi-outlet support",
  "WhatsApp reminders & invoices",
  "Reports & exports",
  "Priority support",
];

function loadRazorpayScript() {
  return new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = "https://checkout.razorpay.com/v1/checkout.js";
    s.onload = resolve;
    s.onerror = reject;
    document.body.appendChild(s);
  });
}

export default function Subscription() {
  const { user, reload } = useAuth();
  const config = usePublicConfig();
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    const { data } = await api.get("/subscription");
    setData(data);
  };
  useEffect(() => { load(); }, []);

  const pay = async () => {
    setBusy(true);
    try {
      const { data: sub } = await api.post("/subscription/autodebit/start");
      await loadRazorpayScript();
      const rzp = new window.Razorpay({
        key: sub.key_id,
        subscription_id: sub.subscription_id,
        name: "GymBoss_VVO",
        description: `GymBoss_VVO Pro — ${inr(sub.amount / 100)}/month`,
        prefill: { name: user?.full_name, email: user?.email, contact: user?.phone },
        theme: { color: "#7C3AED" },
        handler: async (resp) => {
          try {
            await api.post("/subscription/autodebit/verify", resp);
            toast.success("Subscription activated. Welcome aboard!");
            await reload();
            load();
          } catch (e) {
            toast.error(apiError(e, "Payment verification failed"));
          }
        },
      });
      rzp.on("payment.failed", () => toast.error("Payment failed. No amount was charged."));
      rzp.open();
    } catch (e) {
      toast.error(apiError(e, "Could not start payment"), { duration: 6000 });
    } finally {
      setBusy(false);
    }
  };

  const sub = data?.subscription;
  const autodebit = data?.autodebit;
  const autodebitActive = autodebit?.status === "active";
  const autodebitHalted = autodebit?.status === "halted";
  const price = sub?.plan_price_inr || 999;
  const isTrial = sub?.status === "trial";
  const isActive = sub?.status === "active";
  const needsPayment = !isActive;
  const trialPct = isTrial ? Math.round(((10 - (sub?.trial_days_left ?? 10)) / 10) * 100) : 100;

  const statusMeta = {
    trial: { label: "Free Trial", cls: "badge-frozen" },
    active: { label: "Active", cls: "badge-active" },
    expired: { label: "Trial Ended", cls: "badge-expired" },
    payment_due: { label: "Payment Due", cls: "badge-expiring" },
    cancelled: { label: "Cancelled", cls: "badge-expired" },
  }[sub?.status] || { label: sub?.status, cls: "badge-frozen" };

  const columns = [
    { key: "created_at", label: "Date", render: (p) => formatDate(p.created_at) },
    { key: "order_id", label: "Reference", render: (p) => <span className="font-num text-xs text-muted-foreground">{p.order_id}</span> },
    { key: "amount", label: "Amount", align: "right", render: (p) => <span className="font-num font-bold text-foreground">{inr(p.amount)}</span> },
    { key: "status", label: "Status", align: "right", render: (p) => <StatusBadge status={p.status} label={p.status === "paid" ? "Paid" : p.status === "failed" ? "Failed" : "Pending"} /> },
  ];

  return (
    <div data-testid="subscription-page">
      <PageHeader title="Subscription" subtitle="Your GymBoss_VVO plan and billing." testid="subscription-header" />

      <div className="grid items-start gap-5 lg:grid-cols-5">
        <div className="rounded-xl border border-border bg-card p-6 shadow-card lg:col-span-3" data-testid="subscription-status-card">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand/12 text-brand"><Crown className="h-5 w-5" /></div>
              <div>
                <p className="font-display text-lg font-bold text-foreground" data-testid="subscription-status">
                  {isTrial ? "Free Trial" : isActive ? "GymBoss_VVO Pro" : "Subscription"}
                </p>
                <p className="text-sm text-muted-foreground">
                  {isTrial && `Ends ${formatDate(sub?.trial_ends_at)}`}
                  {isActive && sub?.subscription_ends_at && `Active until ${formatDate(sub.subscription_ends_at)}`}
                  {sub?.status === "expired" && "Your free trial has ended"}
                  {sub?.status === "payment_due" && "Your last paid period has ended"}
                </p>
              </div>
            </div>
            <span className={`badge-status ${statusMeta.cls}`}>{statusMeta.label}{isTrial ? ` · ${sub?.trial_days_left} days left` : ""}</span>
          </div>

          {isTrial && (
            <div className="mt-5">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Trial progress</span>
                <span className="font-num font-semibold text-foreground">{10 - (sub?.trial_days_left ?? 10)} of 10 days used</span>
              </div>
              <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-secondary">
                <div className="h-full rounded-full bg-brand transition-all" style={{ width: `${trialPct}%` }} data-testid="trial-progress-bar" />
              </div>
            </div>
          )}

          {autodebitActive && (
            <div className="mt-5 flex items-center gap-2.5 rounded-lg border border-success/25 bg-success/8 px-4 py-3" data-testid="autodebit-active-card">
              <Check className="h-4 w-4 shrink-0 text-success" strokeWidth={3} />
              <p className="text-sm text-foreground">
                Billing is active — {inr(price)}/month{sub?.subscription_ends_at ? `, paid through ${formatDate(sub.subscription_ends_at)}` : ""}.
                <span className="text-muted-foreground"> Manage it from My Profile.</span>
              </p>
            </div>
          )}
          {autodebitHalted && (
            <div className="mt-5 rounded-lg border border-warning/30 bg-warning/10 px-4 py-3" data-testid="autodebit-halted-card">
              <p className="text-sm font-bold text-warning">Last charge didn't go through</p>
              <p className="mt-0.5 text-xs text-muted-foreground">Tap Pay below to retry and keep your access uninterrupted.</p>
            </div>
          )}

          <div className="mt-5 flex items-start gap-2.5 rounded-lg bg-secondary/50 px-4 py-3">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-brand" />
            <p className="text-xs leading-relaxed text-muted-foreground">
              Your gym data is always safe — we never delete it, even if a trial ends. Cancel anytime from My Profile; access continues until the end of your paid period.
            </p>
          </div>
        </div>

        <div className="overflow-hidden rounded-xl border border-border bg-card shadow-card lg:col-span-2" data-testid="subscription-plan-card">
          <div className="bg-gradient-to-br from-brand to-[#5B21B6] px-6 py-6 text-white">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 opacity-80" />
              <p className="text-xs font-bold uppercase tracking-wider opacity-80">GymBoss_VVO Pro</p>
            </div>
            <p className="mt-2 font-display text-4xl font-extrabold tracking-tight">
              {inr(price)}<span className="text-base font-semibold opacity-80">/month</span>
            </p>
            <p className="mt-1 text-xs opacity-75">per gym · all outlets included</p>
          </div>
          <div className="p-6">
            <ul className="grid grid-cols-1 gap-2.5">
              {INCLUDED.map((f) => (
                <li key={f} className="flex items-center gap-2.5 text-sm text-foreground">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-success/12"><Check className="h-3 w-3 text-success" strokeWidth={3.5} /></span>
                  {f}
                </li>
              ))}
            </ul>
            {isActive && !autodebitHalted ? (
              <div className="mt-6 flex items-center justify-center gap-2 rounded-lg border border-success/25 bg-success/8 py-3 text-sm font-semibold text-success" data-testid="subscribed-badge">
                <Check className="h-4 w-4" strokeWidth={3} />You're subscribed
              </div>
            ) : data?.razorpay_configured ? (
              <Button className="mt-6 h-11 w-full rounded-xl bg-brand text-base font-semibold hover:bg-brand-hover" onClick={pay} disabled={busy} data-testid="subscribe-button">
                {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Pay {inr(price)}/month
              </Button>
            ) : (
              <div className="mt-6 rounded-lg border border-border bg-secondary/40 p-3 text-xs text-muted-foreground" data-testid="razorpay-not-configured">
                <p className="flex items-center gap-1.5 font-medium text-foreground"><ShieldCheck className="h-3.5 w-3.5 shrink-0" />Online payments are being enabled by BuildVVO.</p>
                {config?.whatsapp_number ? (
                  <a className="mt-1 inline-block font-semibold text-brand hover:underline" href={waLink(config.whatsapp_number, "Hi, I want to activate my GymBoss_VVO subscription.")} target="_blank" rel="noopener noreferrer" data-testid="subscription-whatsapp-link">
                    Contact us on WhatsApp to activate instantly.
                  </a>
                ) : config?.support_email ? (
                  <a className="mt-1 inline-block font-semibold text-brand hover:underline" href={`mailto:${config.support_email}?subject=GymBoss_VVO subscription activation`} data-testid="subscription-support-email-link">
                    Email us to activate instantly.
                  </a>
                ) : null}
              </div>
            )}
            {needsPayment && data?.razorpay_configured && (
              <p className="mt-3 text-center text-[11px] leading-relaxed text-muted-foreground">
                Secure payment via Razorpay · UPI, cards & netbanking
              </p>
            )}
          </div>
        </div>
      </div>

      <h2 className="mb-3 mt-8 font-display text-sm font-bold uppercase tracking-wider text-muted-foreground">Payment History</h2>
      <DataTable testid="subscription-payments-table" columns={columns} rows={data?.payments || []} loading={!data}
                 empty={<EmptyState icon={Crown} title="No subscription payments yet" testid="subscription-payments-empty" />} />
    </div>
  );
}
