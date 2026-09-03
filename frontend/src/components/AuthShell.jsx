import { Link } from "react-router-dom";
import { Logo } from "../components/Logo";
import { ThemeToggle } from "../components/ThemeToggle";

export function AuthShell({ title, subtitle, children, wide = false }) {
  return (
    <div className="flex min-h-screen flex-col items-center bg-slate-50 px-4 py-10 dark:bg-background" data-testid="auth-shell">
      <div className="flex flex-col items-center">
        <Link to="/"><Logo /></Link>
        <h1 className="mt-5 font-display text-xl font-bold text-slate-900 dark:text-foreground">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500 dark:text-muted-foreground">{subtitle}</p>}
      </div>
      <div className={`mt-8 w-full ${wide ? "max-w-md" : "max-w-sm"} rounded-2xl border border-slate-200 bg-white p-7 shadow-card dark:border-border dark:bg-card`}>
        {children}
      </div>
      <div className="mt-6 flex items-center gap-2">
        <ThemeToggle testid="auth-theme-toggle" />
        <Link to="/" className="text-xs font-medium text-slate-500 transition-colors hover:text-slate-800 dark:text-muted-foreground dark:hover:text-foreground" data-testid="auth-back-home">
          Back to website
        </Link>
      </div>
    </div>
  );
}
