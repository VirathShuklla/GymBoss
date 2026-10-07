import { useState } from "react";
import { QrCode, Fingerprint, LogIn, LogOut, ChevronRight, ClipboardCheck } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { BottomSheet, EmptyRow, ListSkeleton, Seg } from "../ui";
import { MemberPicker } from "../../components/app/ui";
import { useAttendance } from "../../components/attendance/useAttendance";
import { AttendanceSheets } from "../../components/attendance/AttendanceSheets";

const fmtTime = (iso) => (iso ? new Date(iso).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }) : "—");
const SOURCE = { qr: "QR", biometric: "Fingerprint", manual: "Manual" };

function Tile({ icon: Icon, title, desc, onClick, testid, dot }) {
  return (
    <button onClick={onClick} data-testid={testid} className="flex flex-col items-start gap-3 rounded-3xl border border-border bg-card p-4 text-left active:scale-[0.98]">
      <span className="relative flex h-11 w-11 items-center justify-center rounded-2xl bg-brand/10 text-brand">
        <Icon className="h-6 w-6" />
        {dot && <span className={`absolute -right-0.5 -top-0.5 h-3 w-3 rounded-full border-2 border-card ${dot}`} />}
      </span>
      <span><span className="block text-[15px] font-bold text-foreground">{title}</span><span className="block text-xs leading-snug text-muted-foreground">{desc}</span></span>
    </button>
  );
}

function Visit({ name, sub, a, onOut }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-border bg-card px-4 py-3">
      <span className={`flex h-10 w-10 items-center justify-center rounded-full ${a.check_out ? "bg-secondary text-muted-foreground" : "bg-success/12 text-success"}`}>
        {a.check_out ? <LogOut className="h-5 w-5" /> : <LogIn className="h-5 w-5" />}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-foreground">{name}</p>
        <p className="text-xs text-muted-foreground">{sub} · In {fmtTime(a.check_in)}{a.check_out ? ` · Out ${fmtTime(a.check_out)}` : ""}</p>
      </div>
      {onOut && !a.check_out && (
        <button onClick={() => onOut(a.id)} data-testid={`m-att-out-${a.id}`} className="rounded-xl border border-border px-3 py-1.5 text-xs font-semibold text-foreground">Out</button>
      )}
    </div>
  );
}

export default function Attendance() {
  const data = useAttendance();
  const { summary, today, staff, reload } = data;
  const [sheet, setSheet] = useState(null);
  const [seg, setSeg] = useState("members");
  const [member, setMember] = useState(null);
  const [busy, setBusy] = useState(false);

  const checkIn = async () => {
    setBusy(true);
    try { await api.post("/attendance/check-in", { member_id: member.id }); toast.success(`${member.full_name} checked in`); setMember(null); setSheet(null); reload(); }
    catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };
  const checkOut = async (id) => {
    try { await api.post(`/attendance/${id}/check-out`); toast.success("Checked out"); reload(); } catch (e) { toast.error(apiError(e)); }
  };
  const devDot = summary?.devices ? (summary.devices_online ? "bg-success" : "bg-warning") : null;
  const list = seg === "members" ? today : staff;

  return (
    <div className="m-anim" data-testid="m-attendance">
      <h1 className="font-display text-2xl font-extrabold tracking-tight text-foreground">Attendance</h1>
      <p className="text-sm text-muted-foreground">{new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" })}</p>

      <div className="mt-4 rounded-3xl bg-gradient-to-br from-brand to-[#5B21B6] p-5 text-white shadow-xl shadow-brand/25" data-testid="m-att-hero">
        <p className="text-xs font-semibold uppercase tracking-wider opacity-80">Inside the gym now</p>
        <p className="font-num mt-1 text-5xl font-extrabold" data-testid="m-att-inside">{summary?.inside_now ?? "—"}</p>
        <div className="mt-4 grid grid-cols-3 gap-2 text-center">
          {[["Today", summary?.today], ["Staff", summary?.staff_today], ["Devices", summary ? `${summary.devices_online}/${summary.devices}` : "—"]].map(([l, v]) => (
            <div key={l} className="rounded-2xl bg-white/15 py-2"><p className="text-[11px] opacity-80">{l}</p><p className="font-num text-base font-bold">{v ?? "—"}</p></div>
          ))}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <Tile icon={QrCode} title="QR Check-in" desc="Show or share your gym's QR" onClick={() => setSheet("qr")} testid="m-att-qr" />
        <Tile icon={Fingerprint} title="Biometric" desc="Fingerprint machines" onClick={() => setSheet("bio")} testid="m-att-bio" dot={devDot} />
      </div>
      <button onClick={() => setSheet("manual")} data-testid="m-att-manual"
        className="mt-3 flex w-full items-center gap-3 rounded-2xl border border-border bg-card px-4 py-3.5 text-left active:scale-[0.99]">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-success/12 text-success"><LogIn className="h-5 w-5" /></span>
        <span className="flex-1"><span className="block text-sm font-bold text-foreground">Check in a member</span><span className="block text-xs text-muted-foreground">Mark attendance yourself</span></span>
        <ChevronRight className="h-4 w-4 text-muted-foreground" />
      </button>

      <div className="mb-3 mt-6"><Seg tabs={[{ value: "members", label: `Members (${today?.length ?? 0})` }, { value: "staff", label: `Staff (${staff?.length ?? 0})` }]} value={seg} onChange={setSeg} /></div>
      {!list ? <ListSkeleton rows={3} /> : list.length === 0 ? (
        <EmptyRow icon={ClipboardCheck} title={seg === "members" ? "No check-ins yet today" : "No staff check-ins today"} subtitle="Share your QR code or connect a fingerprint device to get started." testid="m-att-empty" />
      ) : (
        <div className="space-y-2.5" data-testid="m-att-list">
          {list.map((a) => seg === "members"
            ? <Visit key={a.id} a={a} name={a.member_name} sub={`${a.member_code} · ${SOURCE[a.source] || "Manual"}`} onOut={checkOut} />
            : <Visit key={a.id} a={a} name={a.staff_name} sub={a.role || "staff"} />)}
        </div>
      )}

      <BottomSheet open={sheet === "manual"} onOpenChange={(o) => !o && setSheet(null)} title="Check in a member" subtitle="Search by name, phone or member ID" testid="m-att-manual-sheet">
        <MemberPicker selected={member} onSelect={setMember} testid="m-att-member" />
        <button disabled={!member || busy} onClick={checkIn} data-testid="m-att-checkin-submit"
          className="flex h-[52px] w-full items-center justify-center gap-2 rounded-2xl bg-brand text-[15px] font-semibold text-white disabled:opacity-50">Check In</button>
      </BottomSheet>
      <AttendanceSheets Sheet={BottomSheet} sheet={sheet} setSheet={setSheet} data={data} />
    </div>
  );
}
