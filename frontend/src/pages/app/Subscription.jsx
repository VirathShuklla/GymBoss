import { useEffect, useState } from "react";
import { Crown, Loader2, Check, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { inr, formatDate } from "../../lib/format";
import { useAuth } from "../../contexts/AuthContext";
import { usePublicConfig, waLink } from "../../hooks/usePublicConfig";
import { PageHeader, DataTable, StatusBadge, EmptyState } from "../../components/app/ui";
import { Button } from "../../components/ui/button";

const INCLUDED = ["Unlimited members", "All modules included", "Multi-outlet support", "WhatsApp communication", "Reports & exports", "Priority support"];

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
  const { user, organisation, reload } = useAuth();
  const config = usePublicConfig();
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    const { data } = await api.get("/subscription");
    setData(data);
  };
  useEffect(() => { load(); }, []);

  const subscribe = async () => {
    setBusy(true);
    try {
      const { data: order } = await api.post("/subscription/create-order");
      await loadRazorpayScript();
      const rzp = new window.Razorpay({
        key: order.key_id,
        amount: order.amount,
        currency: order.currency,
        name: "GymBoss_VVO",
        description: "GymBoss_VVO Monthly Subscription",
        order_id: order.order_id,
        prefill: { name: user?.full_name, email: user?.email, contact: user?.phone },
        theme: { color: "#7C3AED" },
        handler: async (resp) => {
          try {
            await api.post("/subscription/verify", resp);
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
      toast.error(apiError(e, "Payments are being configured. Please contact BuildVVO support."), { duration: 6000 });
    } finally {
      setBusy(false);
    }
  };

  const sub = data?.subscription;
  const statusLabel = { trial: `Free Trial — ${sub?.trial_days_left} days left`, active: "Active", expired: "Trial Ended", payment_due: "Payment Due", cancelled: "Cancelled" }[sub?.status] || sub?.status;

  const columns = [
    { key: "created_at", label: "Date", render: (p) => formatDate(p.created_at) },
    { key: "order_id", label: "Order", render: (p) => <span className="font-num text-xs text-muted-foreground">{p.order_id}</span> },
    { key: "amount", label: "Amount", align: "right", render: (p) => <span className="font-num font-bold text-foreground">{inr(p.amount)}</span> },
    { key: "status", label: "Status", render: (p) => <StatusBadge status={p.status} label={p.status === "paid" ? "Paid" : p.status === "failed" ? "Failed" : "Pending"} /> },
  ];

  return (
    <div data-testid="subscription-page">
      <PageHeader title="Subscription" subtitle="Your GymBoss_VVO plan and billing." testid="subscription-header" />
      <div className="grid max-w-4xl gap-5 lg:grid-cols-2">
        <div className="rounded-xl border border-border bg-card p-6 shadow-card" data-testid="subscription-status-card">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand/12 text-brand"><Crown className="h-5 w-5" /></div>
            <div>
              <p className="font-display text-lg font-bold text-foreground" data-testid="subscription-status">{statusLabel}</p>
              <p className="text-sm text-muted-foreground">
                {sub?.status === "trial" && `Trial ends ${formatDate(sub.trial_ends_at)}`}
                {sub?.status === "active" && `Renews — valid until ${formatDate(sub.subscription_ends_at)}`}
                {(sub?.status === "expired" || sub?.status === "payment_due") && "Subscribe to continue using GymBoss_VVO"}
              </p>
            </div>
          </div>
          <div className="mt-5 rounded-lg bg-secondary/50 px-4 py-3 text-sm text-muted-foreground">
            Your gym data is always safe — we never delete it, even if a trial ends.
          </div>
        </div>
        <div className="overflow-hidden rounded-xl border border-border bg-card shadow-card" data-testid="subscription-plan-card">
          <div className="bg-gradient-to-br from-brand to-[#5B21B6] px-6 py-5 text-white">
            <p className="text-xs font-bold uppercase tracking-wider opacity-80">GymBoss_VVO Pro</p>
            <p className="mt-1 font-display text-3xl font-extrabold">{inr(999)}<span className="text-base font-semibold opacity-80">/month</span></p>
          </div>
          <div className="p-6">
            <ul className="space-y-2">
              {INCLUDED.map((f) => (
                <li key={f} className="flex items-center gap-2 text-sm text-foreground"><Check className="h-4 w-4 text-success" strokeWidth={3} />{f}</li>
              ))}
            </ul>
            {sub?.status !== "active" && (
              <Button className="mt-5 w-full bg-brand font-semibold hover:bg-brand-hover" onClick={subscribe} disabled={busy} data-testid="subscribe-button">
                {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Subscribe Now — {inr(999)}/month
              </Button>
            )}
            {!data?.razorpay_configured && sub?.status !== "active" && (
              <p className="mt-3 flex items-start gap-1.5 text-xs text-muted-foreground" data-testid="razorpay-not-configured">
                <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                Online payments are being enabled by BuildVVO. {" "}
                {config?.whatsapp_number && <a className="font-semibold text-brand hover:underline" href={waLink(config.whatsapp_number, "Hi, I want to activate my GymBoss_VVO subscription.")} target="_blank" rel="noopener noreferrer">Contact us on WhatsApp</a>}
                {" "}to activate instantly.
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
