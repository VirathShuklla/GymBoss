// Mobile Reports screen: 6-month revenue trend (simple bars), outstanding dues list,
// upcoming membership expiries, and enquiry-conversion stats. Reads /reports/* endpoints.
import { useEffect, useState } from "react";
import api from "../../lib/api";
import { inr } from "../../lib/format";
import { ListSkeleton } from "../ui";
import { MonthlyReportButton } from "../../components/app/MonthlyReportButton";

const more = async (path, prev, setter, extra = {}) => {
  const page = (prev?.page || 0) + 1;
  const { data } = await api.get(path, { params: { ...extra, page, limit: 50 } });
  setter({ ...data, items: page === 1 ? data.items : [...prev.items, ...data.items] });
};

export default function Reports() {
  const [trend, setTrend] = useState(null);
  const [dues, setDues] = useState(null);
  const [expiry, setExpiry] = useState(null);
  const [conv, setConv] = useState(null);

  useEffect(() => {
    api.get("/reports/revenue-trend?months=6").then(({ data }) => setTrend(data.points)).catch(() => setTrend([]));
    more("/reports/outstanding-dues", null, setDues).catch(() => setDues({ items: [], total: 0, count: 0 }));
    more("/reports/membership-expiry", null, setExpiry, { days: 30 }).catch(() => setExpiry({ items: [], count: 0 }));
    api.get("/reports/enquiry-conversion").then(({ data }) => setConv(data)).catch(() => setConv(null));
  }, []);

  const maxRev = trend ? Math.max(...trend.map((x) => x.revenue), 1) : 1;

  return (
    <div data-testid="m-reports" className="space-y-6">
      <Section title="Monthly finance report">
        <MonthlyReportButton testid="m-monthly-report" compact />
      </Section>
      <Section title="Revenue Trend (6 months)">
        {!trend ? <ListSkeleton rows={3} /> : (
          <div className="rounded-2xl border border-border bg-card p-4" data-testid="m-reports-trend">
            {trend.map((p) => (
              <div key={p.month} className="py-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">{p.month}</span>
                  <span className="font-num font-bold text-foreground">{inr(p.revenue)}</span>
                </div>
                <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-secondary">
                  <div className="h-full rounded-full bg-brand" style={{ width: `${Math.round((100 * p.revenue) / maxRev)}%` }} />
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title={`Outstanding Dues${dues ? ` · ${inr(dues.total)}` : ""}`}>
        {!dues ? <ListSkeleton rows={3} /> : dues.items.length === 0 ? <Empty text="No outstanding dues" /> : (
          <div className="space-y-2" data-testid="m-reports-dues">
            {dues.items.map((m) => (
              <Row key={m.id} a={m.full_name} b={m.member_code} c={inr(m.due_amount)} cls="text-danger" />
            ))}
            <More data={dues} onMore={() => more("/reports/outstanding-dues", dues, setDues)} testid="m-dues-more" />
          </div>
        )}
      </Section>

      <Section title="Expiring in 30 days">
        {!expiry ? <ListSkeleton rows={3} /> : expiry.items.length === 0 ? <Empty text="No upcoming expiries" /> : (
          <div className="space-y-2" data-testid="m-reports-expiry">
            {expiry.items.map((m) => (
              <Row key={m.id} a={m.full_name} b={m.plan_name} c={`${m.days_left}d`} cls={m.days_left <= 7 ? "text-warning" : "text-foreground"} />
            ))}
            <More data={expiry} onMore={() => more("/reports/membership-expiry", expiry, setExpiry, { days: 30 })} testid="m-expiry-more" />
          </div>
        )}
      </Section>

      <Section title="Enquiry Conversion">
        {!conv ? <ListSkeleton rows={2} /> : (
          <div className="rounded-2xl border border-border bg-card p-4" data-testid="m-reports-conversion">
            <Stat label="Total leads" value={conv.total} cls="text-foreground" />
            <Stat label="Converted" value={conv.converted} cls="text-success" />
            <Stat label="Conversion rate" value={`${conv.rate}%`} cls="text-brand" />
          </div>
        )}
      </Section>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div>
      <h2 className="mb-2 font-display text-sm font-bold uppercase tracking-wider text-muted-foreground">{title}</h2>
      {children}
    </div>
  );
}

function Row({ a, b, c, cls }) {
  return (
    <div className="flex items-center justify-between rounded-2xl border border-border bg-card px-4 py-3">
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-foreground">{a}</p>
        <p className="truncate text-xs text-muted-foreground">{b}</p>
      </div>
      <span className={`font-num text-sm font-bold ${cls}`}>{c}</span>
    </div>
  );
}

function Stat({ label, value, cls }) {
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className={`font-num font-bold ${cls}`}>{value}</span>
    </div>
  );
}

function More({ data, onMore, testid }) {
  const [busy, setBusy] = useState(false);
  if (!data?.count || data.items.length >= data.count) return null;
  return (
    <button disabled={busy} onClick={async () => { setBusy(true); try { await onMore(); } catch (e) { /* keep list */ } finally { setBusy(false); } }}
            className="w-full rounded-2xl border border-border py-3 text-sm font-semibold text-brand disabled:opacity-60" data-testid={testid}>
      {busy ? "Loading…" : `Load more (${data.items.length} of ${data.count})`}
    </button>
  );
}

function Empty({ text }) {
  return <div className="rounded-2xl border border-dashed border-border py-8 text-center text-sm text-muted-foreground">{text}</div>;
}
