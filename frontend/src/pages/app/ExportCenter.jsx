import { useState } from "react";
import { toast } from "sonner";
import { Download, Users, IndianRupee, ClipboardCheck, Receipt, UserPlus, UserCog, Layers } from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { PageHeader } from "../../components/app/ui";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { Input } from "../../components/ui/input";
import { downloadExport } from "../../lib/files";
import { apiError } from "../../lib/api";

const DATED = ["payments", "expenses"];

const DATASETS = [
  { key: "members", label: "Members", desc: "Member profiles, plans, expiry and dues", icon: Users },
  { key: "payments", label: "Payments", desc: "All member payment transactions", icon: IndianRupee },
  { key: "attendance", label: "Attendance", desc: "Check-in and check-out records", icon: ClipboardCheck },
  { key: "expenses", label: "Expenses", desc: "Expense records by category", icon: Receipt },
  { key: "enquiries", label: "Enquiries", desc: "Lead details, sources and statuses", icon: UserPlus },
  { key: "staff", label: "Staff", desc: "Team members, roles and joining dates", icon: UserCog },
  { key: "plans", label: "Plans & Catalogue", desc: "Memberships, PT, services and products", icon: Layers },
];

export default function ExportCenter() {
  const { outlets } = useAuth();
  const [outletId, setOutletId] = useState("all");
  const [range, setRange] = useState({ from: "", to: "" });
  const [busy, setBusy] = useState(null);

  const download = async (dataset) => {
    setBusy(dataset);
    try {
      await downloadExport(dataset, {
        outlet_id: outletId !== "all" ? outletId : undefined,
        date_from: DATED.includes(dataset) ? range.from || undefined : undefined,
        date_to: DATED.includes(dataset) ? range.to || undefined : undefined,
      });
    } catch (e) { toast.error(apiError(e, "Export failed")); } finally { setBusy(null); }
  };

  return (
    <div data-testid="export-center-page">
      <PageHeader title="Export Center" subtitle="Download your gym data as CSV files. Payment and expense dates are transaction dates (IST)." testid="export-header">
        <Input type="date" value={range.from} onChange={(e) => setRange({ ...range, from: e.target.value })} className="h-9 w-40" aria-label="From date" data-testid="export-date-from" />
        <Input type="date" value={range.to} onChange={(e) => setRange({ ...range, to: e.target.value })} className="h-9 w-40" aria-label="To date" data-testid="export-date-to" />
        {outlets.length > 1 && (
          <Select value={outletId} onValueChange={setOutletId}>
            <SelectTrigger className="h-9 w-44" data-testid="export-outlet"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Outlets</SelectItem>
              {outlets.map((o) => <SelectItem key={o.id} value={o.id}>{o.name}</SelectItem>)}
            </SelectContent>
          </Select>
        )}
      </PageHeader>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" data-testid="export-grid">
        {DATASETS.map((d) => (
          <div key={d.key} className="rounded-xl border border-border bg-card p-5 shadow-card transition-all hover:border-brand/40" data-testid={`export-card-${d.key}`}>
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand/12 text-brand">
              <d.icon className="h-5 w-5" />
            </div>
            <p className="mt-3 font-display text-base font-bold text-foreground">{d.label}</p>
            <p className="mt-1 text-sm text-muted-foreground">{d.desc}</p>
            <button onClick={() => download(d.key)} disabled={busy === d.key} data-testid={`export-download-${d.key}`}
                    className="mt-4 inline-flex items-center gap-1.5 rounded-lg border border-border px-3.5 py-2 text-sm font-semibold text-foreground transition-colors hover:border-brand hover:text-brand">
              <Download className="h-4 w-4" />{busy === d.key ? "Preparing…" : "Download CSV"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
