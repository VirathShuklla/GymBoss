import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { AuthShell } from "../../components/AuthShell";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get("token") || "";
  const [form, setForm] = useState({ password: "", confirm: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (form.password.length < 8) return setError("Password must be at least 8 characters");
    if (form.password !== form.confirm) return setError("Passwords do not match");
    setBusy(true);
    try {
      await api.post("/auth/reset-password", { token, password: form.password });
      toast.success("Password updated. Please log in.");
      navigate("/login", { replace: true });
    } catch (err) {
      setError(apiError(err, "This reset link is invalid or has expired."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Choose a new password" subtitle="Your new password must be at least 8 characters">
      {!token ? (
        <div className="text-center" data-testid="reset-missing-token">
          <p className="text-sm text-slate-600 dark:text-muted-foreground">This reset link is invalid or has expired.</p>
          <Link to="/forgot-password" className="mt-4 inline-block text-sm font-semibold text-brand hover:underline">Request a new link</Link>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4" data-testid="reset-form">
          {error && <div className="rounded-lg border border-danger/25 bg-danger/10 px-3.5 py-2.5 text-sm text-danger" data-testid="reset-error">{error}</div>}
          <div className="space-y-1.5">
            <Label htmlFor="new-password">New Password</Label>
            <Input id="new-password" type="password" data-testid="reset-password" placeholder="Minimum 8 characters"
                   value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="confirm-password">Confirm Password</Label>
            <Input id="confirm-password" type="password" data-testid="reset-confirm" placeholder="Re-enter password"
                   value={form.confirm} onChange={(e) => setForm({ ...form, confirm: e.target.value })} required />
          </div>
          <Button type="submit" className="w-full rounded-lg bg-brand font-semibold hover:bg-brand-hover" disabled={busy} data-testid="reset-submit-button">
            {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Update Password
          </Button>
          <p className="text-center text-sm">
            <Link to="/login" className="font-medium text-brand hover:underline">Back to sign in</Link>
          </p>
        </form>
      )}
    </AuthShell>
  );
}
