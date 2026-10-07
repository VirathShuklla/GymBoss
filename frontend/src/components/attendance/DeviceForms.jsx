import { useEffect, useState } from "react";
import { ScanBarcode, Tag, Info, Mail, Loader2, CheckCircle2, Search } from "lucide-react";
import { toast } from "sonner";
import api, { apiError } from "../../lib/api";
import { MemberPicker } from "../app/ui";

const inputCls = "h-12 w-full rounded-xl border border-input bg-background pl-10 pr-3 text-[15px] text-foreground outline-none placeholder:text-muted-foreground focus:border-brand";
const btnCls = "flex h-12 w-full items-center justify-center gap-2 rounded-2xl bg-foreground text-sm font-semibold text-background active:scale-[0.98] disabled:opacity-50";

export function ConnectDeviceForm({ types, outlets, contactHref, onDone }) {
  const [form, setForm] = useState({ device_type: types?.[0] || "eSSL X990", serial_number: "", name: "", outlet_id: outlets?.[0]?.id });
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/attendance/devices", form);
      toast.success(`${form.name} connected. It will show Online once the device reaches our server.`);
      onDone();
    } catch (err) { toast.error(apiError(err)); } finally { setBusy(false); }
  };
  return (
    <form onSubmit={submit} className="space-y-4" data-testid="att-connect-form">
      <div>
        <p className="mb-2 text-sm font-bold text-foreground">Device type</p>
        <div className="flex flex-wrap gap-2">
          {(types || []).map((t) => (
            <button type="button" key={t} onClick={() => setForm({ ...form, device_type: t })} data-testid={`att-type-${t.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}`}
              className={`rounded-full border px-3.5 py-2 text-sm font-medium transition-colors ${form.device_type === t ? "border-foreground bg-foreground text-background" : "border-border text-foreground"}`}>{t}</button>
          ))}
        </div>
      </div>
      <label className="block">
        <span className="mb-1.5 block text-sm font-bold text-foreground">Serial number</span>
        <span className="relative block"><ScanBarcode className="absolute left-3 top-3.5 h-5 w-5 text-muted-foreground" />
          <input required value={form.serial_number} onChange={(e) => setForm({ ...form, serial_number: e.target.value.toUpperCase() })} placeholder="e.g. CQZ7235160012" className={`${inputCls} font-num`} data-testid="att-connect-serial" /></span>
        <span className="mt-1.5 flex gap-1.5 text-[12px] text-muted-foreground"><Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />Printed on the back of the device, or Menu → System Info → Device Info → Serial Number.</span>
      </label>
      <label className="block">
        <span className="mb-1.5 block text-sm font-bold text-foreground">Device name</span>
        <span className="relative block"><Tag className="absolute left-3 top-3.5 h-5 w-5 text-muted-foreground" />
          <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Front Desk" className={inputCls} data-testid="att-connect-name" /></span>
      </label>
      {outlets?.length > 1 && (
        <div>
          <p className="mb-2 text-sm font-bold text-foreground">Outlet</p>
          <div className="flex flex-wrap gap-2">
            {outlets.map((o) => (
              <button type="button" key={o.id} onClick={() => setForm({ ...form, outlet_id: o.id })} data-testid={`att-connect-outlet-${o.id}`}
                className={`rounded-full border px-3.5 py-2 text-sm font-medium ${form.outlet_id === o.id ? "border-foreground bg-foreground text-background" : "border-border text-foreground"}`}>{o.name}</button>
            ))}
          </div>
        </div>
      )}
      <button disabled={busy} className={btnCls} data-testid="att-connect-submit">{busy && <Loader2 className="h-4 w-4 animate-spin" />}Connect</button>
      {contactHref && <a href={contactHref} target="_blank" rel="noopener noreferrer" className="flex items-center justify-center gap-1.5 text-sm text-muted-foreground"><Mail className="h-4 w-4" />Need help? Contact us</a>}
    </form>
  );
}

function DeviceIdList() {
  const [rows, setRows] = useState(null);
  const [q, setQ] = useState("");
  useEffect(() => { api.get("/attendance/device-ids").then(({ data }) => setRows(data)).catch(() => setRows([])); }, []);
  const list = (rows || []).filter((r) => `${r.full_name} ${r.member_code}`.toLowerCase().includes(q.toLowerCase()));
  return (
    <div className="rounded-2xl border border-border" data-testid="att-device-ids">
      <div className="relative border-b border-border p-2"><Search className="absolute left-4 top-4 h-4 w-4 text-muted-foreground" />
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search member" className="h-9 w-full rounded-lg bg-secondary pl-8 pr-2 text-sm text-foreground outline-none" data-testid="att-device-ids-search" /></div>
      <div className="max-h-48 overflow-y-auto">
        {!rows ? <p className="p-3 text-xs text-muted-foreground">Loading…</p> : list.slice(0, 100).map((r) => (
          <div key={r.member_id} className="flex justify-between border-b border-border px-3 py-2 text-sm last:border-0">
            <span className="truncate text-foreground">{r.full_name} <span className="text-xs text-muted-foreground">{r.member_code}</span></span>
            <span className="font-num font-bold text-brand">{r.device_user_id}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function SetupGuide() {
  const host = new URL(process.env.REACT_APP_BACKEND_URL).host;
  const steps = [
    ["Add the device here", "Tap Connect a Device and enter its serial number and a name like Front Desk."],
    ["Connect it to the internet", "On the device: Menu → COMM → Ethernet (LAN cable) or Wi-Fi. Make sure it has internet."],
    ["Point it to GymBoss_VVO", <>Menu → COMM → <b>Cloud Server Setting</b> (called ADMS on some models). Turn on <b>Enable Domain Name</b>, set Server Address to <b className="font-num break-all text-foreground">{host}</b>, Port <b>443</b> with HTTPS on (use port 80 if your model has no HTTPS option). Keep proxy off and save.</>],
    ["Enrol your members", "Menu → User Mgt → New User. Set the User ID to the number in the member's code (IPF-1001 becomes 1001), then scan their finger. The full list is below."],
    ["You're live", "Within 1–2 minutes the device shows Online here, and every fingerprint scan appears in today's attendance. The first scan of the day is Punch In, the next is Punch Out."],
  ];
  return (
    <div className="space-y-4" data-testid="att-setup-guide">
      <ol className="space-y-3">
        {steps.map(([t, d], i) => (
          <li key={i} className="flex gap-3">
            <span className="font-num flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand text-xs font-bold text-white">{i + 1}</span>
            <div><p className="text-sm font-bold text-foreground">{t}</p><p className="text-[13px] leading-relaxed text-muted-foreground">{d}</p></div>
          </li>
        ))}
      </ol>
      <p className="text-sm font-bold text-foreground">Member device IDs</p>
      <DeviceIdList />
      <p className="rounded-xl bg-secondary/60 p-3 text-xs text-muted-foreground">No machine yet? Use <b>Test punch</b> on a connected device to see exactly how a fingerprint scan shows up.</p>
    </div>
  );
}

export function SupportedDevices({ types }) {
  return (
    <div className="space-y-2" data-testid="att-supported-list">
      {(types || []).map((t) => (
        <div key={t} className="flex items-center gap-2.5 rounded-xl border border-border px-4 py-3 text-sm font-medium text-foreground">
          <CheckCircle2 className="h-4 w-4 text-success" />{t}
        </div>
      ))}
      <p className="pt-1 text-xs text-muted-foreground">Any eSSL or ZKTeco machine with ADMS / Cloud Server (push) support works. If you're not sure about yours, contact us with the model name.</p>
    </div>
  );
}

export function TestPunchForm({ device, onDone }) {
  const [member, setMember] = useState(null);
  const [busy, setBusy] = useState(false);
  const run = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/attendance/devices/${device.id}/test-punch`, { member_id: member.id });
      const msg = { in: "punched in", out: "punched out", duplicate: "already punched in a moment ago" }[data.action];
      toast.success(`${data.member_name} ${msg} via ${device.name}`);
      onDone();
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };
  return (
    <div className="space-y-4" data-testid="att-test-punch">
      <p className="text-sm text-muted-foreground">Pick a member. We'll record a fingerprint scan exactly as if it came from this device.</p>
      <MemberPicker selected={member} onSelect={setMember} testid="att-test-member" />
      <button disabled={!member || busy} onClick={run} className={btnCls} data-testid="att-test-submit">{busy && <Loader2 className="h-4 w-4 animate-spin" />}Simulate fingerprint scan</button>
    </div>
  );
}
