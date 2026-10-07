import { useState } from "react";
import { ClipboardCheck, LogIn, LogOut, QrCode, Fingerprint, Users, UserCheck, Wifi, ChevronRight } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { PageHeader, DataTable, EmptyState, MemberPicker } from "../../components/app/ui";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { Button } from "../../components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { useAttendance } from "../../components/attendance/useAttendance";
import { AttendanceSheets } from "../../components/attendance/AttendanceSheets";
import { WebSheet } from "../../components/attendance/WebSheet";
import { useEffect } from "react";

const fmtTime = (iso) => (iso ? new Date(iso).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }) : "—");
export const SOURCE = { qr: "QR", biometric: "Biometric", manual: "Manual" };
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

function Stat({ icon: Icon, label, value, testid }) {
  return (
    <div className="rounded-xl border border-border bg-card p-4 shadow-card" data-testid={testid}>
      <div className="flex items-center justify-between"><p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</p><Icon className="h-4 w-4 text-brand" /></div>
      <p className="font-num mt-1 text-2xl font-extrabold text-foreground">{value ?? "—"}</p>
    </div>
  );
}

function MethodCard({ icon: Icon, title, desc, cta, onClick, testid, badge }) {
  return (
    <button onClick={onClick} data-testid={testid} className="group flex items-start gap-4 rounded-xl border border-border bg-card p-5 text-left shadow-card transition-colors hover:border-brand/40">
      <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-brand/12 text-brand"><Icon className="h-6 w-6" /></span>
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-2 font-display text-base font-bold text-foreground">{title}{badge}</span>
        <span className="mt-0.5 block text-sm text-muted-foreground">{desc}</span>
        <span className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-brand">{cta}<ChevronRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" /></span>
      </span>
    </button>
  );
}

export default function Attendance() {
  const [outletId, setOutletId] = useState("all");
  const data = useAttendance(outletId === "all" ? undefined : outletId);
  const { summary, today, staff, qr, reload } = data;
  const [sheet, setSheet] = useState(null);
  const [selected, setSelected] = useState(null);
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [history, setHistory] = useState(null);
  useEffect(() => { setHistory(null); api.get("/attendance/history", { params: { month } }).then(({ data }) => setHistory(data)); }, [month]);

  const checkIn = async () => {
    try { await api.post("/attendance/check-in", { member_id: selected.id }); toast.success(`${selected.full_name} checked in`); setSelected(null); reload(); }
    catch (e) { toast.error(apiError(e)); }
  };
  const checkOut = async (id) => {
    try { await api.post(`/attendance/${id}/check-out`); toast.success("Checked out"); reload(); } catch (e) { toast.error(apiError(e)); }
  };

  const memberCols = [
    { key: "member", label: "Member", render: (a) => <div><p className="font-medium text-foreground">{a.member_name}</p><p className="font-num text-xs text-muted-foreground">{a.member_code}</p></div> },
    { key: "source", label: "Method", render: (a) => <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs font-semibold text-foreground">{SOURCE[a.source] || "Manual"}</span> },
    { key: "check_in", label: "Punch In", render: (a) => <span className="font-num text-foreground">{fmtTime(a.check_in)}</span> },
    { key: "check_out", label: "Punch Out", render: (a) => <span className="font-num text-muted-foreground">{fmtTime(a.check_out)}</span> },
    { key: "actions", label: "", align: "right", render: (a) => !a.check_out && (
      <Button size="sm" variant="outline" onClick={() => checkOut(a.id)} data-testid={`checkout-${a.id}`}><LogOut className="mr-1.5 h-3.5 w-3.5" />Check Out</Button>
    ) },
  ];
  const staffCols = [
    { key: "name", label: "Staff", render: (s) => <div><p className="font-medium text-foreground">{s.staff_name}</p><p className="text-xs capitalize text-muted-foreground">{s.role}</p></div> },
    { key: "check_in", label: "Punch In", render: (s) => <span className="font-num text-foreground">{fmtTime(s.check_in)}</span> },
    { key: "check_out", label: "Punch Out", render: (s) => <span className="font-num text-muted-foreground">{fmtTime(s.check_out)}</span> },
  ];
  const histCols = [
    { key: "date", label: "Date", render: (d) => <span className="font-num text-foreground">{d.date}</span> },
    { key: "count", label: "Check-Ins", align: "right", render: (d) => <span className="font-num font-bold text-foreground">{d.count}</span> },
  ];

  return (
    <div data-testid="attendance-page">
      <PageHeader title="Attendance" subtitle="Members check in by scanning a QR code, a fingerprint machine, or you mark them here." testid="attendance-header" />

      <div className="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat icon={ClipboardCheck} label="Check-ins today" value={summary?.today} testid="att-stat-today" />
        <Stat icon={UserCheck} label="Inside now" value={summary?.inside_now} testid="att-stat-inside" />
        <Stat icon={Users} label="Staff today" value={summary?.staff_today} testid="att-stat-staff" />
        <Stat icon={Wifi} label="Devices online" value={summary ? `${summary.devices_online}/${summary.devices}` : null} testid="att-stat-devices" />
      </div>

      <div className="mb-6 grid gap-4 lg:grid-cols-3">
        <MethodCard icon={QrCode} title="QR Check-in" desc="Print one QR at your entrance. Members scan it with their phone. No app or hardware needed." cta="Show QR code" onClick={() => setSheet("qr")} testid="att-open-qr" />
        <MethodCard icon={Fingerprint} title="Biometric" desc="Connect an eSSL / ZKTeco fingerprint machine. Punches arrive here automatically." cta="Manage devices" onClick={() => setSheet("bio")} testid="att-open-bio"
          badge={summary?.devices ? <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${summary.devices_online ? "bg-success/15 text-success" : "bg-secondary text-muted-foreground"}`}>{summary.devices_online ? "Online" : "Offline"}</span> : null} />
        <div className="rounded-xl border border-border bg-card p-5 shadow-card" data-testid="checkin-card">
          <p className="font-display text-base font-bold text-foreground">Manual check-in</p>
          <p className="mb-3 text-sm text-muted-foreground">Search a member and check them in.</p>
          <MemberPicker selected={selected} onSelect={setSelected} testid="checkin-search" />
          <Button className="mt-3 w-full bg-brand hover:bg-brand-hover" disabled={!selected} onClick={checkIn} data-testid="checkin-button"><LogIn className="mr-1.5 h-4 w-4" />Check In</Button>
        </div>
      </div>

      <Tabs defaultValue="today">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <TabsList>
            <TabsTrigger value="today" data-testid="tab-today">Members today</TabsTrigger>
            <TabsTrigger value="staff" data-testid="tab-staff">Staff today</TabsTrigger>
            <TabsTrigger value="history" data-testid="tab-history">History</TabsTrigger>
          </TabsList>
          {qr?.outlets?.length > 1 && (
            <Select value={outletId} onValueChange={setOutletId}>
              <SelectTrigger className="h-9 w-40" data-testid="attendance-outlet-filter"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Outlets</SelectItem>
                {qr.outlets.map((o) => <SelectItem key={o.outlet_id} value={o.outlet_id}>{o.outlet_name}</SelectItem>)}
              </SelectContent>
            </Select>
          )}
        </div>
        <TabsContent value="today">
          <DataTable testid="attendance-today-table" columns={memberCols} rows={today || []} loading={!today}
            empty={<EmptyState icon={ClipboardCheck} title="No check-ins yet today" description="Share your QR code or connect a device to start." testid="attendance-empty" />} />
        </TabsContent>
        <TabsContent value="staff">
          <DataTable testid="attendance-staff-table" columns={staffCols} rows={staff || []} loading={!staff}
            empty={<EmptyState icon={Users} title="No staff check-ins today" description="Staff scan the same QR and choose the Staff tab." testid="attendance-staff-empty" />} />
        </TabsContent>
        <TabsContent value="history">
          <div className="mb-4">
            <Select value={String(month)} onValueChange={(v) => setMonth(Number(v))}>
              <SelectTrigger className="h-9 w-40" data-testid="history-month"><SelectValue /></SelectTrigger>
              <SelectContent>{MONTHS.map((m, i) => <SelectItem key={m} value={String(i + 1)}>{m}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <DataTable testid="attendance-history-table" columns={histCols} rows={history?.daily || []} loading={!history} rowKey="date"
            empty={<EmptyState icon={ClipboardCheck} title="No attendance this month" testid="history-empty" />} />
        </TabsContent>
      </Tabs>

      <AttendanceSheets Sheet={WebSheet} sheet={sheet} setSheet={setSheet} data={data} />
    </div>
  );
}
