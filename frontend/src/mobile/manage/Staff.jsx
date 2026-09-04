import { useEffect, useState } from "react";
import { UserCog } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { MButton, Field, TextInput, PhoneInput, Pills, BottomSheet, ListSkeleton, EmptyRow } from "../ui";
import { ModuleHeader } from "./ModuleHeader";

const EMPTY = { kind: "Staff", name: "", phone: "", email: "", password: "", permission: "view", enable_finance: false };

export default function Staff() {
  const [items, setItems] = useState(null);
  const [open, setOpen] = useState(false);
  const [f, setF] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const load = () => api.get("/staff").then(({ data }) => setItems(data)).catch(() => setItems([]));
  useEffect(() => { load(); }, []);

  const submit = async () => {
    if (f.password && !f.email) return toast.error("Email is required to create a login account");
    setBusy(true);
    try {
      await api.post("/staff", {
        name: f.name.trim(),
        role: f.kind === "Admin" ? "admin" : "staff",
        phone: f.phone.replace(/\D/g, ""),
        email: f.email || undefined,
        password: f.password || undefined,
        permission: f.kind === "Admin" ? "full" : f.permission,
        enable_finance: f.kind === "Admin" ? true : f.enable_finance,
      });
      toast.success(`${f.kind} added`);
      setOpen(false);
      setF(EMPTY);
      load();
    } catch (e) {
      toast.error(apiError(e, "Could not add account"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid="m-staff">
      <ModuleHeader title={items ? `${items.length} accounts` : "Staff"} onAdd={() => setOpen(true)} addLabel="Add Account" testid="m-staff-add" />
      {!items ? (
        <ListSkeleton />
      ) : items.length === 0 ? (
        <EmptyRow icon={UserCog} title="No staff yet" subtitle="Give your team controlled access." testid="m-staff-empty" />
      ) : (
        <div className="space-y-2.5">
          {items.map((s) => (
            <div key={s.id} className="flex items-center gap-3 rounded-2xl border border-border bg-card px-4 py-3.5" data-testid={`m-staff-${s.id}`}>
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-brand/10 font-display text-xs font-bold text-brand">
                {s.name?.slice(0, 2).toUpperCase()}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-foreground">{s.name}</p>
                <p className="truncate text-xs capitalize text-muted-foreground">{s.role} · {s.has_login ? "Has login" : "No login"}</p>
              </div>
              <span className={`badge-status ${s.status === "active" ? "badge-active" : "badge-expired"}`}>{s.status}</span>
            </div>
          ))}
        </div>
      )}

      <BottomSheet open={open} onOpenChange={setOpen} title="Add Staff / Admin" subtitle="Staff / Admins will have access to the gym." testid="m-staff-sheet">
        <Pills options={["Staff", "Admin"]} value={f.kind} onChange={(v) => setF({ ...f, kind: v })} />
        {f.kind === "Admin" && <p className="rounded-xl bg-brand/8 px-3 py-2 text-xs text-brand">Admins get full access to all outlets.</p>}
        <Field label="Name"><TextInput data-testid="m-staff-name" value={f.name} onChange={set("name")} placeholder="Full name" /></Field>
        <Field label="Mobile number"><PhoneInput data-testid="m-staff-phone" value={f.phone} onChange={set("phone")} /></Field>
        <Field label="Email (for login)"><TextInput type="email" autoCapitalize="none" value={f.email} onChange={set("email")} placeholder="staff@gym.com" /></Field>
        <Field label="Password (optional)" hint="Set a password to create a login account."><TextInput type="password" value={f.password} onChange={set("password")} placeholder="Min 8 characters" /></Field>
        {f.kind === "Staff" && (
          <>
            <Field label="Permission"><Pills options={[{ value: "view", label: "View" }, { value: "manage", label: "View & Edit" }, { value: "full", label: "Full" }]} value={f.permission} onChange={(v) => setF({ ...f, permission: v })} /></Field>
            <label className="flex items-center gap-2.5 rounded-xl border border-border px-3.5 py-3">
              <input type="checkbox" checked={f.enable_finance} onChange={(e) => setF({ ...f, enable_finance: e.target.checked })} className="h-4 w-4 accent-[hsl(var(--primary))]" />
              <span className="text-sm font-medium text-foreground">Finance page access</span>
            </label>
          </>
        )}
        <MButton onClick={submit} loading={busy} disabled={f.name.trim().length < 2 || f.phone.replace(/\D/g, "").length !== 10} data-testid="m-staff-save">Add Account</MButton>
      </BottomSheet>
    </div>
  );
}
