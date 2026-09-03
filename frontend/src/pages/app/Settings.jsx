import { useState } from "react";
import { Loader2, Moon, Sun, Monitor, MessageCircle, CreditCard, Crown } from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { inr } from "../../lib/format";
import { useAuth } from "../../contexts/AuthContext";
import { useTheme } from "../../contexts/ThemeContext";
import { PageHeader } from "../../components/app/ui";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";

export default function Settings() {
  const { organisation, subscription, user, reload } = useAuth();
  const { theme, setTheme } = useTheme();
  const [profile, setProfile] = useState({ name: organisation?.name || "", city: organisation?.city || "" });
  const [busy, setBusy] = useState(false);

  const saveProfile = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.put("/gym/profile", profile);
      toast.success("Gym profile updated");
      reload();
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setBusy(false);
    }
  };

  const themes = [
    { value: "light", label: "Light", icon: Sun },
    { value: "dark", label: "Dark", icon: Moon },
    { value: "system", label: "System", icon: Monitor },
  ];

  return (
    <div data-testid="settings-page">
      <PageHeader title="Settings" subtitle="Your gym, preferences and integrations." testid="settings-header" />
      <Tabs defaultValue="profile">
        <TabsList className="mb-5 flex-wrap" data-testid="settings-tabs">
          <TabsTrigger value="profile" data-testid="settings-tab-profile">Gym Profile</TabsTrigger>
          <TabsTrigger value="appearance" data-testid="settings-tab-appearance">Appearance</TabsTrigger>
          <TabsTrigger value="integrations" data-testid="settings-tab-integrations">Integrations</TabsTrigger>
          <TabsTrigger value="subscription" data-testid="settings-tab-subscription">Subscription</TabsTrigger>
        </TabsList>

        <TabsContent value="profile">
          <form onSubmit={saveProfile} className="max-w-md space-y-4 rounded-xl border border-border bg-card p-6 shadow-card" data-testid="gym-profile-form">
            <div className="space-y-1.5"><Label>Gym Name</Label><Input value={profile.name} onChange={(e) => setProfile({ ...profile, name: e.target.value })} data-testid="settings-gym-name" /></div>
            <div className="space-y-1.5"><Label>City</Label><Input value={profile.city || ""} onChange={(e) => setProfile({ ...profile, city: e.target.value })} data-testid="settings-gym-city" /></div>
            <Button className="bg-brand hover:bg-brand-hover" disabled={busy} data-testid="settings-save-profile">
              {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Save Changes
            </Button>
          </form>
        </TabsContent>

        <TabsContent value="appearance">
          <div className="max-w-md rounded-xl border border-border bg-card p-6 shadow-card" data-testid="appearance-settings">
            <p className="mb-4 text-sm text-muted-foreground">Choose how GymBoss_VVO looks on this device.</p>
            <div className="grid grid-cols-3 gap-3">
              {themes.map((t) => (
                <button key={t.value} onClick={() => setTheme(t.value)} data-testid={`appearance-${t.value}`}
                        className={`flex flex-col items-center gap-2 rounded-xl border-2 px-4 py-5 transition-colors ${
                          theme === t.value ? "border-brand bg-brand/8 text-brand" : "border-border text-muted-foreground hover:border-muted-foreground/50"
                        }`}>
                  <t.icon className="h-5 w-5" />
                  <span className="text-sm font-semibold">{t.label}</span>
                </button>
              ))}
            </div>
          </div>
        </TabsContent>

        <TabsContent value="integrations">
          <div className="grid max-w-3xl gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-border bg-card p-6 shadow-card" data-testid="integration-whatsapp">
              <div className="flex items-center justify-between">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#25D366]/12 text-[#25D366]"><MessageCircle className="h-5 w-5" /></div>
                <span className="badge-status badge-expiring">Not Connected</span>
              </div>
              <p className="mt-3 font-display text-base font-bold text-foreground">WhatsApp Business API</p>
              <p className="mt-1 text-sm text-muted-foreground">Connect the official Meta WhatsApp Business Platform to send bulk and automated announcements. Individual click-to-WhatsApp messaging already works.</p>
              <p className="mt-3 text-xs text-muted-foreground">Contact BuildVVO support to enable this integration for your gym.</p>
            </div>
            <div className="rounded-xl border border-border bg-card p-6 shadow-card" data-testid="integration-razorpay">
              <div className="flex items-center justify-between">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand/12 text-brand"><CreditCard className="h-5 w-5" /></div>
                <span className="badge-status badge-expiring">Not Connected</span>
              </div>
              <p className="mt-3 font-display text-base font-bold text-foreground">Razorpay</p>
              <p className="mt-1 text-sm text-muted-foreground">Powers your GymBoss_VVO subscription billing (₹999/month). Online activation is being enabled by BuildVVO.</p>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="subscription">
          <div className="max-w-md rounded-xl border border-border bg-card p-6 shadow-card" data-testid="subscription-settings">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand/12 text-brand"><Crown className="h-5 w-5" /></div>
              <div>
                <p className="font-display text-base font-bold text-foreground">
                  {subscription?.status === "trial" ? `Free Trial — ${subscription.trial_days_left} days left` : subscription?.status === "active" ? "Active Subscription" : "Subscription"}
                </p>
                <p className="text-sm text-muted-foreground">{inr(subscription?.plan_price_inr || 999)}/month</p>
              </div>
            </div>
            <Link to="/app/subscription" data-testid="settings-manage-subscription"
                  className="mt-5 inline-block rounded-lg bg-brand px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-hover">
              Manage Subscription
            </Link>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
