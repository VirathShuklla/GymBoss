import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "../../contexts/AuthContext";
import { apiError } from "../../lib/api";
import { MButton, Field, TextInput, PhoneInput } from "../ui";

export default function Register() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [f, setF] = useState({ gym_name: "", outlet_name: "", full_name: "", email: "", phone: "", password: "" });
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const steps = [
    { title: "Gym Info", sub: "Tell us about your gym." },
    { title: "About You", sub: "The owner's details." },
    { title: "Almost done", sub: "Set up your login." },
  ];

  const canNext =
    (step === 0 && f.gym_name.trim().length >= 2 && f.outlet_name.trim().length >= 2) ||
    (step === 1 && f.full_name.trim().length >= 2 && /\S+@\S+\.\S+/.test(f.email)) ||
    (step === 2 && f.phone.replace(/\D/g, "").length === 10 && f.password.length >= 8);

  const submit = async () => {
    setBusy(true);
    try {
      await register({
        full_name: f.full_name.trim(),
        email: f.email.trim().toLowerCase(),
        phone: f.phone.replace(/\D/g, ""),
        password: f.password,
        gym_name: f.gym_name.trim(),
        outlet_name: f.outlet_name.trim(),
        city: f.outlet_name.trim(),
      });
      toast.success("Gym created! Your 10-day free trial has started.");
      navigate("/m/home", { replace: true });
    } catch (err) {
      toast.error(apiError(err, "Could not create your account"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-background px-6 pb-[calc(28px+env(safe-area-inset-bottom))] pt-[calc(24px+env(safe-area-inset-top))]" data-testid="m-register">
      <button onClick={() => (step === 0 ? navigate("/m/welcome") : setStep(step - 1))} className="flex h-10 w-10 items-center justify-center rounded-full bg-secondary text-foreground">
        <ArrowLeft className="h-5 w-5" />
      </button>

      <div className="mt-6 flex gap-2">
        {steps.map((_, i) => (
          <span key={i} className={`h-1.5 flex-1 rounded-full transition-colors ${i <= step ? "bg-brand" : "bg-border"}`} />
        ))}
      </div>

      <div className="mt-7">
        <h1 className="font-display text-3xl font-extrabold tracking-tight text-foreground">{steps[step].title}</h1>
        <p className="mt-2 text-[15px] text-muted-foreground">{steps[step].sub}</p>
      </div>

      <div key={step} className="m-anim mt-7 flex-1 space-y-5">
        {step === 0 && (
          <>
            <Field label="Gym name">
              <TextInput data-testid="m-reg-gym" value={f.gym_name} onChange={set("gym_name")} placeholder="Iron Paradise Fitness" />
            </Field>
            <Field label="Outlet location (Area / City)">
              <TextInput data-testid="m-reg-outlet" value={f.outlet_name} onChange={set("outlet_name")} placeholder="Koramangala, Bengaluru" />
            </Field>
          </>
        )}
        {step === 1 && (
          <>
            <Field label="Your name">
              <TextInput data-testid="m-reg-name" value={f.full_name} onChange={set("full_name")} placeholder="Full name" />
            </Field>
            <Field label="Email">
              <TextInput data-testid="m-reg-email" type="email" autoCapitalize="none" value={f.email} onChange={set("email")} placeholder="you@gym.com" />
            </Field>
          </>
        )}
        {step === 2 && (
          <>
            <Field label="Mobile number">
              <PhoneInput data-testid="m-reg-phone" value={f.phone} onChange={set("phone")} />
            </Field>
            <Field label="Password" hint="At least 8 characters.">
              <TextInput data-testid="m-reg-password" type="password" value={f.password} onChange={set("password")} placeholder="Create a password" />
            </Field>
          </>
        )}
      </div>

      <MButton
        className="mt-4"
        disabled={!canNext}
        loading={busy}
        data-testid="m-reg-next"
        onClick={() => (step < 2 ? setStep(step + 1) : submit())}
      >
        {step < 2 ? "Continue" : "Create my gym"}
      </MButton>
      <p className="mt-5 text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link to="/m/login" className="font-semibold text-brand">Log in</Link>
      </p>
    </div>
  );
}
