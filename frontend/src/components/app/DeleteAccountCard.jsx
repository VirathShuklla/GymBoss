import { useState } from "react";
import { Loader2, Trash2 } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { useAuth } from "../../contexts/AuthContext";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "../ui/dialog";

export const deleteCopy = (role) => role === "owner"
  ? "This permanently deletes your gym, all members, payments, attendance, staff logins and uploaded files. Any auto-renewal is cancelled. This cannot be undone."
  : "This permanently deletes your staff login. Your gym's data is not affected. This cannot be undone.";

export function useDeleteAccount(redirectTo) {
  const { logout } = useAuth();
  const [busy, setBusy] = useState(false);
  const run = async ({ password, confirm }) => {
    if (!password) return toast.error("Enter your password");
    if (confirm.trim() !== "DELETE") return toast.error("Type DELETE to confirm");
    setBusy(true);
    try {
      const { data } = await api.post("/auth/delete-account", { password, confirm: confirm.trim() });
      toast.success(data.message);
      await logout();
      window.location.replace(redirectTo);
    } catch (err) {
      toast.error(apiError(err, "Could not delete account"));
    } finally {
      setBusy(false);
    }
  };
  return { busy, run };
}

export function DeleteAccountCard() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ password: "", confirm: "" });
  const { busy, run } = useDeleteAccount("/");
  return (
    <div className="rounded-xl border border-danger/25 bg-danger/5 p-6 lg:col-span-2" data-testid="delete-account-card">
      <p className="font-display text-base font-bold text-danger">Delete Account</p>
      <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{deleteCopy(user?.role)}</p>
      <Button variant="outline" className="mt-4 border-danger/40 text-danger hover:bg-danger/10 hover:text-danger" onClick={() => setOpen(true)} data-testid="delete-account-open">
        <Trash2 className="mr-2 h-4 w-4" />Delete my account
      </Button>
      <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (!o) setF({ password: "", confirm: "" }); }}>
        <DialogContent data-testid="delete-account-dialog">
          <DialogHeader>
            <DialogTitle className="text-danger">Delete your account?</DialogTitle>
            <DialogDescription>{deleteCopy(user?.role)}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5"><Label>Your password</Label><Input type="password" autoComplete="current-password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} data-testid="delete-account-password" /></div>
            <div className="space-y-1.5"><Label>Type <span className="font-mono font-bold">DELETE</span> to confirm</Label><Input value={f.confirm} onChange={(e) => setF({ ...f, confirm: e.target.value })} autoCapitalize="characters" data-testid="delete-account-confirm-text" /></div>
            <div className="flex gap-3">
              <Button variant="outline" className="flex-1" onClick={() => setOpen(false)} data-testid="delete-account-cancel">Cancel</Button>
              <Button className="flex-1 bg-danger text-white hover:bg-danger/90" disabled={busy || f.confirm.trim() !== "DELETE" || !f.password} onClick={() => run(f)} data-testid="delete-account-submit">
                {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Delete permanently
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
