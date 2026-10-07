import { Check } from "lucide-react";
import { inr } from "../lib/format";

const per = (m) => (m === 1 ? "month" : m === 12 ? "year" : `${m} months`);

// Selectable SaaS plan cards (prices + offers are managed by the Super Admin).
export function PlanPicker({ plans, value, onChange, testid = "plan-picker" }) {
  return (
    <div className="grid gap-2.5" data-testid={testid}>
      {(plans || []).map((p) => {
        const on = value === p.id;
        return (
          <button type="button" key={p.id} onClick={() => onChange(p.id)} data-testid={`${testid}-${p.id}`}
            className={`flex items-center gap-3 rounded-2xl border-2 px-4 py-3 text-left transition-colors ${on ? "border-brand bg-brand/5" : "border-border bg-card"}`}>
            <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 ${on ? "border-brand bg-brand text-white" : "border-muted-foreground/40"}`}>
              {on && <Check className="h-3 w-3" strokeWidth={3.5} />}
            </span>
            <span className="min-w-0 flex-1">
              <span className="flex flex-wrap items-center gap-1.5 text-sm font-bold text-foreground">
                {p.name}
                {p.offer_label && <span className="rounded-full bg-success/15 px-2 py-0.5 text-[10px] font-bold uppercase text-success">{p.offer_label}</span>}
                {!p.offer_label && p.save_pct > 0 && <span className="rounded-full bg-success/15 px-2 py-0.5 text-[10px] font-bold text-success">Save {p.save_pct}%</span>}
              </span>
              {p.months > 1 && <span className="block text-xs text-muted-foreground">{inr(p.per_month)}/month, billed every {per(p.months)}</span>}
            </span>
            <span className="text-right">
              {p.offer_price && <span className="font-num block text-xs text-muted-foreground line-through">{inr(p.price)}</span>}
              <span className="font-num block text-base font-extrabold text-foreground">{inr(p.effective_price)}<span className="text-xs font-medium text-muted-foreground">/{per(p.months)}</span></span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

export const planPeriod = per;
