import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { Eye, EyeOff, Loader2, Check } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "../../contexts/AuthContext";
import { apiError } from "../../lib/api";
import { AuthShell } from "../../components/AuthShell";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function Stepper({ step }) {
  return (
    <div className="mb-8 flex items-center justify-center" data-testid="signup-stepper">
      {[1, 2, 3].map((n, i) => (
        <div key={n} className="flex items-center">
          <div
            data-testid={`stepper-step-${n}`}
            className={`flex h-9 w-9 items-center justify-center rounded-full font-num text-sm font-bold transition-colors ${
              n < step
                ? "bg-success text-white"
                : n === step
                  ? "bg-brand text-white"
                  : "bg-slate-200 text-slate-500 dark:bg-secondary dark:text-muted-foreground"
            }`}
          >
            {n < step ? <Check className="h-4 w-4" strokeWidth={3} /> : n}
          </div>
          {i < 2 && <div className={`mx-2 h-0.5 w-12 sm:w-16 ${n < step ? "bg-success" : "bg-slate-200 dark:bg-secondary"}`} />}
        </div>
      ))}
    </div>
  );
}

export default function Register() {
  const { register, user } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [busy, setBusy] = useState(false);
  const [showPw, setShowPw] = useState(false);
  const [errors, setErrors] = useState({});
  const [form, setForm] = useState({
    full_name: "", email: "", phone: "", password: "", confirm: "",
    gym_name: "", outlet_name: "", city: "",
  });

  if (user) {
    return <Navigate to="/app" replace />;
  }

  const set = (k) => (e) => {
    setForm({ ...form, [k]: e.target.value });
    setErrors((prev) => ({ ...prev, [k]: undefined }));
  };

  const next = () => {
    const errs = {};
    if (step === 1) {
      if (form.full_name.trim().length < 2) errs.full_name = "Enter your full name";
      if (!EMAIL_RE.test(form.email.trim())) errs.email = "Enter a valid email address";
    }
    if (step === 2) {
      if (!/^\d{10}$/.test(form.phone.replace(/\D/g, "").slice(-10))) errs.phone = "Enter a valid 10-digit mobile number";
      if (form.password.length < 8) errs.password = "Password must be at least 8 characters";
      if (form.confirm !== form.password) errs.confirm = "Passwords do not match";
    }
    setErrors(errs);
    if (Object.keys(errs).length === 0) setStep(step + 1);
  };

  const submit = async () => {
    const errs = {};
    if (form.gym_name.trim().length < 2) errs.gym_name = "Enter your gym name";
    if (form.outlet_name.trim().length < 2) errs.outlet_name = "Enter your outlet name";
    setErrors(errs);
    if (Object.keys(errs).length) return;
    setBusy(true);
    try {
      await register({
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        phone: form.phone,
        password: form.password,
        gym_name: form.gym_name.trim(),
        outlet_name: form.outlet_name.trim(),
        city: form.city.trim() || undefined,
      });
      toast.success("Your 10-day free trial has started. Welcome to GymBoss_VVO!");
      navigate("/app", { replace: true });
    } catch (err) {
      toast.error(apiError(err, "Could not create your account."));
      setStep(1);
    } finally {
      setBusy(false);
    }
  };

  const fieldError = (k) =>
    errors[k] ? <p className="text-xs text-danger" data-testid={`error-${k}`}>{errors[k]}</p> : null;

  return (
    <AuthShell title="Create Your Account" subtitle="Start your 10-day free trial — no credit card required" wide>
      <Stepper step={step} />
      <div data-testid={`register-step-${step}`}>
        {step === 1 && (
          <div className="space-y-4">
            <h2 className="font-display text-base font-bold text-slate-900 dark:text-foreground">Account Information</h2>
            <div className="space-y-1.5">
              <Label htmlFor="full_name">Full Name</Label>
              <Input id="full_name" data-testid="register-full-name" placeholder="Enter your full name" value={form.full_name} onChange={set("full_name")} />
              {fieldError("full_name")}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" data-testid="register-email" placeholder="Enter your email" value={form.email} onChange={set("email")} />
              {fieldError("email")}
            </div>
            <Button className="w-full rounded-lg bg-brand font-semibold hover:bg-brand-hover" onClick={next} data-testid="register-next-1">Next</Button>
          </div>
        )}
        {step === 2 && (
          <div className="space-y-4">
            <h2 className="font-display text-base font-bold text-slate-900 dark:text-foreground">Contact & Security</h2>
            <div className="space-y-1.5">
              <Label htmlFor="phone">Phone Number</Label>
              <div className="flex">
                <span className="inline-flex items-center rounded-l-lg border border-r-0 border-input bg-slate-50 px-3 text-sm font-medium text-slate-600 dark:bg-secondary dark:text-muted-foreground">+91</span>
                <Input id="phone" inputMode="numeric" data-testid="register-phone" placeholder="98765 43210" className="rounded-l-none"
                       value={form.phone} onChange={set("phone")} />
              </div>
              {fieldError("phone")}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input id="password" type={showPw ? "text" : "password"} data-testid="register-password" placeholder="Minimum 8 characters"
                       value={form.password} onChange={set("password")} className="pr-10" />
                <button type="button" onClick={() => setShowPw(!showPw)} data-testid="register-password-toggle"
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600" aria-label="Toggle password visibility">
                  {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {fieldError("password")}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="confirm">Confirm Password</Label>
              <Input id="confirm" type="password" data-testid="register-confirm-password" placeholder="Re-enter your password"
                     value={form.confirm} onChange={set("confirm")} />
              {fieldError("confirm")}
            </div>
            <div className="flex gap-3">
              <Button variant="outline" className="flex-1 rounded-lg" onClick={() => setStep(1)} data-testid="register-prev-2">Previous</Button>
              <Button className="flex-1 rounded-lg bg-brand font-semibold hover:bg-brand-hover" onClick={next} data-testid="register-next-2">Next</Button>
            </div>
          </div>
        )}
        {step === 3 && (
          <div className="space-y-4">
            <h2 className="font-display text-base font-bold text-slate-900 dark:text-foreground">Gym Setup</h2>
            <div className="space-y-1.5">
              <Label htmlFor="gym_name">Gym Name</Label>
              <Input id="gym_name" data-testid="register-gym-name" placeholder="Enter your gym name" value={form.gym_name} onChange={set("gym_name")} />
              {fieldError("gym_name")}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="outlet_name">Outlet Name</Label>
              <Input id="outlet_name" data-testid="register-outlet-name" placeholder="e.g., Main Branch" value={form.outlet_name} onChange={set("outlet_name")} />
              {fieldError("outlet_name")}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="city">City <span className="font-normal text-slate-400">(optional)</span></Label>
              <Input id="city" data-testid="register-city" placeholder="e.g., Bengaluru" value={form.city} onChange={set("city")} />
            </div>
            <div className="flex gap-3">
              <Button variant="outline" className="flex-1 rounded-lg" onClick={() => setStep(2)} disabled={busy} data-testid="register-prev-3">Previous</Button>
              <Button className="flex-1 rounded-lg bg-success font-semibold text-white hover:bg-success/90" onClick={submit} disabled={busy} data-testid="register-finish-button">
                {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Start Free Trial
              </Button>
            </div>
          </div>
        )}
      </div>
      <p className="mt-6 text-center text-sm text-slate-500 dark:text-muted-foreground">
        Already have an account?{" "}
        <Link to="/login" className="font-semibold text-brand hover:underline" data-testid="register-login-link">Login</Link>
      </p>
    </AuthShell>
  );
}
