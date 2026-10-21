import { useEffect, useState } from "react";
import { UserCog, ChevronRight } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { MButton, Field, TextInput, PhoneInput, Pills, BottomSheet, ListSkeleton, EmptyRow } from "../ui";
import { ModuleHeader } from "./ModuleHeader";

const EMPTY = { kind: "Staff", name: "", phone: "", email: "", password: "", permission: "view", enable_finance: false };

const fromStaff = (s) => ({
  kind: s.role === "admin" ? "Admin" : "Staff", name: s.name || "", phone: (s.phone || "").replace(/\D/g, "").slice(-10),
  email: s.email || "", password: "", permission: s.permission || "view", enable_finance: !!s.enable_finance,
});

export default function Staff() {
  const [items, setItems] = useState(null);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [f, setF] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const load = () => api.get("/staff").then(({ data }) => setItems(data)).catch(() => setItems([]));
  useEffect(() => { load(); }, []);

  const openNew = () => { setEditing(null); setF(EMPTY); setOpen(true); };
  const openEdit = (s) => { setEditing(s); setF(fromStaff(s)); setOpen(true); };

  const submit = async () => {
    const needsEmail = f.password || editing?.has_login;
    if (needsEmail && !f.email) return toast.error("Email is required for a login account");
    if (f.password && f.password.length < 8) return toast.error("Password must be at least 8 characters");
    const admin = f.kind === "Admin";
    const body = {
      name: f.name.trim(),
      role: admin ? "admin" : (editing && editing.role !== "admin" ? editing.role : "staff"),
      phone: f.phone.replace(/\D/g, ""),
      email: f.email.trim() || undefined,
      password: f.password || undefined,
      permission: admin ? "full" : f.permission,
      enable_finance: admin ? true : f.enable_finance,
    };
    setBusy(true);
    try {
      if (editing) {
        const { address, joining_date, outlet_id, salary, gender } = editing;
        await api.put(`/staff/${editing.id}`, { address, joining_date, outlet_id, salary, gender, ...body });
        toast.success("Account updated");
      } else {
        await api.post("/staff", body);
        toast.success(`${f.kind} added`);
      }
      setOpen(false);
      load();
    } catch (e) {
      toast.error(apiError(e, "Could not save account"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid="m-staff">
      <ModuleHeader title={items ? `${items.length} accounts` : "Staff"} onAdd={openNew} addLabel="Add Account" testid="m-staff-add" />
      {!items ? (
        <ListSkeleton />
      ) : items.length === 0 ? (
        <EmptyRow icon={UserCog} title="No staff yet" subtitle="Give your team controlled access." testid="m-staff-empty" />
      ) : (
        <div className="m-group">
          {items.map((s) => (
            <button key={s.id} onClick={() => openEdit(s)}               className="m-group-row text-left" data-testid={`m-staff-${s.id}`}>
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-secondary font-display text-xs font-bold text-foreground">
                {s.name?.slice(0, 2).toUpperCase()}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-foreground">{s.name}</p>
                <p className="truncate text-xs text-muted-foreground"><span className="capitalize">{s.role}</span> · {s.has_login ? s.email : "No login"}</p>
              </div>
              <span className={`badge-status capitalize ${s.status === "active" ? "badge-active" : "badge-expired"}`}>{s.status}</span>
              <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
            </button>
          ))}
        </div>
      )}

      <BottomSheet open={open} onOpenChange={setOpen} title={editing ? "Edit account" : "Add Staff / Admin"}
        subtitle={editing ? "Update details, login email or password." : "Staff / Admins will have access to the gym."} testid="m-staff-sheet">
        <Pills options={["Staff", "Admin"]} value={f.kind} onChange={(v) => setF({ ...f, kind: v })} />
        {f.kind === "Admin" && <p className="rounded-xl bg-brand/8 px-3 py-2 text-xs text-brand">Admins get full access to all outlets.</p>}
        <Field label="Name"><TextInput data-testid="m-staff-name" value={f.name} onChange={set("name")} placeholder="Full name" /></Field>
        <Field label="Mobile number"><PhoneInput data-testid="m-staff-phone" value={f.phone} onChange={set("phone")} /></Field>
        <Field label="Email (for login)" hint={editing?.has_login ? "Changing this updates their login email and signs them out." : undefined}>
          <TextInput data-testid="m-staff-email" type="email" autoCapitalize="none" value={f.email} onChange={set("email")} placeholder="staff@gym.com" />
        </Field>
        <Field label={editing?.has_login ? "New password (optional)" : "Password (optional)"} hint={editing?.has_login ? "Leave blank to keep the current password." : "Set a password to create a login account."}>
          <TextInput data-testid="m-staff-password" type="password" value={f.password} onChange={set("password")} placeholder="Min 8 characters" />
        </Field>
        {f.kind === "Staff" && (
          <>
            <Field label="Permission"><Pills options={[{ value: "view", label: "View" }, { value: "manage", label: "View & Edit" }, { value: "full", label: "Full" }]} value={f.permission} onChange={(v) => setF({ ...f, permission: v })} /></Field>
            <label className="flex min-h-[48px] items-center gap-2.5 rounded-xl border border-border px-3.5 py-3">
              <input type="checkbox" checked={f.enable_finance} onChange={(e) => setF({ ...f, enable_finance: e.target.checked })} className="h-4 w-4 accent-[hsl(var(--primary))]" />
              <span className="text-sm font-medium text-foreground">Finance page access</span>
            </label>
          </>
        )}
        <MButton onClick={submit} loading={busy} disabled={f.name.trim().length < 2 || f.phone.replace(/\D/g, "").length !== 10} data-testid="m-staff-save">
          {editing ? "Save Changes" : "Add Account"}
        </MButton>
      </BottomSheet>
    </div>
  );
}
