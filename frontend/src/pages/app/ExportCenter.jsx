import { useState } from "react";
import { Download, Users, IndianRupee, ClipboardCheck, Receipt, UserPlus, UserCog, Layers } from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { PageHeader } from "../../components/app/ui";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";

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

  const download = (dataset) => {
    const base = process.env.REACT_APP_BACKEND_URL;
    const params = outletId !== "all" ? `?outlet_id=${outletId}` : "";
    window.open(`${base}/api/export/${dataset}${params}`, "_blank");
  };

  return (
    <div data-testid="export-center-page">
      <PageHeader title="Export Center" subtitle="Download your gym data as CSV files." testid="export-header">
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
            <button onClick={() => download(d.key)} data-testid={`export-download-${d.key}`}
                    className="mt-4 inline-flex items-center gap-1.5 rounded-lg border border-border px-3.5 py-2 text-sm font-semibold text-foreground transition-colors hover:border-brand hover:text-brand">
              <Download className="h-4 w-4" />Download CSV
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
