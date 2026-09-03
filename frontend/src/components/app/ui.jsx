import { useState } from "react";
import { format } from "date-fns";
import { Search, Inbox, Loader2, CalendarIcon } from "lucide-react";
import { Skeleton } from "../ui/skeleton";
import { Input } from "../ui/input";
import { Calendar } from "../ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "../ui/popover";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "../ui/alert-dialog";
import api from "../../lib/api";

export function PageHeader({ title, subtitle, children, testid }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3" data-testid={testid}>
      <div>
        <h1 className="font-display text-2xl font-bold tracking-tight text-foreground">{title}</h1>
        {subtitle && <p className="mt-0.5 text-sm text-muted-foreground">{subtitle}</p>}
      </div>
      {children && <div className="flex items-center gap-2.5">{children}</div>}
    </div>
  );
}

const STATUS_STYLES = {
  active: ["badge-active", "Active"],
  expiring_soon: ["badge-expiring", "Expiring Soon"],
  expired: ["badge-expired", "Expired"],
  frozen: ["badge-frozen", "Frozen"],
  new: ["badge-frozen", "New"],
  contacted: ["badge-expiring", "Contacted"],
  "follow-up": ["badge-expiring", "Follow-Up"],
  interested: ["badge-active", "Interested"],
  converted: ["badge-active", "Converted"],
  lost: ["badge-expired", "Lost"],
  disabled: ["badge-expired", "Disabled"],
  scheduled: ["badge-frozen", "Scheduled"],
  integration_required: ["badge-expiring", "Integration Required"],
  cancelled: ["badge-expired", "Cancelled"],
  queued: ["badge-frozen", "Queued"],
  sent: ["badge-active", "Sent"],
  paid: ["badge-active", "Paid"],
  failed: ["badge-expired", "Failed"],
  admission: ["badge-active", "Admission"],
  renewal: ["badge-frozen", "Renewal"],
  due: ["badge-expiring", "Due Payment"],
};

export function StatusBadge({ status, label }) {
  const key = String(status || "").toLowerCase();
  const [cls, defaultLabel] = STATUS_STYLES[key] || ["badge-frozen", status];
  return <span className={`badge-status ${cls}`} data-testid={`status-${key}`}>{label || defaultLabel}</span>;
}

export function EmptyState({ icon: Icon = Inbox, title, description, action, testid }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-14 text-center" data-testid={testid}>
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-secondary text-muted-foreground">
        <Icon className="h-6 w-6" />
      </div>
      <p className="mt-4 text-sm font-semibold text-foreground">{title}</p>
      {description && <p className="mt-1 max-w-xs text-sm text-muted-foreground">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function DataTable({ columns, rows, loading, empty, onRowClick, testid, rowKey = "id" }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-card shadow-card" data-testid={testid}>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
            {columns.map((c) => (
              <th key={c.key} className={`px-4 py-3 ${c.align === "right" ? "text-right" : ""}`}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {loading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <tr key={i} className="border-b border-border/60">
                {columns.map((c) => <td key={c.key} className="px-4 py-3"><Skeleton className="h-4 w-full max-w-[120px]" /></td>)}
              </tr>
            ))
          ) : rows.length === 0 ? (
            <tr><td colSpan={columns.length} className="p-0">{empty}</td></tr>
          ) : (
            rows.map((row) => (
              <tr key={row[rowKey]} onClick={onRowClick ? () => onRowClick(row) : undefined}
                  className={`border-b border-border/60 last:border-0 ${onRowClick ? "cursor-pointer hover:bg-secondary/40" : ""}`}
                  data-testid={`${testid}-row-${row[rowKey]}`}>
                {columns.map((c) => (
                  <td key={c.key} className={`px-4 py-2.5 ${c.align === "right" ? "text-right" : ""}`}>
                    {c.render ? c.render(row) : row[c.key] ?? "—"}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export function SearchInput({ value, onChange, placeholder = "Search...", testid }) {
  return (
    <div className="relative">
      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <Input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder}
             className="h-9 rounded-lg pl-9" data-testid={testid} />
    </div>
  );
}

export function ConfirmDialog({ open, onClose, onConfirm, title, description, confirmLabel = "Delete", busy, testid }) {
  return (
    <AlertDialog open={open} onOpenChange={(o) => !o && onClose()}>
      <AlertDialogContent data-testid={testid}>
        <AlertDialogHeader>
          <AlertDialogTitle className="font-display">{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel data-testid={`${testid}-cancel`}>Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm} disabled={busy} data-testid={`${testid}-confirm`}
                             className="bg-danger text-white hover:bg-danger/90">
            {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}{confirmLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

export function MemberPicker({ onSelect, selected, testid }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);

  const search = async (q) => {
    setQuery(q);
    if (q.trim().length < 2) { setResults([]); return; }
    setSearching(true);
    try {
      const { data } = await api.get("/members", { params: { search: q, limit: 8 } });
      setResults(data.items);
    } finally {
      setSearching(false);
    }
  };

  if (selected) {
    return (
      <div className="flex items-center justify-between rounded-lg border border-border bg-secondary/50 px-3 py-2.5" data-testid={`${testid}-selected`}>
        <div>
          <p className="text-sm font-semibold text-foreground">{selected.full_name}</p>
          <p className="text-xs text-muted-foreground">{selected.member_code} · {selected.phone}</p>
        </div>
        <button type="button" onClick={() => onSelect(null)} className="text-xs font-medium text-brand hover:underline" data-testid={`${testid}-clear`}>Change</button>
      </div>
    );
  }

  return (
    <div className="relative">
      <SearchInput value={query} onChange={search} placeholder="Search name, phone or member ID" testid={testid} />
      {searching && <Loader2 className="absolute right-3 top-2.5 h-4 w-4 animate-spin text-muted-foreground" />}
      {results.length > 0 && (
        <div className="absolute z-20 mt-1 w-full rounded-lg border border-border bg-popover shadow-lift" data-testid={`${testid}-results`}>
          {results.map((m) => (
            <button key={m.id} type="button" onClick={() => { onSelect(m); setResults([]); setQuery(""); }}
                    className="flex w-full items-center justify-between px-3 py-2.5 text-left text-sm hover:bg-secondary"
                    data-testid={`${testid}-option-${m.id}`}>
              <span className="font-medium text-foreground">{m.full_name}</span>
              <span className="text-xs text-muted-foreground">{m.member_code}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function DateField({ value, onChange, testid, placeholder = "Select date" }) {
  const date = value ? new Date(`${String(value).slice(0, 10)}T00:00:00`) : undefined;
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button type="button" data-testid={testid}
                className={`flex h-9 w-full items-center justify-between rounded-lg border border-input bg-transparent px-3 text-sm shadow-xs transition-colors hover:border-ring/50 focus:outline-none focus:ring-2 focus:ring-ring/30 ${date ? "text-foreground" : "text-muted-foreground"}`}>
          {date ? format(date, "dd MMM yyyy") : placeholder}
          <CalendarIcon className="h-4 w-4 text-muted-foreground" />
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar mode="single" selected={date} onSelect={(d) => onChange(d ? format(d, "yyyy-MM-dd") : "")} initialFocus />
      </PopoverContent>
    </Popover>
  );
}

export function Pagination({ page, total, limit, onPage, testid }) {
  const pages = Math.max(1, Math.ceil(total / limit));
  if (pages <= 1) return null;
  return (
    <div className="mt-4 flex items-center justify-between text-sm" data-testid={testid}>
      <span className="text-muted-foreground">{total} records · Page {page} of {pages}</span>
      <div className="flex gap-2">
        <button disabled={page <= 1} onClick={() => onPage(page - 1)} data-testid={`${testid}-prev`}
                className="rounded-lg border border-border px-3 py-1.5 font-medium text-foreground disabled:opacity-40 hover:bg-secondary">Previous</button>
        <button disabled={page >= pages} onClick={() => onPage(page + 1)} data-testid={`${testid}-next`}
                className="rounded-lg border border-border px-3 py-1.5 font-medium text-foreground disabled:opacity-40 hover:bg-secondary">Next</button>
      </div>
    </div>
  );
}
