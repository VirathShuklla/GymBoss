import { Check, X, Minus } from "lucide-react";

const ROWS = [
  ["Know who owes money, instantly", "no", "partial", "yes"],
  ["Automatic expiry & renewal list", "no", "partial", "yes"],
  ["WhatsApp reminders in one tap", "no", "no", "yes"],
  ["PDF receipts for members", "no", "no", "yes"],
  ["QR & fingerprint attendance", "partial", "no", "yes"],
  ["Staff logins with limited access", "no", "no", "yes"],
  ["Works on your phone, anywhere", "no", "partial", "yes"],
  ["Monthly revenue & expense reports", "no", "partial", "yes"],
];
const Cell = ({ v }) => v === "yes"
  ? <Check className="mx-auto h-5 w-5 text-emerald-500" strokeWidth={3} />
  : v === "partial" ? <Minus className="mx-auto h-5 w-5 text-amber-400" strokeWidth={3} /> : <X className="mx-auto h-5 w-5 text-slate-300" strokeWidth={3} />;

export function Comparison() {
  return (
    <section className="bg-white py-20 sm:py-28" data-testid="comparison-section">
      <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
        <div className="text-center">
          <p className="text-sm font-bold uppercase tracking-widest text-brand">Why switch</p>
          <h2 className="mt-3 font-display text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">Registers and Excel can't chase your dues.</h2>
        </div>
        <div className="mt-12 overflow-hidden rounded-3xl border border-slate-200">
          <table className="w-full text-sm" data-testid="comparison-table">
            <thead>
              <tr className="bg-slate-50 text-slate-500">
                <th className="px-4 py-4 text-left font-semibold sm:px-6"> </th>
                <th className="px-2 py-4 font-semibold">Register</th>
                <th className="px-2 py-4 font-semibold">Excel</th>
                <th className="bg-brand px-2 py-4 font-bold text-white">GymBoss</th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map(([label, a, b, c]) => (
                <tr key={label} className="border-t border-slate-100">
                  <td className="px-4 py-3.5 font-medium text-slate-700 sm:px-6">{label}</td>
                  <td className="px-2 py-3.5"><Cell v={a} /></td>
                  <td className="px-2 py-3.5"><Cell v={b} /></td>
                  <td className="bg-brand/5 px-2 py-3.5"><Cell v={c} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
