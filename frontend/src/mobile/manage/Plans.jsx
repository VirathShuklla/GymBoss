import { useEffect, useState } from "react";
import { Layers } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { inr } from "../../lib/format";
import { MButton, Field, TextInput, Pills, BottomSheet, ListSkeleton, EmptyRow } from "../ui";
import { ModuleHeader } from "./ModuleHeader";

const EMPTY = { name: "", type: "membership", duration_type: "months", duration: "1", price: "" };
const TYPE_LABEL = { membership: "Membership", pt: "PT", service: "Service", product: "Product" };

export default function Plans() {
  const [items, setItems] = useState(null);
  const [open, setOpen] = useState(false);
  const [f, setF] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const load = () => api.get("/plans").then(({ data }) => setItems(data)).catch(() => setItems([]));
  useEffect(() => { load(); }, []);

  const submit = async () => {
    setBusy(true);
    try {
      await api.post("/plans", {
        name: f.name.trim(),
        type: f.type,
        duration_type: f.duration_type,
        duration: Number(f.duration) || 1,
        price: Number(f.price) || 0,
      });
      toast.success("Plan added");
      setOpen(false);
      setF(EMPTY);
      load();
    } catch (e) {
      toast.error(apiError(e, "Could not add plan"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid="m-plans">
      <ModuleHeader title={items ? `${items.length} items` : "Plans"} onAdd={() => setOpen(true)} addLabel="Add Plan" testid="m-plans-add" />
      {!items ? (
        <ListSkeleton />
      ) : items.length === 0 ? (
        <EmptyRow icon={Layers} title="No plans yet" subtitle="Create membership, PT, service or product items." testid="m-plans-empty" />
      ) : (
        <div className="space-y-2.5">
          {items.map((p) => (
            <div key={p.id} className="flex items-center justify-between rounded-2xl border border-border bg-card px-4 py-3.5" data-testid={`m-plan-${p.id}`}>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-foreground">{p.name}</p>
                <p className="text-xs text-muted-foreground">{TYPE_LABEL[p.type] || p.type}{p.type === "membership" ? ` · ${p.duration} ${p.duration_type}` : ""}</p>
              </div>
              <p className="font-num text-sm font-bold text-foreground">{inr(p.price)}</p>
            </div>
          ))}
        </div>
      )}

      <BottomSheet open={open} onOpenChange={setOpen} title="Add Plan" subtitle="Add a plan or catalogue item." testid="m-plan-sheet">
        <Field label="Name"><TextInput data-testid="m-plan-name" value={f.name} onChange={set("name")} placeholder="Eg. 6 Months Membership" /></Field>
        <Field label="Type"><Pills options={Object.entries(TYPE_LABEL).map(([value, label]) => ({ value, label }))} value={f.type} onChange={(v) => setF({ ...f, type: v })} /></Field>
        {f.type === "membership" && (
          <div className="grid grid-cols-2 gap-3">
            <Field label="Duration type"><Pills options={[{ value: "months", label: "Months" }, { value: "days", label: "Days" }]} value={f.duration_type} onChange={(v) => setF({ ...f, duration_type: v })} /></Field>
            <Field label="Duration"><TextInput inputMode="numeric" value={f.duration} onChange={set("duration")} placeholder="6" /></Field>
          </div>
        )}
        <Field label="Amount"><TextInput inputMode="numeric" data-testid="m-plan-price" value={f.price} onChange={set("price")} placeholder="Eg. 3000" /></Field>
        <MButton onClick={submit} loading={busy} disabled={f.name.trim().length < 2} data-testid="m-plan-save">Add Plan</MButton>
      </BottomSheet>
    </div>
  );
}
