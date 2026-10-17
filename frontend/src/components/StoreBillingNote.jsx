import { Info } from "lucide-react";

export function StoreBillingNote({ className = "" }) {
  return (
    <div className={`rounded-2xl border border-border bg-secondary/40 p-4 text-xs text-muted-foreground ${className}`} data-testid="in-app-billing-note">
      <p className="flex items-center gap-1.5 font-medium text-foreground"><Info className="h-3.5 w-3.5 shrink-0" />Plans can't be purchased inside the app.</p>
      <p className="mt-1">Your subscription is managed from your GymBoss_VVO account on our website. Everything you do here stays in sync.</p>
    </div>
  );
}
