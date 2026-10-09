import { Link } from "react-router-dom";
import { Users, IndianRupee, ClipboardCheck, MessageCircle, BarChart3, UserCog, Bell, Smartphone, ShieldCheck, CreditCard, Download } from "lucide-react";
import { usePublicConfig } from "../../hooks/usePublicConfig";
import { inr } from "../../lib/format";
import { track } from "../../lib/track";

const STACK = [
  { icon: Users, title: "Member management", replaces: "Registers and notebooks" },
  { icon: IndianRupee, title: "Fee & due tracking", replaces: "Excel sheets and memory" },
  { icon: Bell, title: "Renewal & due reminders", replaces: "Manual calls every morning" },
  { icon: MessageCircle, title: "WhatsApp messages & receipts", replaces: "Typing every message by hand" },
  { icon: ClipboardCheck, title: "QR & biometric attendance", replaces: "Attendance registers" },
  { icon: UserCog, title: "Staff roles & permissions", replaces: "Sharing one login with everyone" },
  { icon: BarChart3, title: "Finance reports & exports", replaces: "Month-end calculations" },
  { icon: Smartphone, title: "Mobile app for owners", replaces: "Being stuck at the front desk" },
];

export function ValueStack() {
  const config = usePublicConfig();
  const plans = config?.pricing_plans || [];
  const best = plans.find((p) => p.id === "yearly") || plans[0];
  const perDay = best ? Math.round(best.effective_price / (best.months * 30)) : null;
  return (
    <section id="value" className="bg-slate-950 py-20 text-white sm:py-28" data-testid="value-stack-section">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl">
          <p className="text-sm font-bold uppercase tracking-widest text-violet-300">Everything you get</p>
          <h2 className="mt-3 font-display text-3xl font-extrabold tracking-tight sm:text-4xl">8 tools your gym needs. One simple price.</h2>
          <p className="mt-4 text-base text-slate-300 sm:text-lg">Stop juggling registers, Excel, WhatsApp and calls. Every plan includes all of this, with no add-ons and no per-member fees.</p>
        </div>
        <div className="mt-12 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {STACK.map(({ icon: Icon, title, replaces }) => (
            <div key={title} className="rounded-2xl border border-white/10 bg-white/[0.04] p-5" data-testid={`value-item-${title.split(" ")[0].toLowerCase()}`}>
              <Icon className="h-6 w-6 text-violet-300" />
              <p className="mt-4 font-display text-base font-bold">{title}</p>
              <p className="mt-1 text-sm text-slate-400"><span className="text-slate-500">Replaces:</span> {replaces}</p>
            </div>
          ))}
        </div>
        <div className="mt-8 flex flex-col items-start justify-between gap-6 rounded-3xl bg-gradient-to-r from-brand to-violet-500 p-7 sm:flex-row sm:items-center sm:p-9">
          <div>
            <p className="text-sm font-semibold text-white/80">All 8 tools, every day, for just</p>
            <p className="mt-1 font-display text-4xl font-extrabold tracking-tight" data-testid="value-per-day">{perDay ? `${inr(perDay)}/day` : "\u00a0"}</p>
            {best && <p className="mt-1 text-sm text-white/80">on the {best.name} plan ({inr(best.effective_price)}/{best.months === 12 ? "year" : `${best.months} months`})</p>}
          </div>
          <Link to="/register" onClick={() => track("hero_cta_click", { location: "value_stack" })} data-testid="value-cta" className="rounded-xl bg-white px-6 py-3.5 text-sm font-bold text-brand transition-transform hover:-translate-y-0.5">Start 10-Day Free Trial</Link>
        </div>
        <div className="mt-6 grid gap-3 sm:grid-cols-3" data-testid="risk-reversal">
          {[
            [CreditCard, "No credit card to start", "Use every feature free for 10 days."],
            [ShieldCheck, "Your data stays yours", "Nothing is deleted, even if you stop paying."],
            [Download, "Export anytime", "Download members and payments to Excel in one click."],
          ].map(([Icon, t, d]) => (
            <div key={t} className="flex gap-3 rounded-2xl border border-white/10 p-4">
              <Icon className="mt-0.5 h-5 w-5 shrink-0 text-emerald-400" />
              <div><p className="text-sm font-bold">{t}</p><p className="text-sm text-slate-400">{d}</p></div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
