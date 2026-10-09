import { useState } from "react";
import { Link } from "react-router-dom";
import { usePublicConfig } from "../../hooks/usePublicConfig";
import { inr } from "../../lib/format";
import { track } from "../../lib/track";

function Slider({ label, value, min, max, step, onChange, fmt, testid }) {
  return (
    <label className="block">
      <span className="flex items-baseline justify-between text-sm"><span className="font-medium text-slate-700">{label}</span><span className="font-display text-lg font-bold text-slate-900">{fmt(value)}</span></span>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))}
        className="mt-2 w-full accent-[hsl(var(--brand))]" data-testid={testid} />
    </label>
  );
}

// Visitor-driven estimate: how much unpaid/forgotten fee money GymBoss reminders could recover.
export function RoiCalculator() {
  const config = usePublicConfig();
  const monthly = config?.plan_price_inr || 999;
  const [members, setMembers] = useState(150);
  const [fee, setFee] = useState(1000);
  const [late, setLate] = useState(10);
  const atRisk = Math.round((members * fee * late) / 100);
  const recovered = Math.round(atRisk / 2);
  const multiple = recovered / monthly;
  const touched = () => track("roi_used", {}, { oncePerSession: true });

  return (
    <section className="bg-[#FBF6EC] py-20 sm:py-28" data-testid="roi-section" onPointerDown={touched}>
      <div className="mx-auto grid max-w-6xl items-center gap-10 px-4 sm:px-6 lg:grid-cols-2 lg:px-8">
        <div>
          <p className="text-sm font-bold uppercase tracking-widest text-brand">Do the maths</p>
          <h2 className="mt-3 font-display text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">How much fee money slips through the cracks?</h2>
          <p className="mt-4 text-base text-slate-600 sm:text-lg">Most gyms lose money to forgotten renewals and dues nobody followed up on. Move the sliders to match your gym.</p>
          <div className="mt-8 space-y-6 rounded-3xl border border-slate-200 bg-white p-6">
            <Slider label="Active members" value={members} min={20} max={1000} step={10} onChange={setMembers} fmt={(v) => v} testid="roi-members" />
            <Slider label="Average monthly fee" value={fee} min={300} max={5000} step={100} onChange={setFee} fmt={inr} testid="roi-fee" />
            <Slider label="Members who pay late or forget each month" value={late} min={2} max={40} step={1} onChange={setLate} fmt={(v) => `${v}%`} testid="roi-late" />
          </div>
        </div>
        <div className="rounded-3xl bg-slate-900 p-8 text-white shadow-2xl sm:p-10" data-testid="roi-result">
          <p className="text-sm text-slate-400">Fees at risk every month</p>
          <p className="font-display text-4xl font-extrabold tracking-tight" data-testid="roi-at-risk">{inr(atRisk)}</p>
          <div className="my-6 h-px bg-white/10" />
          <p className="text-sm text-slate-400">If timely reminders recover even half of it</p>
          <p className="font-display text-5xl font-extrabold tracking-tight text-emerald-400" data-testid="roi-recovered">{inr(recovered)}<span className="text-lg font-semibold text-slate-400">/month</span></p>
          <p className="mt-4 text-base text-slate-300">
            That's <span className="font-bold text-white" data-testid="roi-multiple">{multiple >= 1 ? `${multiple.toFixed(1)}×` : "close to"}</span> the cost of GymBoss ({inr(monthly)}/month).
          </p>
          <Link to="/register" onClick={() => track("hero_cta_click", { location: "roi" })} data-testid="roi-cta"
            className="mt-8 block rounded-xl bg-brand py-3.5 text-center text-sm font-semibold text-white hover:bg-brand-hover">Start recovering dues: try free for 10 days</Link>
          <p className="mt-3 text-center text-xs text-slate-500">This is an estimate based on your inputs, not a guarantee.</p>
        </div>
      </div>
    </section>
  );
}
