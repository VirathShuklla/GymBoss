import { useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { formatPhone } from "../../lib/format";
import { useAuth } from "../../contexts/AuthContext";
import { PageHeader } from "../../components/app/ui";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";

export default function Profile() {
  const { user, organisation, reload } = useAuth();
  const [form, setForm] = useState({ full_name: user?.full_name || "", phone: (user?.phone || "").replace(/\D/g, "").slice(-10) });
  const [busy, setBusy] = useState(false);

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

  return (
    <div data-testid="profile-page">
      <PageHeader title="My Profile" subtitle="Your account details." testid="profile-header" />
      <div className="max-w-md rounded-xl border border-border bg-card p-6 shadow-card">
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
    </div>
  );
}
