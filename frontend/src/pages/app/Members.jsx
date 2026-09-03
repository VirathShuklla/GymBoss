import { useEffect, useMemo, useState } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import { Plus, Users, Download } from "lucide-react";
import { toast } from "sonner";
import api from "../../lib/api";
import { inr, formatDate, formatPhone } from "../../lib/format";
import { waMe } from "../../lib/whatsapp";
import { useAuth } from "../../contexts/AuthContext";
import { PageHeader, DataTable, SearchInput, StatusBadge, EmptyState, Pagination } from "../../components/app/ui";
import { MemberForm } from "../../components/app/MemberForm";
import { MemberDrawer } from "../../components/app/MemberDrawer";
import { Button } from "../../components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";

const STATUSES = [
  { value: "all", label: "All Statuses" },
  { value: "active", label: "Active" },
  { value: "expiring_soon", label: "Expiring Soon" },
  { value: "expired", label: "Expired" },
  { value: "frozen", label: "Frozen" },
];

export default function Members() {
  const { outlets, user } = useAuth();
  const location = useLocation();
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [plans, setPlans] = useState([]);
  const [search, setSearch] = useState("");
  const [searchField, setSearchField] = useState("name");
  const [status, setStatus] = useState("all");
  const [planId, setPlanId] = useState("all");
  const [gender, setGender] = useState("all");
  const [batch, setBatch] = useState("all");
  const [batches, setBatches] = useState([]);
  const [outletId, setOutletId] = useState("all");
  const [page, setPage] = useState(1);
  const [formOpen, setFormOpen] = useState(false);
  const [editMember, setEditMember] = useState(null);
  const [prefill, setPrefill] = useState(null);
  const [drawerId, setDrawerId] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/members", {
        params: { search: search || undefined, search_field: searchField, status, plan_id: planId === "all" ? undefined : planId, gender, batch, outlet_id: outletId === "all" ? undefined : outletId, page, limit: 20 },
      });
      setData(data);
    } catch {
      toast.error("We couldn't load your members.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [status, planId, outletId, gender, batch, searchField, page]);
  useEffect(() => {
    const t = setTimeout(() => { setPage(1); load(); }, 350);
    return () => clearTimeout(t);
  }, [search]);
  useEffect(() => {
    api.get("/plans", { params: { type: "membership" } }).then(({ data }) => setPlans(data));
    api.get("/batches").then(({ data }) => setBatches(data));
  }, []);

  useEffect(() => {
    if (params.get("add") === "1") {
      setFormOpen(true);
      setParams({}, { replace: true });
    }
    if (location.state?.prefill) {
      setPrefill(location.state.prefill);
      setFormOpen(true);
      window.history.replaceState({}, "");
    }
  }, []);

  const hasFilters = search || status !== "all" || planId !== "all" || outletId !== "all" || gender !== "all" || batch !== "all";
  const readOnly = user?.permission === "view" && user?.role !== "owner";
  const columns = [
    { key: "member", label: "Member", render: (m) => (
      <div className="flex items-center gap-3">
        {m.photo_url ? (
          <img src={`${process.env.REACT_APP_BACKEND_URL}${m.photo_url}`} alt={m.full_name} className="h-9 w-9 shrink-0 rounded-lg object-cover" />
        ) : (
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand/12 font-display text-xs font-bold text-brand">
            {m.full_name.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase()}
          </div>
        )}
        <div>
          <p className="font-medium text-foreground">{m.full_name}</p>
          <p className="font-num text-xs text-muted-foreground">{m.member_code}</p>
        </div>
      </div>
    )},
    { key: "phone", label: "Phone", render: (m) => <span className="font-num text-muted-foreground">{formatPhone(m.phone)}</span> },
    { key: "plan_name", label: "Plan" },
    { key: "joining_date", label: "Joining", render: (m) => formatDate(m.joining_date) },
    { key: "membership_expiry", label: "Expiry", render: (m) => formatDate(m.membership_expiry) },
    { key: "days_left", label: "Days Left", align: "right", render: (m) => (
      <span className={`font-num font-bold ${m.days_left == null ? "text-muted-foreground" : m.days_left < 0 ? "text-danger" : m.days_left <= 7 ? "text-warning" : "text-foreground"}`}>{m.days_left ?? "—"}</span>
    )},
    { key: "due_amount", label: "Due", align: "right", render: (m) => (
      <span className={`font-num font-semibold ${m.due_amount > 0 ? "text-danger" : "text-muted-foreground"}`}>{m.due_amount > 0 ? inr(m.due_amount) : "—"}</span>
    )},
    { key: "status", label: "Status", render: (m) => <StatusBadge status={m.status} /> },
    { key: "wa", label: "", render: (m) => (
      <a href={waMe(m.phone)} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}
         className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-[#25D366] hover:bg-[#25D366]/10" data-testid={`member-wa-${m.id}`} aria-label="WhatsApp">
        <MessageCircleIcon />
      </a>
    )},
  ];

  return (
    <div data-testid="members-page">
      <PageHeader title="Members" subtitle="Manage your gym members and memberships." testid="members-header">
        <Button variant="outline" onClick={() => window.open(`${process.env.REACT_APP_BACKEND_URL}/api/export/members`, "_blank")} data-testid="members-export">
          <Download className="mr-1.5 h-4 w-4" />Export
        </Button>
        {!readOnly && (
          <Button className="bg-brand hover:bg-brand-hover" onClick={() => { setEditMember(null); setPrefill(null); setFormOpen(true); }} data-testid="add-member-button">
            <Plus className="mr-1.5 h-4 w-4" />Add Member
          </Button>
        )}
      </PageHeader>

      <div className="mb-4 flex flex-wrap items-center gap-2.5" data-testid="members-filters">
        <Select value={searchField} onValueChange={setSearchField}>
          <SelectTrigger className="h-9 w-32 rounded-r-none border-r-0" data-testid="members-search-field"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="name">Name</SelectItem>
            <SelectItem value="phone">Phone</SelectItem>
            <SelectItem value="code">Member ID</SelectItem>
          </SelectContent>
        </Select>
        <div className="-ml-2.5 w-full sm:w-56"><SearchInput value={search} onChange={setSearch} placeholder="Search members..." testid="members-search" /></div>
        {outlets.length > 1 && (
          <Select value={outletId} onValueChange={(v) => { setOutletId(v); setPage(1); }}>
            <SelectTrigger className="h-9 w-36" data-testid="members-outlet-filter"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Outlets</SelectItem>
              {outlets.map((o) => <SelectItem key={o.id} value={o.id}>{o.name}</SelectItem>)}
            </SelectContent>
          </Select>
        )}
        <Select value={status} onValueChange={(v) => { setStatus(v); setPage(1); }}>
          <SelectTrigger className="h-9 w-36" data-testid="members-status-filter"><SelectValue /></SelectTrigger>
          <SelectContent>{STATUSES.map((s) => <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>)}</SelectContent>
        </Select>
        <Select value={gender} onValueChange={(v) => { setGender(v); setPage(1); }}>
          <SelectTrigger className="h-9 w-32" data-testid="members-gender-filter"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Genders</SelectItem>
            <SelectItem value="Male">Male</SelectItem>
            <SelectItem value="Female">Female</SelectItem>
            <SelectItem value="Other">Other</SelectItem>
          </SelectContent>
        </Select>
        <Select value={batch} onValueChange={(v) => { setBatch(v); setPage(1); }}>
          <SelectTrigger className="h-9 w-36" data-testid="members-batch-filter"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Batches</SelectItem>
            {batches.map((b) => <SelectItem key={b.id} value={b.name}>{b.name}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={planId} onValueChange={(v) => { setPlanId(v); setPage(1); }}>
          <SelectTrigger className="h-9 w-36" data-testid="members-plan-filter"><SelectValue placeholder="All Plans" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Plans</SelectItem>
            {plans.map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      <DataTable
        testid="members-table"
        columns={columns}
        rows={data.items}
        loading={loading}
        onRowClick={(m) => setDrawerId(m.id)}
        empty={hasFilters
          ? <EmptyState icon={Users} title="No members match your filters" description="Try a different search or clear the filters."
                        action={<Button variant="outline" onClick={() => { setSearch(""); setStatus("all"); setPlanId("all"); setOutletId("all"); setGender("all"); setBatch("all"); }} data-testid="members-clear-filters">Clear Filters</Button>} testid="members-filtered-empty" />
          : <EmptyState icon={Users} title="No members yet" description="Add your first member to begin managing memberships."
                        action={<Button className="bg-brand hover:bg-brand-hover" onClick={() => setFormOpen(true)} data-testid="empty-add-member"><Plus className="mr-1.5 h-4 w-4" />Add Member</Button>} testid="members-empty" />}
      />
      <Pagination page={page} total={data.total} limit={20} onPage={setPage} testid="members-pagination" />

      <MemberForm open={formOpen} onClose={() => setFormOpen(false)} member={editMember} prefill={prefill}
                  plans={plans} outlets={outlets} onSaved={load} />
      <MemberDrawer memberId={drawerId} onClose={() => setDrawerId(null)} onChanged={load} plans={plans}
                    onEdit={(m) => { setEditMember(m); setFormOpen(true); }} />
    </div>
  );
}

function MessageCircleIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4" aria-hidden="true">
      <path d="M12.04 2C6.58 2 2.13 6.45 2.13 11.91c0 1.75.46 3.45 1.32 4.95L2.05 22l5.25-1.38a9.87 9.87 0 0 0 4.74 1.21h.01c5.46 0 9.9-4.45 9.9-9.91A9.85 9.85 0 0 0 12.04 2zm4.52 12.32c-.25-.13-1.47-.72-1.69-.81-.23-.08-.39-.12-.56.13-.16.25-.64.8-.78.97-.14.16-.29.18-.54.06-.25-.13-1.05-.39-1.99-1.23-.74-.66-1.23-1.47-1.38-1.72-.14-.25-.01-.38.11-.51.11-.11.25-.29.37-.43.12-.14.16-.25.25-.41.08-.17.04-.31-.02-.43-.06-.13-.56-1.34-.76-1.84-.2-.48-.41-.42-.56-.43h-.48c-.17 0-.43.06-.66.31-.22.25-.86.85-.86 2.07 0 1.22.89 2.4 1.01 2.56.12.17 1.75 2.67 4.23 3.74.59.26 1.05.41 1.41.52.59.19 1.13.16 1.56.1.48-.07 1.47-.6 1.67-1.18.21-.58.21-1.07.14-1.18-.06-.1-.22-.16-.47-.28z" />
    </svg>
  );
}
