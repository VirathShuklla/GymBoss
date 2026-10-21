import { Info } from "lucide-react";

// Shown in store builds instead of any purchase UI. No prices, links or "pay elsewhere" instructions (Play §4 / Apple 3.1.1).
export function StoreBillingNote({ className = "" }) {
  return (
    <div className={`rounded-2xl border border-border bg-secondary/40 p-4 text-xs text-muted-foreground ${className}`} data-testid="in-app-billing-note">
      <p className="flex items-center gap-1.5 font-medium text-foreground"><Info className="h-3.5 w-3.5 shrink-0" />Subscriptions aren't available for purchase in this app.</p>
      <p className="mt-1">If your organisation already has a GymBoss_VVO subscription, it's active here automatically. For billing questions, contact your account administrator.</p>
    </div>
  );
}
