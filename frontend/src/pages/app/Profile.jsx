import { useEffect, useState } from "react";
import { Loader2, Crown } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { inr, formatDate } from "../../lib/format";
import { useAuth } from "../../contexts/AuthContext";
import { PageHeader, ConfirmDialog } from "../../components/app/ui";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";

export default function Profile() {
  const { user, organisation, reload } = useAuth();
  const [form, setForm] = useState({ full_name: user?.full_name || "", phone: (user?.phone || "").replace(/\D/g, "").slice(-10) });
  const [busy, setBusy] = useState(false);
  const [sub, setSub] = useState(null);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelBusy, setCancelBusy] = useState(false);

  useEffect(() => {
    api.get("/subscription").then(({ data }) => setSub(data)).catch(() => {});
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.put("/profile", form);
      toast.success("Profile updated");
      reload();
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setBusy(false);
    }
  };

  const cancelSubscription = async () => {
    setCancelBusy(true);
    try {
      const res = await api.post("/subscription/autodebit/cancel");
      toast.success(res.data.message);
      setCancelOpen(false);
      const { data } = await api.get("/subscription");
      setSub(data);
    } catch (err) {
      toast.error(apiError(err, "Could not cancel the subscription"));
    } finally {
      setCancelBusy(false);
    }
  };

  const autodebit = sub?.autodebit;
  const canCancel = autodebit?.status === "active" || autodebit?.status === "halted" || autodebit?.status === "created";
  const price = sub?.subscription?.plan_price_inr || 999;

  return (
    <div data-testid="profile-page">
      <PageHeader title="My Profile" subtitle="Your account details." testid="profile-header" />
      <div className="grid max-w-4xl gap-5 lg:grid-cols-2">
        <div className="rounded-xl border border-border bg-card p-6 shadow-card">
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-brand/15 font-display text-lg font-bold text-brand">
              {user?.full_name?.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase()}
            </div>
            <div>
              <p className="font-display text-lg font-bold text-foreground" data-testid="profile-name">{user?.full_name}</p>
              <p className="text-sm text-muted-foreground">{organisation?.name} · <span className="capitalize">{user?.role}</span></p>
            </div>
          </div>
          <form onSubmit={submit} className="mt-6 space-y-4">
            <div className="space-y-1.5"><Label>Full Name</Label><Input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} data-testid="profile-full-name" /></div>
            <div className="space-y-1.5"><Label>Email</Label><Input value={user?.email || ""} disabled className="opacity-60" data-testid="profile-email" /></div>
            <div className="space-y-1.5"><Label>Phone</Label><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} data-testid="profile-phone" /></div>
            <Button className="bg-brand hover:bg-brand-hover" disabled={busy} data-testid="profile-save">
              {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Save Changes
            </Button>
          </form>
        </div>

        <div className="rounded-xl border border-border bg-card p-6 shadow-card" data-testid="profile-subscription-card">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand/12 text-brand"><Crown className="h-5 w-5" /></div>
            <div>
              <p className="font-display text-base font-bold text-foreground">Subscription</p>
              <p className="text-xs text-muted-foreground">GymBoss_VVO Pro · {inr(price)}/month</p>
            </div>
          </div>
          <div className="mt-4 text-sm">
            {!sub ? (
              <p className="text-muted-foreground">Loading…</p>
            ) : autodebit ? (
              <div className="space-y-1.5">
                <div className="flex justify-between"><span className="text-muted-foreground">Status</span><span className="font-semibold capitalize text-foreground">{autodebit.status}</span></div>
                {sub.subscription?.subscription_ends_at && (
                  <div className="flex justify-between"><span className="text-muted-foreground">Paid through</span><span className="font-num font-medium text-foreground">{formatDate(sub.subscription.subscription_ends_at)}</span></div>
                )}
              </div>
            ) : (
              <p className="text-muted-foreground">No active subscription billing yet.</p>
            )}
          </div>
          {canCancel && (
            <button onClick={() => setCancelOpen(true)} data-testid="profile-cancel-subscription"
                    className="mt-5 rounded-md border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:border-danger/40 hover:text-danger">
              Cancel Subscription
            </button>
          )}
        </div>
      </div>

      <ConfirmDialog open={cancelOpen} onClose={() => setCancelOpen(false)} onConfirm={cancelSubscription} busy={cancelBusy}
                     testid="profile-cancel-confirm" title="Cancel subscription?"
                     description="Monthly billing will stop. Your access continues until the end of the current paid period, and your gym data stays safe."
                     confirmLabel="Cancel Subscription" />
    </div>
  );
}
