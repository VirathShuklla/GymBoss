import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { CheckCircle2, LogOut, AlertCircle, Loader2, Dumbbell } from "lucide-react";
import api, { apiError } from "../lib/api";

export default function CheckIn() {
  const { token } = useParams();
  const [info, setInfo] = useState(null);
  const [err, setErr] = useState("");
  const [kind, setKind] = useState("member");
  const [ident, setIdent] = useState(() => localStorage.getItem("gb-checkin-id") || "");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => { api.get(`/public/checkin/${token}`).then(({ data }) => setInfo(data)).catch((e) => setErr(apiError(e))); }, [token]);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      const { data } = await api.post(`/public/checkin/${token}`, { kind, identifier: ident });
      localStorage.setItem("gb-checkin-id", ident);
      setResult(data);
    } catch (e2) { setErr(apiError(e2)); } finally { setBusy(false); }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-5 py-10" data-testid="checkin-page">
      <div className="w-full max-w-sm">
        <div className="text-center">
          <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-brand text-white"><Dumbbell className="h-7 w-7" /></span>
          <h1 className="mt-4 font-display text-2xl font-extrabold text-foreground" data-testid="checkin-gym">{info?.gym_name || (err ? "Check-in" : "Loading…")}</h1>
          {info && <p className="text-sm text-muted-foreground">{info.outlet_name}{info.city ? `, ${info.city}` : ""}</p>}
        </div>

        {result ? (
          <div className="mt-8 rounded-3xl border border-border bg-card p-7 text-center shadow-card" data-testid="checkin-result">
            {result.action === "out" ? <LogOut className="mx-auto h-14 w-14 text-brand" /> : <CheckCircle2 className="mx-auto h-14 w-14 text-success" />}
            <p className="mt-4 font-display text-xl font-bold text-foreground">{result.action === "out" ? "Punched Out" : result.action === "in" ? "Punched In" : "Already In"}</p>
            <p className="mt-1 text-sm text-muted-foreground" data-testid="checkin-result-message">{result.message}</p>
            <button onClick={() => setResult(null)} className="mt-6 h-12 w-full rounded-2xl border border-border text-sm font-semibold text-foreground" data-testid="checkin-done">Done</button>
          </div>
        ) : info ? (
          <form onSubmit={submit} className="mt-8 space-y-4 rounded-3xl border border-border bg-card p-6 shadow-card">
            <div className="grid grid-cols-2 gap-1 rounded-2xl bg-secondary p-1">
              {[["member", "Member"], ["staff", "Staff"]].map(([v, l]) => (
                <button type="button" key={v} onClick={() => { setKind(v); setErr(""); }} data-testid={`checkin-kind-${v}`}
                  className={`h-10 rounded-xl text-sm font-semibold transition-colors ${kind === v ? "bg-card text-foreground shadow" : "text-muted-foreground"}`}>{l}</button>
              ))}
            </div>
            <label className="block">
              <span className="mb-1.5 block text-sm font-semibold text-foreground">{kind === "member" ? "Member ID or phone number" : "Phone number or email"}</span>
              <input value={ident} onChange={(e) => setIdent(e.target.value)} required autoFocus data-testid="checkin-identifier"
                placeholder={kind === "member" ? "e.g. IPF-1001 or 98765 43210" : "e.g. 98765 43210"}
                className="h-13 w-full rounded-xl border border-input bg-background px-4 py-3 text-base text-foreground outline-none focus:border-brand" />
            </label>
            {err && <p className="flex items-start gap-1.5 text-sm text-danger" data-testid="checkin-error"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />{err}</p>}
            <button disabled={busy} className="flex h-13 w-full items-center justify-center gap-2 rounded-2xl bg-brand py-3.5 text-base font-semibold text-white disabled:opacity-60" data-testid="checkin-submit">
              {busy && <Loader2 className="h-4 w-4 animate-spin" />}Punch In / Out
            </button>
            <p className="text-center text-xs text-muted-foreground">First scan of the day punches you in. Scan again when you leave.</p>
          </form>
        ) : err ? (
          <p className="mt-8 rounded-2xl border border-danger/30 bg-danger/10 p-4 text-center text-sm text-danger" data-testid="checkin-invalid">{err}</p>
        ) : null}
        <p className="mt-8 text-center text-[11px] text-muted-foreground">Powered by GymBoss_VVO</p>
      </div>
    </div>
  );
}
