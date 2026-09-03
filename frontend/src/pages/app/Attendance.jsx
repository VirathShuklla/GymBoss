import { useEffect, useState } from "react";
import { ClipboardCheck, LogIn, LogOut } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { useAuth } from "../../contexts/AuthContext";
import { PageHeader, DataTable, EmptyState, MemberPicker } from "../../components/app/ui";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { Button } from "../../components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";

const fmtTime = (iso) => (iso ? new Date(iso).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }) : "—");

export default function Attendance() {
  const { outlets } = useAuth();
  const [selected, setSelected] = useState(null);
  const [todayList, setTodayList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [history, setHistory] = useState(null);
  const [outletId, setOutletId] = useState("all");
  const [month, setMonth] = useState(new Date().getMonth() + 1);

  const loadToday = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/attendance", { params: { outlet_id: outletId === "all" ? undefined : outletId } });
      setTodayList(data);
    } finally {
      setLoading(false);
    }
  };
  const loadHistory = async () => {
    const { data } = await api.get("/attendance/history", { params: { month } });
    setHistory(data);
  };
  useEffect(() => { loadToday(); }, [outletId]);
  useEffect(() => { loadHistory(); }, [month]);

  const checkIn = async () => {
    try {
      await api.post("/attendance/check-in", { member_id: selected.id });
      toast.success(`${selected.full_name} checked in`);
      setSelected(null);
      loadToday();
    } catch (e) {
      toast.error(apiError(e));
    }
  };

  const checkOut = async (id) => {
    try {
      await api.post(`/attendance/${id}/check-out`);
      toast.success("Checked out");
      loadToday();
    } catch (e) {
      toast.error(apiError(e));
    }
  };

  const todayColumns = [
    { key: "member", label: "Member", render: (a) => (
      <div><p className="font-medium text-foreground">{a.member_name}</p><p className="font-num text-xs text-muted-foreground">{a.member_code}</p></div>
    )},
    { key: "check_in", label: "Check-In", render: (a) => <span className="font-num text-foreground">{fmtTime(a.check_in)}</span> },
    { key: "check_out", label: "Check-Out", render: (a) => <span className="font-num text-muted-foreground">{fmtTime(a.check_out)}</span> },
    { key: "actions", label: "", align: "right", render: (a) => (
      !a.check_out && (
        <Button size="sm" variant="outline" onClick={() => checkOut(a.id)} data-testid={`checkout-${a.id}`}>
          <LogOut className="mr-1.5 h-3.5 w-3.5" />Check Out
        </Button>
      )
    )},
  ];

  const historyColumns = [
    { key: "date", label: "Date", render: (d) => <span className="font-num text-foreground">{d.date}</span> },
    { key: "count", label: "Check-Ins", align: "right", render: (d) => <span className="font-num font-bold text-foreground">{d.count}</span> },
  ];

  return (
    <div data-testid="attendance-page">
      <PageHeader title="Attendance" subtitle="Member check-ins and attendance history." testid="attendance-header" />
      <Tabs defaultValue="today">
        <TabsList className="mb-5">
          <TabsTrigger value="today" data-testid="tab-today">Today</TabsTrigger>
          <TabsTrigger value="history" data-testid="tab-history">History</TabsTrigger>
        </TabsList>
        <TabsContent value="today">
          <div className="mb-5 rounded-xl border border-border bg-card p-5 shadow-card" data-testid="checkin-card">
            <p className="mb-3 font-display text-sm font-bold text-foreground">Check In Member</p>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
              <div className="flex-1"><MemberPicker selected={selected} onSelect={setSelected} testid="checkin-search" /></div>
              <Button className="bg-brand hover:bg-brand-hover" disabled={!selected} onClick={checkIn} data-testid="checkin-button">
                <LogIn className="mr-1.5 h-4 w-4" />Check In
              </Button>
            </div>
          </div>
          <div className="mb-4 flex items-center justify-between">
            <p className="text-sm text-muted-foreground" data-testid="today-count"><span className="font-num font-bold text-foreground">{todayList.length}</span> check-ins today</p>
            {outlets.length > 1 && (
              <Select value={outletId} onValueChange={setOutletId}>
                <SelectTrigger className="h-9 w-40" data-testid="attendance-outlet-filter"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Outlets</SelectItem>
                  {outlets.map((o) => <SelectItem key={o.id} value={o.id}>{o.name}</SelectItem>)}
                </SelectContent>
              </Select>
            )}
          </div>
          <DataTable testid="attendance-today-table" columns={todayColumns} rows={todayList} loading={loading}
                     empty={<EmptyState icon={ClipboardCheck} title="No check-ins yet today" description="Check in members as they arrive." testid="attendance-empty" />} />
        </TabsContent>
        <TabsContent value="history">
          <div className="mb-4">
            <Select value={String(month)} onValueChange={(v) => setMonth(Number(v))}>
              <SelectTrigger className="h-9 w-40" data-testid="history-month"><SelectValue /></SelectTrigger>
              <SelectContent>
                {["January","February","March","April","May","June","July","August","September","October","November","December"].map((m, i) => (
                  <SelectItem key={m} value={String(i + 1)}>{m}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DataTable testid="attendance-history-table" columns={historyColumns} rows={history?.daily || []} loading={!history} rowKey="date"
                     empty={<EmptyState icon={ClipboardCheck} title="No attendance this month" testid="history-empty" />} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
