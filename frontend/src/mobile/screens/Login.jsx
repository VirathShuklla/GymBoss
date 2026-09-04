import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { ArrowLeft, Lock, Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "../../contexts/AuthContext";
import { apiError } from "../../lib/api";
import { MButton, Field, TextInput } from "../ui";

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await login(identifier.trim(), password);
      toast.success("Welcome back!");
      navigate("/m/home", { replace: true });
    } catch (err) {
      toast.error(apiError(err, "Invalid credentials"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-background px-6 pb-[calc(28px+env(safe-area-inset-bottom))] pt-[calc(24px+env(safe-area-inset-top))]" data-testid="m-login">
      <button onClick={() => navigate("/m/welcome")} className="flex h-10 w-10 items-center justify-center rounded-full bg-secondary text-foreground">
        <ArrowLeft className="h-5 w-5" />
      </button>
      <div className="mt-8">
        <h1 className="font-display text-3xl font-extrabold tracking-tight text-foreground">Welcome back</h1>
        <p className="mt-2 text-[15px] text-muted-foreground">Log in to manage your gym.</p>
      </div>
      <form onSubmit={submit} className="mt-8 space-y-5">
        <Field label="Mobile number or email">
          <TextInput data-testid="m-login-identifier" value={identifier} onChange={(e) => setIdentifier(e.target.value)} placeholder="you@gym.com or 98765 43210" autoCapitalize="none" />
        </Field>
        <Field label="Password">
          <div className="relative">
            <Lock className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <TextInput data-testid="m-login-password" type={show ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Enter your password" className="px-10" />
            <button type="button" onClick={() => setShow(!show)} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted-foreground">
              {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </Field>
        <MButton type="submit" loading={busy} data-testid="m-login-submit">Proceed</MButton>
      </form>
      <p className="mt-8 text-center text-sm text-muted-foreground">
        New to GymBoss_VVO?{" "}
        <Link to="/m/register" className="font-semibold text-brand" data-testid="m-login-register-link">Create an account</Link>
      </p>
    </div>
  );
}
