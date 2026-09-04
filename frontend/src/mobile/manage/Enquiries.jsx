import { useEffect, useState } from "react";
import { UserPlus } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { MButton, Field, TextInput, PhoneInput, Pills, BottomSheet, ListSkeleton, EmptyRow } from "../ui";
import { ModuleHeader } from "./ModuleHeader";

const EMPTY = { name: "", phone: "", category: "Discussion", follow_up_date: "", notes: "" };

export default function Enquiries() {
  const [items, setItems] = useState(null);
  const [open, setOpen] = useState(false);
  const [f, setF] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const load = () => api.get("/enquiries").then(({ data }) => setItems(data)).catch(() => setItems([]));
  useEffect(() => { load(); }, []);

  const submit = async () => {
    setBusy(true);
    try {
      await api.post("/enquiries", {
        name: f.name.trim(),
        phone: f.phone.replace(/\D/g, ""),
        category: f.category,
        follow_up_date: f.follow_up_date || undefined,
        notes: f.notes || undefined,
        status: "New",
      });
      toast.success("Enquiry added");
      setOpen(false);
      setF(EMPTY);
      load();
    } catch (e) {
      toast.error(apiError(e, "Could not add enquiry"));
    } finally {
      setBusy(false);
    }
  };

  const statusCls = { New: "badge-frozen", Converted: "badge-active", Closed: "badge-expired", "Follow-Up": "badge-expiring" };

  return (
    <div data-testid="m-enquiries">
      <ModuleHeader title={items ? `${items.length} enquiries` : "Enquiries"} onAdd={() => setOpen(true)} addLabel="Add Enquiry" testid="m-enquiries-add" />
      {!items ? (
        <ListSkeleton />
      ) : items.length === 0 ? (
        <EmptyRow icon={UserPlus} title="No enquiries yet" subtitle="Track walk-ins and leads here." testid="m-enquiries-empty" />
      ) : (
        <div className="space-y-2.5">
          {items.map((e) => (
            <div key={e.id} className="flex items-center justify-between rounded-2xl border border-border bg-card px-4 py-3.5" data-testid={`m-enquiry-${e.id}`}>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-foreground">{e.name}</p>
                <p className="truncate text-xs text-muted-foreground">{e.phone} · {e.category || "General"}</p>
              </div>
              <span className={`badge-status ${statusCls[e.status] || "badge-frozen"}`}>{e.status}</span>
            </div>
          ))}
        </div>
      )}

      <BottomSheet open={open} onOpenChange={setOpen} title="Add Enquiry" subtitle="Add enquiry with category and status." testid="m-enquiry-sheet">
        <Field label="Name"><TextInput data-testid="m-enquiry-name" value={f.name} onChange={set("name")} placeholder="Prospect name" /></Field>
        <Field label="Mobile number"><PhoneInput data-testid="m-enquiry-phone" value={f.phone} onChange={set("phone")} /></Field>
        <Field label="Category"><Pills options={["Discussion", "Payment", "Other"]} value={f.category} onChange={(v) => setF({ ...f, category: v })} /></Field>
        <Field label="Follow-up date"><TextInput type="date" value={f.follow_up_date} onChange={set("follow_up_date")} /></Field>
        <Field label="Remark"><TextInput value={f.notes} onChange={set("notes")} placeholder="Optional note" /></Field>
        <MButton onClick={submit} loading={busy} disabled={f.name.trim().length < 2 || f.phone.replace(/\D/g, "").length !== 10} data-testid="m-enquiry-save">Add Enquiry</MButton>
      </BottomSheet>
    </div>
  );
}
