import { BookOpen, Cpu, Mail, ChevronRight, CheckCircle2, AlertCircle, Fingerprint, Trash2, Plus, Timer, RefreshCw, Zap } from "lucide-react";
import { Switch } from "../ui/switch";

function Row({ icon: Icon, title, desc, onClick, href, testid }) {
  const cls = "flex w-full items-center gap-3 rounded-2xl border border-border bg-background px-4 py-3.5 text-left transition-colors hover:bg-secondary/60 active:scale-[0.99]";
  const body = (
    <>
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-secondary text-foreground"><Icon className="h-5 w-5" /></span>
      <span className="min-w-0 flex-1"><span className="block text-sm font-bold text-foreground">{title}</span><span className="block text-xs text-muted-foreground">{desc}</span></span>
      <ChevronRight className="h-4 w-4 text-muted-foreground" />
    </>
  );
  return href
    ? <a href={href} target="_blank" rel="noopener noreferrer" className={cls} data-testid={testid}>{body}</a>
    : <button onClick={onClick} className={cls} data-testid={testid}>{body}</button>;
}

function Status({ devices }) {
  const online = devices.filter((d) => d.online).length;
  if (!devices.length) return (
    <div className="flex items-center gap-2 rounded-2xl border border-border bg-secondary/50 px-4 py-3 text-sm text-muted-foreground" data-testid="att-bio-status">
      <Fingerprint className="h-4 w-4" />No device connected yet. Tap Connect a Device to begin.
    </div>
  );
  return online ? (
    <div className="flex items-center gap-2 rounded-2xl border border-success/30 bg-success/10 px-4 py-3 text-sm font-semibold text-success" data-testid="att-bio-status">
      <CheckCircle2 className="h-4 w-4" />Biometric active: {online} of {devices.length} device(s) online
    </div>
  ) : (
    <div className="flex items-center gap-2 rounded-2xl border border-warning/30 bg-warning/10 px-4 py-3 text-sm font-semibold text-warning" data-testid="att-bio-status">
      <AlertCircle className="h-4 w-4" />Waiting for your device to come online. Follow the setup guide.
    </div>
  );
}

function DeviceCard({ d, onToggleAuto, onRemove, onTest }) {
  return (
    <div className="rounded-2xl border border-border bg-background p-4" data-testid={`att-device-${d.id}`}>
      <div className="flex items-start gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand/10 text-brand"><Fingerprint className="h-5 w-5" /></span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-bold text-foreground">{d.name}</p>
          <p className="font-num truncate text-xs text-muted-foreground">{d.serial_number} · {d.device_type}</p>
        </div>
        <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-bold ${d.online ? "bg-success/12 text-success" : "bg-secondary text-muted-foreground"}`} data-testid={`att-device-status-${d.id}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${d.online ? "bg-success" : "bg-muted-foreground/60"}`} />{d.online ? "Online" : "Offline"}
        </span>
      </div>
      <div className="mt-3 rounded-xl border border-border bg-secondary/40 p-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="flex items-center gap-1.5 text-sm font-bold text-foreground"><Timer className="h-4 w-4" />Auto delete access on expiry</p>
            <ul className="mt-1.5 list-disc space-y-0.5 pl-5 text-[12px] text-muted-foreground">
              <li>Expired members are removed from this device only.</li>
              <li>They stay in the app with all their history.</li>
              <li>Fingerprint access is blocked automatically.</li>
              <li>Re-enrol their fingerprint after renewal.</li>
            </ul>
          </div>
          <Switch checked={d.auto_delete_on_expiry} onCheckedChange={(v) => onToggleAuto(d, v)} data-testid={`att-device-auto-${d.id}`} />
        </div>
      </div>
      <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
        <span>{d.punches} punch(es) · {d.last_seen ? `last seen ${new Date(d.last_seen).toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" })}` : "never connected"}</span>
        <span className="flex gap-1">
          <button onClick={() => onTest(d)} data-testid={`att-device-test-${d.id}`} className="inline-flex items-center gap-1 rounded-lg bg-brand/10 px-2.5 py-1.5 font-semibold text-brand"><Zap className="h-3.5 w-3.5" />Test punch</button>
          <button onClick={() => onRemove(d)} data-testid={`att-device-remove-${d.id}`} aria-label="Remove device" className="rounded-lg p-1.5 text-danger hover:bg-danger/10"><Trash2 className="h-4 w-4" /></button>
        </span>
      </div>
    </div>
  );
}

export function BiometricPanel({ devices, onOpen, onToggleAuto, onRemove, onTest, onRefresh, contactHref }) {
  if (!devices) return <div className="h-72 animate-pulse rounded-2xl bg-secondary" />;
  return (
    <div className="space-y-3" data-testid="att-bio-panel">
      <Row icon={BookOpen} title="View Setup Guide" desc="Step-by-step device connection" onClick={() => onOpen("guide")} testid="att-bio-guide" />
      <Row icon={Cpu} title="Supported Devices" desc="eSSL and ZKTeco machines that work" onClick={() => onOpen("supported")} testid="att-bio-supported" />
      {contactHref && <Row icon={Mail} title="Contact Us" desc="Need help? Our team will set it up with you" href={contactHref} testid="att-bio-contact" />}
      <Status devices={devices} />
      <div className="flex items-center justify-between pt-1">
        <p className="text-sm font-bold text-foreground">Your connected devices</p>
        <button onClick={onRefresh} className="rounded-lg p-1.5 text-muted-foreground hover:text-foreground" aria-label="Refresh" data-testid="att-bio-refresh"><RefreshCw className="h-4 w-4" /></button>
      </div>
      {devices.map((d) => <DeviceCard key={d.id} d={d} onToggleAuto={onToggleAuto} onRemove={onRemove} onTest={onTest} />)}
      <button onClick={() => onOpen("connect")} data-testid="att-bio-connect" className="flex h-12 w-full items-center justify-center gap-2 rounded-2xl bg-foreground text-sm font-semibold text-background active:scale-[0.98]">
        <Plus className="h-4 w-4" />Connect a Device
      </button>
    </div>
  );
}
