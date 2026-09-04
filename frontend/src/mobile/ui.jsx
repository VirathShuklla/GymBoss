import { Loader2, Sun, Moon } from "lucide-react";
import { cn } from "../lib/utils";
import { useTheme } from "../contexts/ThemeContext";
import { Drawer, DrawerContent } from "../components/ui/drawer";

export function MThemeToggle() {
  const { setTheme } = useTheme();
  const toggle = () => {
    const dark = document.documentElement.classList.contains("dark");
    setTheme(dark ? "light" : "dark");
  };
  return (
    <button onClick={toggle} data-testid="m-theme-toggle" aria-label="Toggle theme"
      className="flex h-10 w-10 items-center justify-center rounded-full bg-secondary text-foreground active:scale-95">
      <Sun className="h-5 w-5 dark:hidden" />
      <Moon className="hidden h-5 w-5 dark:block" />
    </button>
  );
}

export function MButton({ variant = "primary", loading, className, children, ...props }) {
  const styles = {
    primary: "bg-brand text-white hover:bg-brand-hover shadow-lg shadow-brand/25",
    outline: "border border-border bg-transparent text-foreground",
    soft: "bg-brand/10 text-brand",
    ghost: "text-muted-foreground",
  }[variant];
  return (
    <button
      {...props}
      disabled={props.disabled || loading}
      className={cn(
        "inline-flex h-[52px] w-full items-center justify-center gap-2 rounded-2xl text-[15px] font-semibold transition-all active:scale-[0.98] disabled:opacity-60",
        styles,
        className
      )}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}

export function Field({ label, children, hint }) {
  return (
    <label className="block">
      {label && <span className="mb-1.5 block text-xs font-semibold text-muted-foreground">{label}</span>}
      {children}
      {hint && <span className="mt-1 block text-[11px] text-muted-foreground">{hint}</span>}
    </label>
  );
}

export function BottomSheet({ open, onOpenChange, title, subtitle, children, testid }) {
  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent className="border-border bg-card px-5 pb-[calc(20px+env(safe-area-inset-bottom))]" data-testid={testid}>
        {(title || subtitle) && (
          <div className="pt-3">
            {title && <h3 className="font-display text-xl font-bold text-foreground">{title}</h3>}
            {subtitle && <p className="mt-0.5 text-sm text-muted-foreground">{subtitle}</p>}
          </div>
        )}
        <div className="mt-4 max-h-[68vh] space-y-4 overflow-y-auto pb-2">{children}</div>
      </DrawerContent>
    </Drawer>
  );
}

export function Seg({ tabs, value, onChange }) {
  return (
    <div className="no-scrollbar -mx-5 flex gap-2 overflow-x-auto px-5 py-1">
      {tabs.map((t) => (
        <button
          key={t.value}
          onClick={() => onChange(t.value)}
          data-testid={`m-seg-${t.value}`}
          className={cn(
            "shrink-0 rounded-full px-4 py-2 text-sm font-semibold transition-colors",
            value === t.value ? "bg-brand text-white" : "bg-secondary text-muted-foreground"
          )}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

export function Pills({ options, value, onChange, multi }) {
  const arr = Array.isArray(value) ? value : [value];
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((o) => {
        const v = typeof o === "string" ? o : o.value;
        const l = typeof o === "string" ? o : o.label;
        const active = arr.includes(v);
        return (
          <button
            key={v}
            type="button"
            onClick={() => onChange(v)}
            data-testid={`m-pill-${v}`}
            className={cn(
              "rounded-full px-3.5 py-2 text-sm font-medium transition-colors",
              active ? "bg-brand text-white" : "bg-secondary text-muted-foreground"
            )}
          >
            {l}
          </button>
        );
      })}
    </div>
  );
}

export function StatusChip({ status }) {
  const map = {
    active: "badge-active",
    expiring_soon: "badge-expiring",
    expired: "badge-expired",
    frozen: "badge-frozen",
    Paid: "badge-active",
    "Partially Paid": "badge-expiring",
    Due: "badge-expired",
  };
  const label = { active: "Active", expiring_soon: "Expiring", expired: "Expired", frozen: "Frozen" }[status] || status;
  return <span className={cn("badge-status", map[status] || "badge-frozen")}>{label}</span>;
}

export function ListSkeleton({ rows = 5 }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-[74px] animate-pulse rounded-2xl bg-secondary" />
      ))}
    </div>
  );
}

export function EmptyRow({ icon: Icon, title, subtitle, testid }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-border py-14 text-center" data-testid={testid}>
      {Icon && <Icon className="h-8 w-8 text-muted-foreground/40" />}
      <p className="mt-3 text-sm font-semibold text-foreground">{title}</p>
      {subtitle && <p className="mt-1 px-8 text-sm text-muted-foreground">{subtitle}</p>}
    </div>
  );
}

const inputCls = "h-12 w-full rounded-xl border border-input bg-background px-3.5 text-[15px] text-foreground outline-none placeholder:text-muted-foreground focus:border-brand";

export function TextInput({ className, ...props }) {
  return <input {...props} className={cn(inputCls, className)} />;
}

export function PhoneInput({ value, onChange, ...props }) {
  return (
    <div className="flex items-center gap-2">
      <span className="flex h-12 items-center rounded-xl border border-input bg-secondary px-3 text-[15px] font-medium text-foreground">🇮🇳 +91</span>
      <input
        {...props}
        inputMode="numeric"
        value={value}
        onChange={onChange}
        placeholder="Mobile number"
        className={cn(inputCls, "flex-1")}
      />
    </div>
  );
}

export function SectionTitle({ children, action }) {
  return (
    <div className="mb-3 mt-6 flex items-center justify-between">
      <h2 className="font-display text-sm font-bold uppercase tracking-wider text-muted-foreground">{children}</h2>
      {action}
    </div>
  );
}
