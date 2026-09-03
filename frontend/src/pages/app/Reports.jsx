import { useEffect, useState } from "react";
import { BarChart3, AlertCircle, CalendarClock, ArrowRightLeft } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";
import api from "../../lib/api";
import { inr, formatDate, formatPhone } from "../../lib/format";
import { PageHeader, DataTable, EmptyState } from "../../components/app/ui";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";

export default function Reports() {
  const [trend, setTrend] = useState(null);
  const [dues, setDues] = useState(null);
  const [expiry, setExpiry] = useState(null);
  const [conversion, setConversion] = useState(null);
  const [growth, setGrowth] = useState(null);

  useEffect(() => {
    api.get("/reports/revenue-trend").then(({ data }) => setTrend(data.points));
    api.get("/reports/outstanding-dues").then(({ data }) => setDues(data));
    api.get("/reports/membership-expiry", { params: { days: 30 } }).then(({ data }) => setExpiry(data.items));
    api.get("/reports/enquiry-conversion").then(({ data }) => setConversion(data));
    api.get("/reports/member-growth").then(({ data }) => setGrowth(data.points));
  }, []);

  const duesColumns = [
    { key: "full_name", label: "Member", render: (m) => (
      <div><p className="font-medium text-foreground">{m.full_name}</p><p className="font-num text-xs text-muted-foreground">{m.member_code}</p></div>
    )},
    { key: "phone", label: "Phone", render: (m) => <span className="font-num text-muted-foreground">{formatPhone(m.phone)}</span> },
    { key: "plan_name", label: "Plan" },
    { key: "membership_expiry", label: "Expiry", render: (m) => formatDate(m.membership_expiry) },
    { key: "due_amount", label: "Due", align: "right", render: (m) => <span className="font-num font-bold text-danger">{inr(m.due_amount)}</span> },
  ];

  const expiryColumns = [
    { key: "full_name", label: "Member", render: (m) => <span className="font-medium text-foreground">{m.full_name}</span> },
    { key: "plan_name", label: "Plan" },
    { key: "membership_expiry", label: "Expiry Date", render: (m) => formatDate(m.membership_expiry) },
    { key: "days_left", label: "Days Left", align: "right", render: (m) => (
      <span className={`font-num font-bold ${m.days_left <= 3 ? "text-danger" : m.days_left <= 7 ? "text-warning" : "text-foreground"}`}>{m.days_left}</span>
    )},
  ];

  const chartStyle = { fontSize: 11, fontFamily: "JetBrains Mono" };

  return (
    <div data-testid="reports-page">
      <PageHeader title="Reports" subtitle="Understand your gym's performance." testid="reports-header" />
      <Tabs defaultValue="revenue">
        <TabsList className="mb-5 flex-wrap" data-testid="reports-tabs">
          <TabsTrigger value="revenue" data-testid="report-tab-revenue">Revenue</TabsTrigger>
          <TabsTrigger value="growth" data-testid="report-tab-growth">Member Growth</TabsTrigger>
          <TabsTrigger value="dues" data-testid="report-tab-dues">Outstanding Dues</TabsTrigger>
          <TabsTrigger value="expiry" data-testid="report-tab-expiry">Membership Expiry</TabsTrigger>
          <TabsTrigger value="enquiries" data-testid="report-tab-enquiries">Enquiry Conversion</TabsTrigger>
        </TabsList>

        <TabsContent value="revenue">
          <div className="rounded-xl border border-border bg-card p-5 shadow-card" data-testid="report-revenue-chart">
            <p className="mb-4 font-display text-sm font-bold text-foreground">Revenue vs Expenses — last 6 months</p>
            {trend && (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={trend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="month" tick={chartStyle} stroke="hsl(var(--muted-foreground))" />
                  <YAxis tick={chartStyle} stroke="hsl(var(--muted-foreground))" />
                  <Tooltip formatter={(v) => inr(v)} contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
                  <Legend />
                  <Bar dataKey="revenue" name="Revenue" fill="#7C3AED" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="expenses" name="Expenses" fill="#F59E0B" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </TabsContent>

        <TabsContent value="growth">
          <div className="rounded-xl border border-border bg-card p-5 shadow-card" data-testid="report-growth-chart">
            <p className="mb-4 font-display text-sm font-bold text-foreground">Member Growth — last 6 months</p>
            {growth && (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={growth}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="month" tick={chartStyle} stroke="hsl(var(--muted-foreground))" />
                  <YAxis tick={chartStyle} stroke="hsl(var(--muted-foreground))" />
                  <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
                  <Legend />
                  <Bar dataKey="joined" name="New Members" fill="#7C3AED" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="total" name="Total Members" fill="#10B981" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </TabsContent>

        <TabsContent value="dues">
          {dues && (
            <p className="mb-3 text-sm text-muted-foreground" data-testid="dues-total">
              Total outstanding: <span className="font-num font-bold text-danger">{inr(dues.total)}</span> across {dues.items.length} members
            </p>
          )}
          <DataTable testid="report-dues-table" columns={duesColumns} rows={dues?.items || []} loading={!dues}
                     empty={<EmptyState icon={AlertCircle} title="No outstanding dues" description="All members are settled up." testid="dues-empty" />} />
        </TabsContent>

        <TabsContent value="expiry">
          <p className="mb-3 text-sm text-muted-foreground">Memberships expiring in the next 30 days</p>
          <DataTable testid="report-expiry-table" columns={expiryColumns} rows={expiry || []} loading={!expiry}
                     empty={<EmptyState icon={CalendarClock} title="No upcoming expiries" testid="expiry-empty" />} />
        </TabsContent>

        <TabsContent value="enquiries">
          {conversion && (
            <div>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4" data-testid="conversion-cards">
                <Stat label="Total Enquiries" value={conversion.total} />
                <Stat label="Converted" value={conversion.converted} color="text-success" />
                <Stat label="Conversion Rate" value={`${conversion.rate}%`} color="text-brand" />
                <Stat label="Active Leads" value={conversion.total - conversion.converted - (conversion.by_status.Lost || 0)} color="text-warning" />
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <div className="rounded-xl border border-border bg-card p-5 shadow-card" data-testid="conversion-by-status">
                  <p className="mb-3 font-display text-sm font-bold text-foreground">By Status</p>
                  {Object.entries(conversion.by_status).map(([s, c]) => (
                    <div key={s} className="flex items-center justify-between py-1 text-sm">
                      <span className="text-muted-foreground">{s}</span>
                      <span className="font-num font-semibold text-foreground">{c}</span>
                    </div>
                  ))}
                </div>
                <div className="rounded-xl border border-border bg-card p-5 shadow-card" data-testid="conversion-by-source">
                  <p className="mb-3 font-display text-sm font-bold text-foreground">By Source</p>
                  {Object.entries(conversion.by_source).map(([s, c]) => (
                    <div key={s} className="flex items-center justify-between py-1 text-sm">
                      <span className="text-muted-foreground">{s}</span>
                      <span className="font-num font-semibold text-foreground">{c}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

function Stat({ label, value, color = "text-foreground" }) {
  return (
    <div className="rounded-xl border border-border bg-card p-4 shadow-card">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className={`font-num mt-1 text-xl font-bold ${color}`}>{value}</p>
    </div>
  );
}
