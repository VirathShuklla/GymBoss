import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, UserPlus, Loader2, CalendarPlus, ArrowRightLeft, Pencil } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { formatDate, formatPhone } from "../../lib/format";
import { waMe } from "../../lib/whatsapp";
import { useAuth } from "../../contexts/AuthContext";
import { PageHeader, DataTable, StatusBadge, EmptyState, SearchInput, DateField } from "../../components/app/ui";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../../components/ui/dialog";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";

const SOURCES = ["Walk-In", "Instagram", "Facebook", "Google", "Website", "Referral", "WhatsApp", "Other"];
const STATUSES = ["New", "Contacted", "Follow-Up", "Interested", "Converted", "Lost"];

function EnquiryDialog({ open, onClose, enquiry, onSaved }) {
  const blank = { name: "", phone: "", email: "", follow_up_date: "", category: "", status: "New", source: "Walk-In", notes: "" };
  const [form, setForm] = useState(blank);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (open) setForm(enquiry ? { ...blank, ...enquiry, phone: (enquiry.phone || "").replace(/\D/g, "").slice(-10) } : blank);
  }, [open, enquiry]);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (enquiry) {
        await api.put(`/enquiries/${enquiry.id}`, form);
        toast.success("Enquiry updated");
      } else {
        await api.post("/enquiries", form);
        toast.success("Enquiry added");
      }
      onSaved(); onClose();
    } catch (err) {
      toast.error(apiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md" data-testid="enquiry-form-modal">
        <DialogHeader><DialogTitle className="font-display text-lg">{enquiry ? "Edit Enquiry" : "Add Enquiry"}</DialogTitle></DialogHeader>
        <form onSubmit={submit} className="space-y-4">
          <div className="space-y-1.5"><Label>Name</Label><Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="enquiry-form-name" /></div>
          <div className="space-y-1.5">
            <Label>Phone</Label>
            <div className="flex">
              <span className="inline-flex items-center rounded-l-lg border border-r-0 border-input bg-secondary px-3 text-sm text-muted-foreground">+91</span>
              <Input required inputMode="numeric" className="rounded-l-none" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} data-testid="enquiry-form-phone" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5"><Label>Email <span className="font-normal text-muted-foreground">(optional)</span></Label><Input type="email" value={form.email || ""} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
            <div className="space-y-1.5"><Label>Follow-Up Date</Label><DateField value={form.follow_up_date || ""} onChange={(v) => setForm({ ...form, follow_up_date: v })} testid="enquiry-form-followup" /></div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5"><Label>Interested In</Label><Input value={form.category || ""} onChange={(e) => setForm({ ...form, category: e.target.value })} placeholder="e.g., Membership, PT" /></div>
            <div className="space-y-1.5">
              <Label>Source</Label>
              <Select value={form.source} onValueChange={(v) => setForm({ ...form, source: v })}>
                <SelectTrigger data-testid="enquiry-form-source"><SelectValue /></SelectTrigger>
                <SelectContent>{SOURCES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>Status</Label>
            <Select value={form.status} onValueChange={(v) => setForm({ ...form, status: v })}>
              <SelectTrigger data-testid="enquiry-form-status"><SelectValue /></SelectTrigger>
              <SelectContent>{STATUSES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5"><Label>Notes</Label><Textarea rows={2} value={form.notes || ""} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>
          <div className="flex justify-end gap-3">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" className="bg-brand hover:bg-brand-hover" disabled={busy} data-testid="enquiry-form-submit">
              {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}{enquiry ? "Save" : "Add Enquiry"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function Enquiries() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const readOnly = user?.permission === "view" && user?.role !== "owner";
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editEnquiry, setEditEnquiry] = useState(null);
  const [followUp, setFollowUp] = useState(null);
  const [fuForm, setFuForm] = useState({ date: "", note: "" });
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/enquiries", { params: { search: search || undefined, status } });
      setItems(data);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, [status]);
  useEffect(() => {
    const t = setTimeout(load, 350);
    return () => clearTimeout(t);
  }, [search]);

  const addFollowUp = async () => {
    if (!fuForm.date) return toast.error("Select a follow-up date");
    setBusy(true);
    try {
      await api.post(`/enquiries/${followUp.id}/follow-ups`, fuForm);
      toast.success("Follow-up added");
      setFollowUp(null); setFuForm({ date: "", note: "" });
      load();
    } catch (e) {
      toast.error(apiError(e));
    } finally {
      setBusy(false);
    }
  };

  const convert = (enquiry) => {
    navigate("/app/members", {
      state: { prefill: { full_name: enquiry.name, phone: enquiry.phone, email: enquiry.email || "", notes: `Converted from enquiry (${enquiry.source || "direct"})`, enquiry_id: enquiry.id } },
    });
  };

  const columns = [
    { key: "name", label: "Name", render: (e) => (
      <div><p className="font-medium text-foreground">{e.name}</p><p className="font-num text-xs text-muted-foreground">{formatPhone(e.phone)}</p></div>
    )},
    { key: "category", label: "Interested In", render: (e) => e.category || "—" },
    { key: "source", label: "Source" },
    { key: "follow_up_date", label: "Follow-Up", render: (e) => formatDate(e.follow_up_date) },
    { key: "status", label: "Status", render: (e) => <StatusBadge status={e.status} /> },
    { key: "actions", label: "", align: "right", render: (e) => (
      <div className="flex justify-end gap-1">
        <a href={waMe(e.phone, `Hi ${e.name.split(" ")[0]}, thanks for your interest in our gym!`)} target="_blank" rel="noopener noreferrer"
           className="rounded-md p-1.5 text-[#25D366] hover:bg-[#25D366]/10" data-testid={`enquiry-wa-${e.id}`} aria-label="WhatsApp">
          <svg viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4"><path d="M12.04 2C6.58 2 2.13 6.45 2.13 11.91c0 1.75.46 3.45 1.32 4.95L2.05 22l5.25-1.38a9.87 9.87 0 0 0 4.74 1.21h.01c5.46 0 9.9-4.45 9.9-9.91A9.85 9.85 0 0 0 12.04 2zm4.52 12.32c-.25-.13-1.47-.72-1.69-.81-.23-.08-.39-.12-.56.13-.16.25-.64.8-.78.97-.14.16-.29.18-.54.06-.25-.13-1.05-.39-1.99-1.23-.74-.66-1.23-1.47-1.38-1.72-.14-.25-.01-.38.11-.51.11-.11.25-.29.37-.43.12-.14.16-.25.25-.41.08-.17.04-.31-.02-.43-.06-.13-.56-1.34-.76-1.84-.2-.48-.41-.42-.56-.43h-.48c-.17 0-.43.06-.66.31-.22.25-.86.85-.86 2.07 0 1.22.89 2.4 1.01 2.56.12.17 1.75 2.67 4.23 3.74.59.26 1.05.41 1.41.52.59.19 1.13.16 1.56.1.48-.07 1.47-.6 1.67-1.18.21-.58.21-1.07.14-1.18-.06-.1-.22-.16-.47-.28z"/></svg>
        </a>
        <button onClick={() => { setFollowUp(e); }} className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground" data-testid={`enquiry-followup-${e.id}`} aria-label="Add follow-up"><CalendarPlus className="h-4 w-4" /></button>
        <button onClick={() => { setEditEnquiry(e); setDialogOpen(true); }} className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground" data-testid={`enquiry-edit-${e.id}`} aria-label="Edit"><Pencil className="h-4 w-4" /></button>
        {e.status !== "Converted" && (
          <button onClick={() => convert(e)} className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-semibold text-brand hover:bg-brand/10" data-testid={`enquiry-convert-${e.id}`}>
            <ArrowRightLeft className="h-3.5 w-3.5" />Convert
          </button>
        )}
      </div>
    )},
  ];

  const hasFilters = search || status !== "all";
  return (
    <div data-testid="enquiries-page">
      <PageHeader title="Enquiries" subtitle="Track leads and convert them into members." testid="enquiries-header">
        {!readOnly && (
          <Button className="bg-brand hover:bg-brand-hover" onClick={() => { setEditEnquiry(null); setDialogOpen(true); }} data-testid="add-enquiry-button">
            <Plus className="mr-1.5 h-4 w-4" />Add Enquiry
          </Button>
        )}
      </PageHeader>
      <div className="mb-4 flex flex-wrap gap-2.5">
        <div className="w-full sm:w-64"><SearchInput value={search} onChange={setSearch} placeholder="Name or phone" testid="enquiries-search" /></div>
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="h-9 w-40" data-testid="enquiries-status-filter"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            {STATUSES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
      <DataTable testid="enquiries-table" columns={columns} rows={items} loading={loading}
                 empty={hasFilters
                   ? <EmptyState icon={UserPlus} title="No enquiries match your filters" description="Try a different search or clear the filters."
                                 action={<Button variant="outline" onClick={() => { setSearch(""); setStatus("all"); }} data-testid="enquiries-clear-filters">Clear Filters</Button>} testid="enquiries-filtered-empty" />
                   : <EmptyState icon={UserPlus} title="No enquiries yet" description="Capture walk-ins and online leads here."
                                 action={<Button className="bg-brand hover:bg-brand-hover" onClick={() => setDialogOpen(true)} data-testid="empty-add-enquiry"><Plus className="mr-1.5 h-4 w-4" />Add Enquiry</Button>} testid="enquiries-empty" />} />
      <EnquiryDialog open={dialogOpen} onClose={() => setDialogOpen(false)} enquiry={editEnquiry} onSaved={load} />
      <Dialog open={Boolean(followUp)} onOpenChange={(o) => !o && setFollowUp(null)}>
        <DialogContent className="max-w-sm" data-testid="followup-modal">
          <DialogHeader><DialogTitle className="font-display">Add Follow-Up — {followUp?.name}</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5"><Label>Next Follow-Up Date</Label><DateField value={fuForm.date} onChange={(v) => setFuForm({ ...fuForm, date: v })} testid="followup-date" /></div>
            <div className="space-y-1.5"><Label>Note</Label><Textarea rows={2} value={fuForm.note} onChange={(e) => setFuForm({ ...fuForm, note: e.target.value })} data-testid="followup-note" /></div>
            {followUp?.follow_ups?.length > 0 && (
              <div className="space-y-1.5">
                <Label>History</Label>
                <div className="max-h-32 space-y-1.5 overflow-y-auto">
                  {followUp.follow_ups.map((f, i) => (
                    <p key={i} className="rounded-lg bg-secondary/60 px-3 py-2 text-xs text-muted-foreground">{formatDate(f.date)} — {f.note || "Follow-up scheduled"}</p>
                  ))}
                </div>
              </div>
            )}
            <Button className="w-full bg-brand hover:bg-brand-hover" onClick={addFollowUp} disabled={busy} data-testid="followup-submit">
              {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Save Follow-Up
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
