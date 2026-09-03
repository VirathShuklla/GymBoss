import { useEffect, useState } from "react";
import { TrendingUp, TrendingDown, Wallet, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import api from "../../lib/api";
import { inr, formatDate } from "../../lib/format";
import { useAuth } from "../../contexts/AuthContext";
import { PageHeader, DataTable, StatusBadge, EmptyState, DateField } from "../../components/app/ui";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { Input } from "../../components/ui/input";

const RANGES = [
  { value: "today", label: "Today" },
  { value: "week", label: "This Week" },
  { value: "month", label: "This Month" },
  { value: "year", label: "This Year" },
  { value: "custom", label: "Custom Range" },
];

export default function Finance() {
  const { outlets } = useAuth();
  const [range, setRange] = useState("month");
  const [custom, setCustom] = useState({ from: "", to: "" });
  const [outletId, setOutletId] = useState("all");
  const [summary, setSummary] = useState(null);
  const [transactions, setTransactions] = useState(null);

  useEffect(() => {
    const params = {
      range,
      outlet_id: outletId === "all" ? undefined : outletId,
      date_from: range === "custom" ? custom.from || undefined : undefined,
      date_to: range === "custom" ? custom.to || undefined : undefined,
    };
    api.get("/finance/summary", { params }).then(({ data }) => setSummary(data)).catch(() => toast.error("Couldn't load finance summary"));
    api.get("/finance/transactions", { params }).then(({ data }) => setTransactions(data));
  }, [range, custom.from, custom.to, outletId]);

  const cards = [
    { key: "revenue", label: "Revenue", icon: TrendingUp, color: "text-success", tile: "bg-success/12" },
    { key: "expenses", label: "Expenses", icon: TrendingDown, color: "text-danger", tile: "bg-danger/12" },
    { key: "net", label: "Net Cash Flow", icon: Wallet, color: "text-brand", tile: "bg-brand/12" },
    { key: "outstanding", label: "Outstanding Dues", icon: AlertCircle, color: "text-warning", tile: "bg-warning/12" },
  ];

  const columns = [
    { key: "created_at", label: "Date", render: (t) => formatDate(t.created_at) },
    { key: "member_name", label: "Member", render: (t) => <span className="font-medium text-foreground">{t.member_name}</span> },
    { key: "type", label: "Type", render: (t) => <StatusBadge status={t.type} /> },
    { key: "plan_name", label: "Description", render: (t) => t.plan_name || "—" },
    { key: "method", label: "Method" },
    { key: "amount", label: "Amount", align: "right", render: (t) => <span className="font-num font-bold text-success">{inr(t.amount)}</span> },
  ];

  return (
    <div data-testid="finance-page">
      <PageHeader title="Finance" subtitle="Revenue, expenses and cash flow." testid="finance-header" />
      <div className="mb-5 flex flex-wrap items-center gap-2.5">
        <Select value={range} onValueChange={setRange}>
          <SelectTrigger className="h-9 w-40" data-testid="finance-range"><SelectValue /></SelectTrigger>
          <SelectContent>{RANGES.map((r) => <SelectItem key={r.value} value={r.value}>{r.label}</SelectItem>)}</SelectContent>
        </Select>
        {range === "custom" && (
          <>
            <div className="w-44"><DateField value={custom.from} onChange={(v) => setCustom({ ...custom, from: v })} testid="finance-from" placeholder="From" /></div>
            <div className="w-44"><DateField value={custom.to} onChange={(v) => setCustom({ ...custom, to: v })} testid="finance-to" placeholder="To" /></div>
          </>
        )}
        {outlets.length > 1 && (
          <Select value={outletId} onValueChange={setOutletId}>
            <SelectTrigger className="h-9 w-40" data-testid="finance-outlet"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Outlets</SelectItem>
              {outlets.map((o) => <SelectItem key={o.id} value={o.id}>{o.name}</SelectItem>)}
            </SelectContent>
          </Select>
        )}
      </div>

      {summary && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4" data-testid="finance-kpis">
            {cards.map((c) => (
              <div key={c.key} className="rounded-xl border border-border bg-card p-4 shadow-card" data-testid={`finance-${c.key}`}>
                <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${c.tile}`}>
                  <c.icon className={`h-[18px] w-[18px] ${c.color}`} />
                </div>
                <p className="mt-3 text-xs font-medium text-muted-foreground">{c.label}</p>
                <p className={`font-num mt-1 text-xl font-bold ${c.color}`}>{inr(summary[c.key])}</p>
                {c.key === "outstanding" && <p className="mt-1 text-[11px] text-muted-foreground">{summary.due_member_count} members pending</p>}
              </div>
            ))}
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <div className="rounded-xl border border-border bg-card p-5 shadow-card" data-testid="finance-by-method">
              <p className="mb-3 font-display text-sm font-bold text-foreground">Collections by Method</p>
              {Object.keys(summary.by_method).length === 0 ? (
                <p className="text-sm text-muted-foreground">No collections in this period.</p>
              ) : (
                <div className="space-y-2">
                  {Object.entries(summary.by_method).map(([m, v]) => (
                    <div key={m} className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">{m}</span>
                      <span className="font-num font-semibold text-foreground">{inr(v)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="rounded-xl border border-border bg-card p-5 shadow-card" data-testid="finance-expense-categories">
              <p className="mb-3 font-display text-sm font-bold text-foreground">Expenses by Category</p>
              {Object.keys(summary.expense_by_category).length === 0 ? (
                <p className="text-sm text-muted-foreground">No expenses in this period.</p>
              ) : (
                <div className="space-y-2">
                  {Object.entries(summary.expense_by_category).map(([c, v]) => (
                    <div key={c} className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">{c}</span>
                      <span className="font-num font-semibold text-danger">{inr(v)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}

      <h2 className="mb-3 mt-7 font-display text-sm font-bold uppercase tracking-wider text-muted-foreground">Transactions</h2>
      <DataTable testid="finance-transactions-table" columns={columns} rows={transactions || []} loading={!transactions}
                 empty={<EmptyState icon={Wallet} title="No transactions in this period" testid="finance-transactions-empty" />} />
    </div>
  );
}
