import { useState } from "react";
import { AlertTriangle } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { BottomSheet, Field, TextInput, MButton } from "./ui";
import { deleteCopy, useDeleteAccount } from "../components/app/DeleteAccountCard";

export function DeleteAccountSheet({ open, onOpenChange }) {
  const { user } = useAuth();
  const [f, setF] = useState({ password: "", confirm: "" });
  const { busy, run } = useDeleteAccount("/m/welcome");
  return (
    <BottomSheet open={open} onOpenChange={(o) => { onOpenChange(o); if (!o) setF({ password: "", confirm: "" }); }}
      title="Delete account" testid="m-delete-account-sheet">
      <div className="flex gap-3 rounded-2xl border border-danger/25 bg-danger/8 p-4">
        <AlertTriangle className="h-5 w-5 shrink-0 text-danger" />
        <p className="text-sm leading-relaxed text-foreground">{deleteCopy(user?.role)}</p>
      </div>
      <Field label="Your password"><TextInput type="password" autoComplete="current-password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} data-testid="m-del-password" /></Field>
      <Field label="Type DELETE to confirm"><TextInput value={f.confirm} onChange={(e) => setF({ ...f, confirm: e.target.value })} autoCapitalize="characters" placeholder="DELETE" data-testid="m-del-confirm" /></Field>
      <MButton className="bg-danger shadow-danger/25 hover:bg-danger/90" loading={busy} disabled={f.confirm.trim() !== "DELETE" || !f.password} onClick={() => run(f)} data-testid="m-del-submit">
        Delete permanently
      </MButton>
    </BottomSheet>
  );
}
