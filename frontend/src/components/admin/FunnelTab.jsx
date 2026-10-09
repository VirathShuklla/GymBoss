import { useEffect, useState } from "react";
import { Info, AlertCircle, Save, Loader2 } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { Button } from "../ui/button";
import { Input } from "../ui/input";

const pctText = (p) => (p == null ? "" : p > 100 ? "n/a" : `${p}%`);

function Box({ title, hint, children, testid, action }) {
  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-card" data-testid={testid}>
      <div className="mb-4 flex items-start justify-between gap-3">
        <div><p className="font-display text-base font-bold text-foreground">{title}</p>{hint && <p className="text-xs text-muted-foreground">{hint}</p>}</div>
        {action}
      </div>
      {children}
    </div>
  );
}

function Funnel({ stages }) {
  const top = Math.max(...stages.map((s) => s.count), 1);
  return (
    <div className="space-y-2.5" data-testid="funnel-stages">
      {stages.map((s, i) => (
        <div key={s.key} data-testid={`funnel-stage-${s.key}`}>
          <div className="flex items-baseline justify-between gap-3 text-sm">
            <p className="font-semibold text-foreground"><span className="mr-2 text-muted-foreground">{i + 1}.</span>{s.label}</p>
            <p className="shrink-0">
              <span className="font-num font-bold text-foreground" data-testid={`funnel-count-${s.key}`}>{s.count}</span>
              {i > 0 && <span className="ml-2 rounded-full bg-secondary px-2 py-0.5 text-xs font-semibold text-muted-foreground" data-testid={`funnel-pct-${s.key}`}>{pctText(s.from_previous)} of previous</span>}
            </p>
          </div>
          <div className="mt-1 h-2.5 overflow-hidden rounded-full bg-secondary">
            <div className="h-full rounded-full bg-brand transition-[width] duration-500" style={{ width: `${Math.max(2, (100 * s.count) / top)}%` }} />
          </div>
          <p className="mt-0.5 text-[11px] text-muted-foreground">{s.description}</p>
        </div>
      ))}
    </div>
  );
}

function Rules({ rules, onSaved }) {
  const [r, setR] = useState(rules);
  const [busy, setBusy] = useState(false);
  useEffect(() => setR(rules), [rules]);
  const save = async () => {
    setBusy(true);
    try { await api.put("/admin/settings", { activation_rules: { min_plans: +r.min_plans, min_members: +r.min_members, min_payments: +r.min_payments } }); toast.success("Activation rule updated"); onSaved(); }
    catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };
  const field = (k, label) => (
    <label className="block text-xs text-muted-foreground">{label}
      <Input type="number" min="0" max="100" value={r[k]} onChange={(e) => setR({ ...r, [k]: e.target.value })} className="mt-1" data-testid={`rule-${k}`} />
    </label>
  );
  return (
    <Box title="What counts as an Activated Trial?" hint="A trial gym is 'activated' once it has done all three of these." testid="activation-rules"
      action={<Button size="sm" onClick={save} disabled={busy} className="bg-brand hover:bg-brand-hover" data-testid="rules-save">{busy ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : <Save className="mr-1.5 h-3.5 w-3.5" />}Save</Button>}>
      <div className="grid grid-cols-3 gap-3">{field("min_plans", "Membership plans")}{field("min_members", "Members added")}{field("min_payments", "Payments recorded")}</div>
    </Box>
  );
}

export function FunnelTab() {
  const [days, setDays] = useState(30);
  const [d, setD] = useState(null);
  const load = () => api.get("/admin/funnel", { params: { days } }).then(({ data }) => setD(data)).catch(() => setD(null));
  useEffect(() => { setD(null); load(); }, [days]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="space-y-5" data-testid="funnel-tab">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="flex items-start gap-2 text-sm text-muted-foreground"><Info className="mt-0.5 h-4 w-4 shrink-0 text-brand" />Follow each step from first visit to paying customer. The % shows how many moved on from the step before.</p>
        <div className="flex gap-1 rounded-lg bg-secondary p-1">
          {[7, 30, 90].map((n) => (
            <button key={n} onClick={() => setDays(n)} data-testid={`funnel-range-${n}`}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold ${days === n ? "bg-card text-foreground shadow" : "text-muted-foreground"}`}>Last {n} days</button>
          ))}
        </div>
      </div>
      {!d ? <div className="h-96 animate-pulse rounded-xl bg-secondary" /> : (
        <>
          {d.funnel.some((s) => s.from_previous > 100) && (
            <p className="flex items-start gap-2 rounded-lg bg-warning/10 p-3 text-xs text-warning" data-testid="funnel-tracking-note">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />Visitor tracking started recently, so some gyms signed up before their visit was recorded. Percentages marked n/a will fix themselves as new data comes in.
            </p>
          )}
          <div className="grid gap-5 lg:grid-cols-5">
            <div className="lg:col-span-3"><Box title="Conversion Funnel" hint={`Last ${d.days} days`} testid="funnel-box"><Funnel stages={d.funnel} /></Box></div>
            <div className="space-y-5 lg:col-span-2">
              <Box title="Landing Page Clicks" hint="Unique people, and % of visitors" testid="funnel-cta">
                <div className="grid grid-cols-2 gap-3">
                  {[["hero_cta_click", "Start trial clicks"], ["demo_click", "Demo clicks"], ["pricing_viewed", "Saw pricing"], ["pricing_cta_click", "Pricing button clicks"]].map(([k, l]) => (
                    <div key={k} className="rounded-lg bg-secondary/60 p-3" data-testid={`cta-${k}`}>
                      <p className="text-xs text-muted-foreground">{l}</p>
                      <p className="font-num text-xl font-bold text-foreground">{d.cta[k].count}<span className="ml-1.5 text-xs font-medium text-muted-foreground">{pctText(d.cta[k].rate)}</span></p>
                    </div>
                  ))}
                </div>
              </Box>
              <Box title="Where Visitors Come From" hint="From UTM tags or the referring website" testid="funnel-sources">
                {d.sources.length === 0 ? <p className="text-sm text-muted-foreground">No visits recorded yet.</p> : d.sources.map((s) => (
                  <div key={s.source} className="flex justify-between border-b border-border py-2 text-sm last:border-0">
                    <span className="truncate text-foreground">{s.source}</span>
                    <span className="font-num text-muted-foreground">{s.visitors} visitors · {s.signups} signups</span>
                  </div>
                ))}
              </Box>
            </div>
          </div>
          <div className="grid gap-5 lg:grid-cols-2">
            <Box title="Trials That Need a Nudge" hint="Trial gyms that haven't activated yet, ending soonest first" testid="funnel-stuck">
              {d.stuck.length === 0 ? <p className="text-sm text-muted-foreground">Every trial gym is activated.</p> : (
                <div className="max-h-80 space-y-2 overflow-y-auto">
                  {d.stuck.map((g) => (
                    <div key={g.id} className="rounded-lg border border-border p-3 text-sm" data-testid={`stuck-${g.id}`}>
                      <div className="flex justify-between gap-2"><p className="font-semibold text-foreground">{g.name}</p><span className="shrink-0 text-xs font-semibold text-warning">{g.days_left} days left</span></div>
                      <p className="text-xs text-muted-foreground">{g.plans} plans · {g.members} members · {g.payments} payments · Still needs: {g.missing.join(", ")}</p>
                    </div>
                  ))}
                </div>
              )}
            </Box>
            <div className="space-y-5">
              <Rules rules={d.rules} onSaved={load} />
              <Box title="All Tracked Events" hint="Total times it happened, and unique gyms or visitors" testid="funnel-events">
                <div className="max-h-72 overflow-y-auto">
                  {d.events.map((e) => (
                    <div key={e.event} className="flex justify-between border-b border-border py-1.5 text-sm last:border-0" data-testid={`event-row-${e.event}`}>
                      <span className="text-foreground">{e.label}</span>
                      <span className="font-num text-muted-foreground">{e.count} <span className="text-xs">({e.unique} unique)</span></span>
                    </div>
                  ))}
                </div>
              </Box>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
