import { useState } from "react";
import { ChevronRight, ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "../../contexts/AuthContext";
import { MButton } from "../ui";

const DEFAULTS = {
  plan_expiring: { label: "Plan Expiring", desc: "Remind about plan expiry", text: "Hi {member_name},\nKindly renew your gym membership before it expires.\nExpires on: {end_date}\n\nRegards,\n{gym_name}" },
  plan_expired: { label: "Plan Expired", desc: "Remind about expired plan", text: "Hi {member_name},\nYour gym membership expired on {end_date}.\nKindly renew it soon.\n\nRegards,\n{gym_name}" },
  pending_due: { label: "Pending Due", desc: "Remind about pending dues", text: "Hi {member_name},\nYour gym membership has a pending due amount of {due_amount}.\nKindly clear the dues soon.\n\nRegards,\n{gym_name}" },
  birthday_wish: { label: "Birthday Wish", desc: "Send birthday wish", text: "Hi {member_name},\nWe wish you a very Happy Birthday.\nEnjoy your day.\n\nRegards,\n{gym_name}" },
};
const TOKENS = ["{member_name}", "{gym_name}", "{end_date}", "{due_amount}"];

export default function Templates() {
  const { organisation } = useAuth();
  const storeKey = `gb-m-templates-${organisation?.id || "x"}`;
  const [store, setStore] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(storeKey) || "{}");
      const merged = {};
      Object.keys(DEFAULTS).forEach((k) => (merged[k] = saved[k] ?? DEFAULTS[k].text));
      return merged;
    } catch {
      return Object.fromEntries(Object.entries(DEFAULTS).map(([k, v]) => [k, v.text]));
    }
  });
  const [editing, setEditing] = useState(null);
  const [draft, setDraft] = useState("");

  const openEdit = (k) => { setEditing(k); setDraft(store[k]); };
  const insertToken = (t) => setDraft((d) => `${d}${t}`);
  const save = () => {
    const next = { ...store, [editing]: draft };
    setStore(next);
    localStorage.setItem(storeKey, JSON.stringify(next));
    toast.success("Template saved");
    setEditing(null);
  };

  const preview = (txt) =>
    txt.replace(/{member_name}/g, "John Doe").replace(/{gym_name}/g, organisation?.name || "Your Gym").replace(/{end_date}/g, "Dec 31, 2026").replace(/{due_amount}/g, "₹500");

  if (editing) {
    return (
      <div data-testid="m-template-edit">
        <button onClick={() => setEditing(null)} className="mb-4 flex items-center gap-2 text-sm font-semibold text-muted-foreground">
          <ArrowLeft className="h-4 w-4" /> {DEFAULTS[editing].label}
        </button>
        <p className="mb-2 text-xs font-semibold text-muted-foreground">Insert</p>
        <div className="mb-4 flex flex-wrap gap-2">
          {TOKENS.map((t) => (
            <button key={t} onClick={() => insertToken(t)} className="rounded-full bg-secondary px-3 py-1.5 font-num text-xs font-medium text-foreground">{t}</button>
          ))}
        </div>
        <textarea
          data-testid="m-template-textarea"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={7}
          className="w-full rounded-2xl border border-input bg-background p-4 text-[15px] leading-relaxed text-foreground outline-none focus:border-brand"
        />
        <p className="mb-2 mt-5 text-xs font-semibold text-muted-foreground">Preview</p>
        <div className="whitespace-pre-line rounded-2xl border border-border bg-card p-4 text-sm text-foreground">{preview(draft)}</div>
        <MButton className="mt-5" onClick={save} data-testid="m-template-save">Save Template</MButton>
      </div>
    );
  }

  return (
    <div data-testid="m-templates">
      <p className="mb-3 text-sm font-semibold text-muted-foreground">Customize reminder message templates.</p>
      <div className="space-y-2.5">
        {Object.entries(DEFAULTS).map(([k, v]) => (
          <button key={k} onClick={() => openEdit(k)} data-testid={`m-template-${k}`}
            className="flex w-full items-center justify-between rounded-2xl border border-border bg-card px-4 py-4 text-left active:scale-[0.99]">
            <div>
              <p className="text-sm font-semibold text-foreground">{v.label}</p>
              <p className="text-xs text-muted-foreground">{v.desc}</p>
            </div>
            <ChevronRight className="h-5 w-5 text-muted-foreground" />
          </button>
        ))}
      </div>
    </div>
  );
}
