import { Navigate, Link } from "react-router-dom";
import { LogOut, ArrowLeft, Lock } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { Logo } from "../components/Logo";
import Subscription from "./app/Subscription";

// Standalone billing portal (intended host: payments.gymboss.in). Same backend, login and entitlement as the app.
export default function BillingPortal() {
  const { status, user, organisation, logout } = useAuth();
  if (status === "loading") return null;
  if (status !== "authed") return <Navigate to="/login?next=/billing" replace />;
  if (user?.role === "super_admin") return <Navigate to="/superadmin" replace />;
  const appUrl = process.env.REACT_APP_APP_URL || "/app";
  const canManage = ["owner", "admin"].includes(user?.role);

  return (
    <div className="min-h-screen bg-background text-foreground" data-testid="billing-portal">
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-4">
          <div className="flex items-center gap-3">
            <Logo />
            <span className="hidden rounded-full bg-brand/10 px-2.5 py-1 text-xs font-bold text-brand sm:inline">Billing</span>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <span className="hidden text-muted-foreground md:inline" data-testid="portal-org-name">{organisation?.name}</span>
            <a href={appUrl} className="flex items-center gap-1 font-semibold text-brand hover:underline" data-testid="portal-back-to-app"><ArrowLeft className="h-4 w-4" />Open app</a>
            <button onClick={logout} className="flex items-center gap-1 text-muted-foreground hover:text-foreground" data-testid="portal-logout"><LogOut className="h-4 w-4" />Log out</button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-5 py-8">
        <h1 className="font-display text-3xl font-extrabold tracking-tight">Subscription & Billing</h1>
        <p className="mt-1 text-sm text-muted-foreground">Manage your GymBoss_VVO plan, payments and invoices for {organisation?.name}.</p>
        <div className="mt-6">
          {canManage ? <Subscription portal /> : (
            <div className="flex items-center gap-3 rounded-xl border border-border bg-card p-6 text-sm text-muted-foreground" data-testid="portal-no-permission">
              <Lock className="h-5 w-5 text-brand" />Only the gym owner or an admin can manage billing.
            </div>
          )}
        </div>
        <p className="mt-10 text-xs text-muted-foreground">
          BuildVVO Technologies Private Limited · <Link to="/terms" className="hover:underline">Terms</Link> · <Link to="/privacy" className="hover:underline">Privacy</Link>
        </p>
      </main>
    </div>
  );
}
