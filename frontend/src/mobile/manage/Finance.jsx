// Mobile Finance screen: revenue / expenses / net / outstanding for a chosen date range,
// a collections-by-method breakdown, and the period's transactions. Reads the same
// /finance/* endpoints as the web app (finance-access gated on the server).
import { useEffect, useState } from "react";
import { IndianRupee, TrendingUp, TrendingDown, Wallet } from "lucide-react";
import api from "../../lib/api";
import { inr, formatDate } from "../../lib/format";
import { Seg, ListSkeleton, EmptyRow } from "../ui";

const RANGES = [
  { value: "today", label: "Today" },
  { value: "week", label: "This Week" },
  { value: "month", label: "This Month" },
  { value: "year", label: "This Year" },
];

export default function Finance() {
  const [range, setRange] = useState("month");
  const [sum, setSum] = useState(null);
  const [txns, setTxns] = useState(null);

  useEffect(() => {
    setSum(null);
    setTxns(null);
    api.get(`/finance/summary?range=${range}`).then(({ data }) => setSum(data)).catch(() => setSum({}));
    api.get(`/finance/transactions?range=${range}`).then(({ data }) => setTxns(data)).catch(() => setTxns([]));
  }, [range]);

  const cards = sum ? [
    { label: "Revenue", value: inr(sum.revenue), cls: "text-success", Icon: TrendingUp },
    { label: "Expenses", value: inr(sum.expenses), cls: "text-danger", Icon: TrendingDown },
    { label: "Net", value: inr(sum.net), cls: "text-brand", Icon: IndianRupee },
    { label: "Outstanding", value: inr(sum.outstanding), cls: "text-warning", Icon: Wallet },
  ] : [];

  return (
    <div data-testid="m-finance">
      <Seg tabs={RANGES} value={range} onChange={setRange} />

      <div className="mt-4 grid grid-cols-2 gap-3">
        {!sum
          ? Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-24 animate-pulse rounded-2xl bg-secondary" />)
          : cards.map((c) => (
            <div key={c.label} className="rounded-2xl border border-border bg-card p-4" data-testid={`m-finance-${c.label.toLowerCase()}`}>
              <div className="flex items-center justify-between">
                <p className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">{c.label}</p>
                <c.Icon className={`h-4 w-4 ${c.cls}`} />
              </div>
              <p className={`font-num mt-1 text-xl font-extrabold ${c.cls}`}>{c.value}</p>
            </div>
          ))}
      </div>

      {sum && Object.keys(sum.by_method || {}).length > 0 && (
        <div className="mt-4 rounded-2xl border border-border bg-card p-4" data-testid="m-finance-by-method">
          <p className="mb-2 text-xs font-bold uppercase tracking-wide text-muted-foreground">Collections by Method</p>
          {Object.entries(sum.by_method).map(([k, v]) => (
            <div key={k} className="flex items-center justify-between py-1.5 text-sm">
              <span className="text-foreground">{k}</span>
              <span className="font-num font-bold text-foreground">{inr(v)}</span>
            </div>
          ))}
        </div>
      )}

      <h2 className="mb-3 mt-6 font-display text-sm font-bold uppercase tracking-wider text-muted-foreground">Transactions</h2>
      {!txns ? (
        <ListSkeleton rows={4} />
      ) : txns.length === 0 ? (
        <EmptyRow icon={IndianRupee} title="No transactions" subtitle="No payments in this period." testid="m-finance-empty" />
      ) : (
        <div className="space-y-2.5" data-testid="m-finance-txns">
          {txns.map((t) => (
            <div key={t.id} className="flex items-center justify-between rounded-2xl border border-border bg-card px-4 py-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-foreground">{t.member_name}</p>
                <p className="text-xs text-muted-foreground">{formatDate(t.created_at)} · {t.method}</p>
              </div>
              <p className="font-num text-sm font-bold text-success">{inr(t.amount)}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
