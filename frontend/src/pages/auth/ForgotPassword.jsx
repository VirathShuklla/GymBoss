import { useState } from "react";
import { Link } from "react-router-dom";
import { Loader2, MailCheck } from "lucide-react";
import api, { apiError } from "../../lib/api";
import { AuthShell } from "../../components/AuthShell";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.post("/auth/forgot-password", { email });
      setDone(true);
    } catch (err) {
      setError(apiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Reset your password" subtitle="We'll email you a secure reset link">
      {done ? (
        <div className="text-center" data-testid="forgot-success">
          <MailCheck className="mx-auto h-10 w-10 text-success" />
          <p className="mt-4 text-sm text-slate-600 dark:text-muted-foreground">
            If that email is registered, a reset link has been sent. The link expires in 1 hour and can be used once.
          </p>
          <Link to="/login" className="mt-5 inline-block text-sm font-semibold text-brand hover:underline" data-testid="forgot-back-login">
            Back to Login
          </Link>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4" data-testid="forgot-form">
          {error && <div className="rounded-lg border border-danger/25 bg-danger/10 px-3.5 py-2.5 text-sm text-danger" data-testid="forgot-error">{error}</div>}
          <div className="space-y-1.5">
            <Label htmlFor="forgot-email">Email</Label>
            <Input id="forgot-email" type="email" data-testid="forgot-email" placeholder="you@gym.com"
                   value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <Button type="submit" className="w-full rounded-lg bg-brand font-semibold hover:bg-brand-hover" disabled={busy} data-testid="forgot-submit-button">
            {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Send Reset Link
          </Button>
          <p className="text-center text-sm">
            <Link to="/login" className="font-medium text-brand hover:underline" data-testid="forgot-login-link">Back to sign in</Link>
          </p>
        </form>
      )}
    </AuthShell>
  );
}
