import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "../../contexts/AuthContext";
import { apiError } from "../../lib/api";
import { AuthShell } from "../../components/AuthShell";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";

export default function Login() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ identifier: "", password: "" });
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (user) {
    return <Navigate to={user.role === "super_admin" ? "/superadmin" : "/app"} replace />;
  }

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const logged = await login(form.identifier, form.password);
      toast.success("Welcome back!");
      navigate("/app", { replace: true });
    } catch (err) {
      setError(apiError(err, "Unable to log in."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Welcome back" subtitle="Log in to your GymBoss_VVO account">
      <form onSubmit={submit} className="space-y-4" data-testid="login-form">
        {error && (
          <div className="rounded-lg border border-danger/25 bg-danger/10 px-3.5 py-2.5 text-sm text-danger" data-testid="login-error">
            {error}
          </div>
        )}
        <div className="space-y-1.5">
          <Label htmlFor="identifier">Email or Mobile</Label>
          <Input id="identifier" data-testid="login-identifier" placeholder="you@gym.com or 98765 43210"
                 value={form.identifier} onChange={(e) => setForm({ ...form, identifier: e.target.value })} required autoComplete="username" />
        </div>
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <Label htmlFor="password">Password</Label>
            <Link to="/forgot-password" className="text-xs font-medium text-brand hover:underline" data-testid="forgot-password-link">
              Forgot Password?
            </Link>
          </div>
          <div className="relative">
            <Input id="password" type={show ? "text" : "password"} data-testid="login-password" placeholder="Enter your password"
                   value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required autoComplete="current-password" className="pr-10" />
            <button type="button" onClick={() => setShow(!show)} data-testid="login-password-toggle"
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600" aria-label="Toggle password visibility">
              {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </div>
        <Button type="submit" className="w-full rounded-lg bg-brand font-semibold hover:bg-brand-hover" disabled={busy} data-testid="login-submit-button">
          {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Login
        </Button>
        <p className="pt-1 text-center text-sm text-slate-500 dark:text-muted-foreground">
          Don't have an account?{" "}
          <Link to="/register" className="font-semibold text-brand hover:underline" data-testid="login-start-trial-link">
            Start Free Trial
          </Link>
        </p>
      </form>
    </AuthShell>
  );
}
