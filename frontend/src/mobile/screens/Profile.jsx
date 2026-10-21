import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { LogOut, Crown, Building2, Phone, Mail, ChevronRight, ShieldCheck, Sun, Moon, Monitor, Check, Loader2, KeyRound, FileText, Trash2 } from "lucide-react";
import { DeleteAccountSheet } from "../DeleteAccountSheet";
import { toast } from "sonner";
import { useAuth } from "../../contexts/AuthContext";
import { useTheme } from "../../contexts/ThemeContext";
import { inr, formatDate } from "../../lib/format";
import { usePublicConfig, waLink } from "../../hooks/usePublicConfig";
import api, { apiError } from "../../lib/api";
import { MButton } from "../ui";
import { PlanPicker, planPeriod } from "../../components/PlanPicker";
import { track } from "../../lib/track";
import { isInApp } from "../../lib/inApp";
import { StoreBillingNote } from "../../components/StoreBillingNote";
import { ChangePasswordSheet } from "../ChangePasswordSheet";

const inApp = isInApp();

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
  const [planId, setPlanId] = useState("monthly");
  const [pwOpen, setPwOpen] = useState(false);
  const [delOpen, setDelOpen] = useState(false);

  const loadBilling = async () => {
    try {
      const { data } = await api.get("/subscription");
      setBilling(data);
    } catch (e) { /* status card still works from context */ }
  };
  useEffect(() => { loadBilling(); }, []);

  const autodebit = billing?.autodebit;
  const autodebitActive = autodebit?.status === "active";
  const autodebitHalted = ["halted", "pending"].includes(autodebit?.status);
  const isActive = subscription?.status === "active";
  const needsPayment = !isActive || autodebitHalted;
  const plans = billing?.plans || [];
  const chosen = plans.find((p) => p.id === planId) || plans[0];
  const activePlan = plans.find((p) => p.id === subscription?.plan);
  const shownPrice = isActive ? (subscription?.amount || price) : (chosen?.effective_price || price);
  const shownPeriod = planPeriod(isActive ? (subscription?.plan_months || 1) : (chosen?.months || 1));

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
      const { data: sub } = await api.post("/subscription/autodebit/start", { plan_id: chosen?.id || "monthly" });
      await loadRazorpayScript();
      const rzp = new window.Razorpay({
        key: sub.key_id,
        subscription_id: sub.subscription_id,
        name: "GymBoss_VVO",
        description: `GymBoss_VVO ${chosen?.name || "Pro"} — ${inr(sub.amount / 100)}/${shownPeriod}`,
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
      rzp.on("payment.failed", (r) => { track("payment_failed", { plan: chosen?.id, reason: r?.error?.reason }); toast.error("Payment failed. No amount was charged."); });
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
      <h1 className="font-display text-[26px] font-bold tracking-tight text-foreground">Profile</h1>

      <div className="mt-5 flex items-center gap-4 px-1">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-secondary font-display text-lg font-bold text-foreground">
          {user?.full_name?.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase()}
        </div>
        <div className="min-w-0">
          <p className="truncate font-display text-lg font-bold text-foreground">{user?.full_name}</p>
          <p className="truncate text-sm capitalize text-muted-foreground">{user?.role}</p>
        </div>
      </div>

      <div className="m-hero mt-5 text-white" data-testid="m-sub-card">
        <div className="flex items-center gap-2">
          <Crown className="h-4 w-4 text-white/70" />
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-white/60">GymBoss_VVO Pro</p>
        </div>
        {!inApp && <p className="mt-2 font-num text-3xl font-extrabold" data-testid="m-sub-price">{inr(shownPrice)}<span className="text-sm font-semibold opacity-80">/{shownPeriod}</span></p>}
        {isActive && activePlan && <p className="text-xs opacity-80">{activePlan.name} plan</p>}
        <p className="mt-1 text-sm opacity-90">{statusText}</p>
      </div>

      {/* Payment / subscription action */}
      {isActive && autodebitActive && !autodebitHalted ? (
        <div className="mt-3 space-y-2.5">
          <div className="flex items-center gap-2.5 rounded-2xl border border-success/25 bg-success/8 px-4 py-3.5 text-sm text-foreground" data-testid="m-billing-active">
            <Check className="h-4 w-4 shrink-0 text-success" strokeWidth={3} />
            {inApp ? "Subscription active" : `Billing active — ${inr(shownPrice)}/${shownPeriod}`}{subscription?.subscription_ends_at ? `, paid through ${formatDate(subscription.subscription_ends_at)}` : ""}.
          </div>
          <button onClick={cancelAutodebit} disabled={cancelBusy} data-testid="m-cancel-autodebit"
            className="flex w-full items-center justify-center gap-2 rounded-2xl border border-border bg-card px-4 py-3 text-xs font-semibold text-muted-foreground active:scale-[0.99] disabled:opacity-60">
            {cancelBusy && <Loader2 className="h-3.5 w-3.5 animate-spin" />} Cancel auto-renewal
          </button>
        </div>
      ) : needsPayment && inApp ? (
        <StoreBillingNote className="mt-3" />
      ) : needsPayment && billing?.razorpay_configured ? (
        <div className="mt-3">
          {autodebitHalted && (
            <div className="mb-2.5 rounded-2xl border border-warning/30 bg-warning/10 px-4 py-3" data-testid="m-billing-halted">
              <p className="text-sm font-bold text-warning">Last charge didn't go through</p>
              <p className="mt-0.5 text-xs text-muted-foreground">Tap below to retry and keep your access uninterrupted.</p>
            </div>
          )}
          {plans.length > 1 && <div className="mb-3"><p className="mb-2 text-xs font-bold uppercase tracking-wider text-muted-foreground">Choose your plan</p><PlanPicker plans={plans} value={chosen?.id} onChange={setPlanId} testid="m-plan" /></div>}
          <MButton onClick={pay} loading={busy} data-testid="m-pay-button">
            Pay {inr(shownPrice)}/{shownPeriod}
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

      <GroupLabel>Your gym</GroupLabel>
      <div className="m-group">
        <Row icon={Building2} label={organisation?.name} sub={organisation?.city} />
        <Row icon={Phone} label={user?.phone || "—"} />
        <Row icon={Mail} label={user?.email || "—"} />
      </div>

      <GroupLabel>Appearance</GroupLabel>
      <div className="m-group grid grid-cols-3 gap-1 p-1" data-testid="m-appearance">
        {[{ v: "light", l: "Light", I: Sun }, { v: "dark", l: "Dark", I: Moon }, { v: "system", l: "System", I: Monitor }].map(({ v, l, I }) => (
          <button key={v} onClick={() => setTheme(v)} data-testid={`m-theme-${v}`}
            className={`flex min-h-[44px] items-center justify-center gap-1.5 rounded-2xl text-xs font-semibold transition-colors ${theme === v ? "bg-foreground text-background" : "text-muted-foreground"}`}>
            <I className="h-4 w-4" /> {l}
          </button>
        ))}
      </div>

      <GroupLabel>Account</GroupLabel>
      <div className="m-group">
        <button onClick={() => setPwOpen(true)} data-testid="m-change-password" className="m-group-row text-sm font-medium text-foreground">
          <KeyRound className="h-[18px] w-[18px] text-muted-foreground" /> Change password
          <ChevronRight className="ml-auto h-4 w-4 text-muted-foreground/60" />
        </button>
        <Link to="/privacy" data-testid="m-privacy-link" className="m-group-row text-sm font-medium text-foreground">
          <FileText className="h-[18px] w-[18px] text-muted-foreground" /> Privacy policy & terms
          <ChevronRight className="ml-auto h-4 w-4 text-muted-foreground/60" />
        </Link>
        {config?.whatsapp_number && (
          <a href={waLink(config.whatsapp_number, "Hi, I need help with GymBoss_VVO.")} target="_blank" rel="noopener noreferrer"
             className="m-group-row text-sm font-medium text-foreground" data-testid="m-support-link">
            <ShieldCheck className="h-[18px] w-[18px] text-muted-foreground" /> Help & support
            <ChevronRight className="ml-auto h-4 w-4 text-muted-foreground/60" />
          </a>
        )}
      </div>

      <div className="mt-6 space-y-1">
        <button onClick={doLogout} data-testid="m-logout"
          className="m-group flex w-full min-h-[52px] items-center justify-center gap-2 text-sm font-semibold text-danger active:bg-secondary">
          <LogOut className="h-[18px] w-[18px]" /> Log out
        </button>
        <button onClick={() => setDelOpen(true)} data-testid="m-delete-account"
          className="flex w-full min-h-[44px] items-center justify-center gap-2 rounded-2xl px-4 py-3 text-xs font-semibold text-muted-foreground outline-none transition-colors focus-visible:ring-2 focus-visible:ring-danger/40 active:text-danger">
          <Trash2 className="h-4 w-4" /> Delete my account
        </button>
      </div>
      <DeleteAccountSheet open={delOpen} onOpenChange={setDelOpen} />
      <p className="mt-6 text-center text-xs text-muted-foreground">GymBoss_VVO · v1.0.0</p>
      <ChangePasswordSheet open={pwOpen} onOpenChange={setPwOpen} />
    </div>
  );
}

function GroupLabel({ children }) {
  return <p className="mb-2 mt-6 px-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">{children}</p>;
}

function Row({ icon: Icon, label, sub }) {
  return (
    <div className="m-group-row">
      <Icon className="h-[18px] w-[18px] shrink-0 text-muted-foreground" />
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-foreground">{label}</p>
        {sub && <p className="truncate text-xs text-muted-foreground">{sub}</p>}
      </div>
    </div>
  );
}
