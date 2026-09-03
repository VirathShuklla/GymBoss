import { Link } from "react-router-dom";
import { ShieldCheck, LogOut } from "lucide-react";
import { Logo } from "../components/Logo";
import { useAuth } from "../contexts/AuthContext";

export default function SuperAdmin() {
  const { user, logout } = useAuth();
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 text-center" data-testid="superadmin-page">
      <Logo />
      <div className="mt-8 max-w-md rounded-2xl border border-border bg-card p-8 shadow-card">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-brand/12 text-brand">
          <ShieldCheck className="h-6 w-6" />
        </div>
        <h1 className="mt-5 font-display text-2xl font-bold text-foreground">BuildVVO Super Admin</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Signed in as <span className="font-semibold text-foreground">{user?.full_name}</span>. The super admin console — gym registrations, MRR, trial conversion and account controls — ships in Milestone 5.
        </p>
        <Link to="/login" onClick={logout} data-testid="superadmin-logout"
              className="mt-6 inline-flex items-center gap-2 rounded-lg border border-border px-5 py-2.5 text-sm font-semibold text-foreground hover:bg-secondary">
          <LogOut className="h-4 w-4" /> Logout
        </Link>
      </div>
    </div>
  );
}
