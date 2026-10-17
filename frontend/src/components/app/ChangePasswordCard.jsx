import { useState } from "react";
import { Loader2, KeyRound } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";

const EMPTY = { current_password: "", new_password: "", confirm: "" };

export function validatePasswordChange(f) {
  if (!f.current_password) return "Enter your current password";
  if (f.new_password.length < 8) return "New password must be at least 8 characters";
  if (f.new_password !== f.confirm) return "New passwords do not match";
  return "";
}

export function ChangePasswordCard() {
  const [f, setF] = useState(EMPTY);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => { setF({ ...f, [k]: e.target.value }); setError(""); };

  const submit = async (e) => {
    e.preventDefault();
    const v = validatePasswordChange(f);
    if (v) return setError(v);
    setBusy(true);
    try {
      const { data } = await api.post("/auth/change-password", { current_password: f.current_password, new_password: f.new_password });
      toast.success(data.message);
      setF(EMPTY);
    } catch (err) {
      setError(apiError(err, "Could not change password"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="rounded-xl border border-border bg-card p-6 shadow-card" data-testid="change-password-card">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand/12 text-brand"><KeyRound className="h-5 w-5" /></div>
        <div>
          <p className="font-display text-base font-bold text-foreground">Change Password</p>
          <p className="text-xs text-muted-foreground">You'll stay signed in here; other devices are signed out.</p>
        </div>
      </div>
      <div className="mt-5 space-y-4">
        {error && <div className="rounded-lg border border-danger/25 bg-danger/10 px-3.5 py-2.5 text-sm text-danger" data-testid="change-password-error">{error}</div>}
        <div className="space-y-1.5"><Label>Current Password</Label><Input type="password" autoComplete="current-password" value={f.current_password} onChange={set("current_password")} data-testid="change-password-current" /></div>
        <div className="space-y-1.5"><Label>New Password</Label><Input type="password" autoComplete="new-password" placeholder="Minimum 8 characters" value={f.new_password} onChange={set("new_password")} data-testid="change-password-new" /></div>
        <div className="space-y-1.5"><Label>Confirm New Password</Label><Input type="password" autoComplete="new-password" value={f.confirm} onChange={set("confirm")} data-testid="change-password-confirm" /></div>
        <Button className="bg-brand hover:bg-brand-hover" disabled={busy} data-testid="change-password-submit">
          {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Update Password
        </Button>
      </div>
    </form>
  );
}
