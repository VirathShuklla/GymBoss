import { useState } from "react";
import { FileDown } from "lucide-react";
import { toast } from "sonner";
import api from "../../lib/api";
import { downloadBlob, blobError } from "../../lib/files";

const istMonth = () => new Date(Date.now() + 5.5 * 3600 * 1000).toISOString().slice(0, 7);

// One-tap monthly finance PDF (collections, expenses, net, dues) on transaction dates (IST).
export function MonthlyReportButton({ outletId, testid = "monthly-report", compact = false }) {
  const [month, setMonth] = useState(istMonth());
  const [busy, setBusy] = useState(false);
  const run = async () => {
    setBusy(true);
    try {
      const { data } = await api.get("/reports/monthly.pdf", { params: { month, outlet_id: outletId || undefined }, responseType: "blob" });
      await downloadBlob(data, `GymBoss-Finance-${month}.pdf`);
    } catch (e) { toast.error(await blobError(e, "Couldn't create the report")); } finally { setBusy(false); }
  };
  return (
    <div className={`flex items-center gap-2 ${compact ? "w-full" : ""}`} data-testid={testid}>
      <input type="month" value={month} max={istMonth()} onChange={(e) => setMonth(e.target.value || istMonth())}
             className="h-9 rounded-lg border border-border bg-card px-2.5 text-sm text-foreground" aria-label="Report month" data-testid={`${testid}-month`} />
      <button onClick={run} disabled={busy} data-testid={`${testid}-download`}
              className={`inline-flex h-9 items-center justify-center gap-1.5 rounded-lg bg-brand px-3.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-60 ${compact ? "flex-1" : ""}`}>
        <FileDown className="h-4 w-4" />{busy ? "Preparing…" : "Monthly PDF"}
      </button>
    </div>
  );
}
