import { useRef, useState } from "react";
import { QRCodeCanvas } from "qrcode.react";
import { Share2, Download, ExternalLink, Info, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { downloadBlob } from "../../lib/files";

export const checkinUrl = (token) => `${window.location.origin}/checkin/${token}`;

const STEPS = [
  "Print this QR and stick it at your entrance or front desk.",
  "Members scan it with their phone camera. No app needed.",
  "Members enter their member ID or phone number. Staff pick the Staff tab and enter their phone or email.",
  "The first scan of the day is Punch In, the next one is Punch Out.",
];

export function QrPanel({ qr, onRotate }) {
  const [idx, setIdx] = useState(0);
  const wrap = useRef(null);
  if (!qr) return <div className="h-80 animate-pulse rounded-2xl bg-secondary" />;
  const o = qr.outlets[idx] || qr.outlets[0];
  if (!o) return <p className="text-sm text-muted-foreground">Add an outlet first to get a QR code.</p>;
  const url = checkinUrl(o.token);
  const png = () => new Promise((res) => wrap.current.querySelector("canvas").toBlob(res, "image/png"));
  const fname = `${qr.gym_name}-${o.outlet_name}-attendance-QR.png`.replace(/\s+/g, "-");

  const share = async () => {
    const file = new File([await png()], fname, { type: "image/png" });
    const text = `Scan to check in at ${qr.gym_name} (${o.outlet_name}): ${url}`;
    try {
      if (navigator.canShare && navigator.canShare({ files: [file] })) await navigator.share({ files: [file], title: "Attendance QR", text });
      else if (navigator.share) await navigator.share({ title: "Attendance QR", text, url });
      else { await navigator.clipboard.writeText(url); toast.success("Check-in link copied"); }
    } catch { /* user closed share sheet */ }
  };

  return (
    <div className="space-y-4" data-testid="att-qr-panel">
      {qr.outlets.length > 1 && (
        <div className="flex flex-wrap gap-2">
          {qr.outlets.map((x, i) => (
            <button key={x.outlet_id} onClick={() => setIdx(i)} data-testid={`att-qr-outlet-${i}`}
              className={`rounded-full px-3.5 py-1.5 text-sm font-semibold transition-colors ${i === idx ? "bg-brand text-white" : "bg-secondary text-muted-foreground"}`}>
              {x.outlet_name}
            </button>
          ))}
        </div>
      )}
      <div className="rounded-2xl border border-border bg-background p-5 text-center">
        <p className="font-display text-lg font-bold text-foreground" data-testid="att-qr-gym">{qr.gym_name}</p>
        <p className="text-sm text-muted-foreground">{o.outlet_name}{o.address ? `, ${o.address}` : ""}</p>
        <div ref={wrap} className="mx-auto mt-4 w-fit rounded-xl bg-white p-3" data-testid="att-qr-code">
          <QRCodeCanvas value={url} size={720} marginSize={1} level="M" style={{ width: 208, height: 208 }} />
        </div>
        <p className="mt-3 text-xs text-muted-foreground">Scan to mark attendance</p>
      </div>
      <div className="rounded-2xl border border-border bg-secondary/40 p-4">
        <p className="mb-2 flex items-center gap-1.5 text-sm font-bold text-foreground"><Info className="h-4 w-4 text-brand" />How to use</p>
        <ol className="space-y-1.5 text-[13px] leading-relaxed text-muted-foreground">
          {STEPS.map((s, i) => <li key={i} className="flex gap-2"><span className="font-num font-bold text-foreground">{i + 1}.</span>{s}</li>)}
        </ol>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <button onClick={share} data-testid="att-qr-share" className="col-span-2 flex h-12 items-center justify-center gap-2 rounded-2xl bg-foreground text-sm font-semibold text-background active:scale-[0.98]">
          <Share2 className="h-4 w-4" />Share QR
        </button>
        <button onClick={async () => downloadBlob(await png(), fname)} data-testid="att-qr-download" className="flex h-11 items-center justify-center gap-2 rounded-2xl border border-border text-sm font-semibold text-foreground">
          <Download className="h-4 w-4" />Download
        </button>
        <a href={url} target="_blank" rel="noopener noreferrer" data-testid="att-qr-open" className="flex h-11 items-center justify-center gap-2 rounded-2xl border border-border text-sm font-semibold text-foreground">
          <ExternalLink className="h-4 w-4" />Open page
        </a>
      </div>
      {onRotate && (
        <button onClick={() => onRotate(o.outlet_id)} data-testid="att-qr-rotate" className="mx-auto flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground">
          <RefreshCw className="h-3.5 w-3.5" />Generate a new QR (old one stops working)
        </button>
      )}
    </div>
  );
}
