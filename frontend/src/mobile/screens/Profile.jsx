import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { LogOut, Crown, Building2, Phone, Mail, ChevronRight, ShieldCheck, Sun, Moon, Monitor, Check, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "../../contexts/AuthContext";
import { useTheme } from "../../contexts/ThemeContext";
import { inr, formatDate } from "../../lib/format";
import { usePublicConfig, waLink } from "../../hooks/usePublicConfig";
import api, { apiError } from "../../lib/api";
import { MButton } from "../ui";

function loadRazorpayScript() {
  return new Promise((resolve, reject) => {
    if (window.Razorpay) return resolve();
    const s = document.createElement("script");
    s.src = "https://checkout.razorpay.com/v1/checkout.js";
    s.onload = resolve;
    s.onerror = reject;
    document.body.appendChild(s);
  });
}

export default function Profile() {
  const navigate = useNavigate();
  const { user, organisation, subscription, reload } = useAuth();
  const { logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const config = usePublicConfig();
  const price = subscription?.plan_price_inr || 999;

  const [billing, setBilling] = useState(null);
  const [busy, setBusy] = useState(false);
  const [cancelBusy, setCancelBusy] = useState(false);

  const loadBilling = async () => {
    try {
      const { data } = await api.get("/subscription");
      setBilling(data);
    } catch (e) { /* status card still works from context */ }
  };
  useEffect(() => { loadBilling(); }, []);

  const autodebit = billing?.autodebit;
  const autodebitActive = autodebit?.status === "active";
  const autodebitHalted = autodebit?.status === "halted";
  const isActive = subscription?.status === "active";
  const needsPayment = !isActive || autodebitHalted;

  const statusText = {
    trial: `Free trial · ${subscription?.trial_days_left ?? 0} days left`,
    active: subscription?.subscription_ends_at ? `Active until ${formatDate(subscription.subscription_ends_at)}` : "Active",
    expired: "Trial ended",
    payment_due: "Payment due",
    cancelled: "Cancelled",
  }[subscription?.status] || subscription?.status;

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
            loadBilling();
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

  const cancelAutodebit = async () => {
    if (!window.confirm("Cancel auto-renewal? Your access continues until the end of your paid period.")) return;
    setCancelBusy(true);
    try {
      await api.post("/subscription/autodebit/cancel");
      toast.success("Auto-renewal cancelled. Access continues until your paid period ends.");
      loadBilling();
    } catch (e) {
      toast.error(apiError(e, "Could not cancel"));
    } finally {
      setCancelBusy(false);
    }
  };

  const doLogout = async () => {
    await logout();
    navigate("/m/welcome", { replace: true });
  };

  return (
    <div className="m-anim" data-testid="m-profile">
      <h1 className="font-display text-2xl font-extrabold tracking-tight text-foreground">Profile</h1>

      <div className="mt-5 flex items-center gap-4 rounded-3xl border border-border bg-card p-5">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-brand/12 font-display text-xl font-bold text-brand">
          {user?.full_name?.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase()}
        </div>
        <div className="min-w-0">
          <p className="truncate font-display text-lg font-bold text-foreground">{user?.full_name}</p>
          <p className="truncate text-sm capitalize text-muted-foreground">{user?.role}</p>
        </div>
      </div>

      <div className="mt-4 overflow-hidden rounded-3xl bg-gradient-to-br from-brand to-[#5B21B6] p-5 text-white shadow-xl shadow-brand/25" data-testid="m-sub-card">
        <div className="flex items-center gap-2">
          <Crown className="h-4 w-4 opacity-90" />
          <p className="text-xs font-bold uppercase tracking-wider opacity-90">GymBoss_VVO Pro</p>
        </div>
        <p className="mt-2 font-num text-3xl font-extrabold">{inr(price)}<span className="text-sm font-semibold opacity-80">/month</span></p>
        <p className="mt-1 text-sm opacity-90">{statusText}</p>
      </div>

      {/* Payment / subscription action */}
      {isActive && autodebitActive && !autodebitHalted ? (
        <div className="mt-3 space-y-2.5">
          <div className="flex items-center gap-2.5 rounded-2xl border border-success/25 bg-success/8 px-4 py-3.5 text-sm text-foreground" data-testid="m-billing-active">
            <Check className="h-4 w-4 shrink-0 text-success" strokeWidth={3} />
            Billing active — {inr(price)}/month{subscription?.subscription_ends_at ? `, paid through ${formatDate(subscription.subscription_ends_at)}` : ""}.
          </div>
          <button onClick={cancelAutodebit} disabled={cancelBusy} data-testid="m-cancel-autodebit"
            className="flex w-full items-center justify-center gap-2 rounded-2xl border border-border bg-card px-4 py-3 text-xs font-semibold text-muted-foreground active:scale-[0.99] disabled:opacity-60">
            {cancelBusy && <Loader2 className="h-3.5 w-3.5 animate-spin" />} Cancel auto-renewal
          </button>
        </div>
      ) : needsPayment && billing?.razorpay_configured ? (
        <div className="mt-3">
          {autodebitHalted && (
            <div className="mb-2.5 rounded-2xl border border-warning/30 bg-warning/10 px-4 py-3" data-testid="m-billing-halted">
              <p className="text-sm font-bold text-warning">Last charge didn't go through</p>
              <p className="mt-0.5 text-xs text-muted-foreground">Tap below to retry and keep your access uninterrupted.</p>
            </div>
          )}
          <MButton onClick={pay} loading={busy} data-testid="m-pay-button">
            Pay {inr(price)}/month
          </MButton>
          <p className="mt-2 text-center text-[11px] text-muted-foreground">Secure payment via Razorpay · UPI, cards & netbanking</p>
        </div>
      ) : needsPayment && billing && !billing.razorpay_configured ? (
        <div className="mt-3 rounded-2xl border border-border bg-secondary/40 p-4 text-xs text-muted-foreground" data-testid="m-razorpay-not-configured">
          <p className="flex items-center gap-1.5 font-medium text-foreground"><ShieldCheck className="h-3.5 w-3.5 shrink-0" />Online payments are being enabled.</p>
          {config?.whatsapp_number && (
            <a className="mt-1 inline-block font-semibold text-brand" href={waLink(config.whatsapp_number, "Hi, I want to activate my GymBoss_VVO subscription.")} target="_blank" rel="noopener noreferrer" data-testid="m-sub-whatsapp-link">
              Contact us on WhatsApp to activate.
            </a>
          )}
        </div>
      ) : null}

      <div className="mt-4 space-y-2.5">
        <p className="px-1 text-xs font-bold uppercase tracking-wide text-muted-foreground">Your Gym</p>
        <Row icon={Building2} label={organisation?.name} sub={organisation?.city} />
        <Row icon={Phone} label={user?.phone || "—"} />
        <Row icon={Mail} label={user?.email || "—"} />
      </div>

      <div className="mt-5">
        <p className="px-1 text-xs font-bold uppercase tracking-wide text-muted-foreground">Appearance</p>
        <div className="mt-2 grid grid-cols-3 gap-2" data-testid="m-appearance">
          {[{ v: "light", l: "Light", I: Sun }, { v: "dark", l: "Dark", I: Moon }, { v: "system", l: "System", I: Monitor }].map(({ v, l, I }) => (
            <button key={v} onClick={() => setTheme(v)} data-testid={`m-theme-${v}`}
              className={`flex flex-col items-center gap-1.5 rounded-2xl border py-3 text-xs font-semibold transition-colors ${theme === v ? "border-brand bg-brand/10 text-brand" : "border-border bg-card text-muted-foreground"}`}>
              <I className="h-5 w-5" /> {l}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-5 space-y-2.5">
        {config?.whatsapp_number && (
          <a href={waLink(config.whatsapp_number, "Hi, I need help with GymBoss_VVO.")} target="_blank" rel="noopener noreferrer"
             className="flex items-center gap-3 rounded-2xl border border-border bg-card px-4 py-3.5 text-sm font-semibold text-foreground" data-testid="m-support-link">
            <ShieldCheck className="h-5 w-5 text-[#25D366]" /> Help & Support
            <ChevronRight className="ml-auto h-4 w-4 text-muted-foreground" />
          </a>
        )}
        <button onClick={doLogout} data-testid="m-logout"
          className="flex w-full items-center gap-3 rounded-2xl border border-danger/25 bg-danger/5 px-4 py-3.5 text-sm font-semibold text-danger active:scale-[0.99]">
          <LogOut className="h-5 w-5" /> Logout
        </button>
      </div>
      <p className="mt-6 text-center text-xs text-muted-foreground/60">GymBoss_VVO · v1.0.0</p>
    </div>
  );
}

function Row({ icon: Icon, label, sub }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-border bg-card px-4 py-3.5">
      <Icon className="h-5 w-5 text-muted-foreground" />
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-foreground">{label}</p>
        {sub && <p className="truncate text-xs text-muted-foreground">{sub}</p>}
      </div>
    </div>
  );
}
