import { useState } from "react";
import { toast } from "sonner";
import api, { apiError } from "../lib/api";
import { BottomSheet, Field, TextInput, MButton } from "./ui";
import { validatePasswordChange } from "../components/app/ChangePasswordCard";

const EMPTY = { current_password: "", new_password: "", confirm: "" };

export function ChangePasswordSheet({ open, onOpenChange }) {
  const [f, setF] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const submit = async () => {
    const v = validatePasswordChange(f);
    if (v) return toast.error(v);
    setBusy(true);
    try {
      const { data } = await api.post("/auth/change-password", { current_password: f.current_password, new_password: f.new_password });
      toast.success(data.message);
      setF(EMPTY);
      onOpenChange(false);
    } catch (err) {
      toast.error(apiError(err, "Could not change password"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <BottomSheet open={open} onOpenChange={onOpenChange} title="Change password" subtitle="Other devices will be signed out." testid="m-change-password-sheet">
      <div className="space-y-4">
        <Field label="Current password"><TextInput type="password" autoComplete="current-password" value={f.current_password} onChange={set("current_password")} data-testid="m-cp-current" /></Field>
        <Field label="New password" hint="At least 8 characters."><TextInput type="password" autoComplete="new-password" value={f.new_password} onChange={set("new_password")} data-testid="m-cp-new" /></Field>
        <Field label="Confirm new password"><TextInput type="password" autoComplete="new-password" value={f.confirm} onChange={set("confirm")} data-testid="m-cp-confirm" /></Field>
        <MButton onClick={submit} loading={busy} data-testid="m-cp-save">Update password</MButton>
      </div>
    </BottomSheet>
  );
}
