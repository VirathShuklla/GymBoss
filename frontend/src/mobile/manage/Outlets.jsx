import { useEffect, useState } from "react";
import { Building2, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { MButton, Field, TextInput, BottomSheet, ListSkeleton, EmptyRow } from "../ui";
import { ModuleHeader } from "./ModuleHeader";

const EMPTY = { name: "", address: "" };

export default function Outlets() {
  const [items, setItems] = useState(null);
  const [open, setOpen] = useState(false);
  const [f, setF] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const load = () => api.get("/outlets").then(({ data }) => setItems(data)).catch(() => setItems([]));
  useEffect(() => { load(); }, []);

  const submit = async () => {
    setBusy(true);
    try {
      await api.post("/outlets", { name: f.name.trim(), address: f.address || undefined, city: f.name.trim() });
      toast.success("Outlet added");
      setOpen(false);
      setF(EMPTY);
      load();
    } catch (e) {
      toast.error(apiError(e, "Could not add outlet"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid="m-outlets">
      <ModuleHeader title={items ? `${items.length} outlets` : "Outlets"} onAdd={() => setOpen(true)} addLabel="Add Outlet" testid="m-outlets-add" />
      {!items ? (
        <ListSkeleton />
      ) : items.length === 0 ? (
        <EmptyRow icon={Building2} title="No outlets yet" testid="m-outlets-empty" />
      ) : (
        <div className="space-y-2.5">
          {items.map((o) => (
            <div key={o.id} className="flex items-center gap-3 rounded-2xl border border-border bg-card px-4 py-3.5" data-testid={`m-outlet-${o.id}`}>
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand/10 text-brand"><Building2 className="h-5 w-5" /></span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-foreground">{o.name}</p>
                {o.address && <p className="truncate text-xs text-muted-foreground">{o.address}</p>}
              </div>
              {o.is_primary && <CheckCircle2 className="h-5 w-5 text-success" />}
            </div>
          ))}
        </div>
      )}

      <BottomSheet open={open} onOpenChange={setOpen} title="Add New Outlet" subtitle="Fill up the required fields." testid="m-outlet-sheet">
        <Field label="Location (Area / City)"><TextInput data-testid="m-outlet-name" value={f.name} onChange={set("name")} placeholder="Eg. Indiranagar" /></Field>
        <Field label="Address (Optional)"><TextInput value={f.address} onChange={set("address")} placeholder="Street address" /></Field>
        <MButton onClick={submit} loading={busy} disabled={f.name.trim().length < 2} data-testid="m-outlet-save">Add Outlet</MButton>
      </BottomSheet>
    </div>
  );
}
