export function DashboardMockup() {
  const kpis = [
    { label: "Today's Collection", value: "₹12,500", accent: "text-emerald-400" },
    { label: "Admissions", value: "3", accent: "text-sky-400" },
    { label: "Renewals", value: "5", accent: "text-brand" },
    { label: "Due Members", value: "8", accent: "text-amber-400" },
  ];
  const rows = [
    ["Aarav Sharma", "Annual", "₹12,000", "Active"],
    ["Priya Nair", "Quarterly", "₹4,000", "Active"],
    ["Rohan Verma", "Monthly", "₹1,500", "Expiring"],
  ];
  return (
    <div className="relative mx-auto mt-16 max-w-5xl" data-testid="hero-dashboard-mockup">
      <div className="absolute -inset-8 rounded-[2rem] bg-gradient-to-tr from-brand/25 via-brand/10 to-transparent blur-2xl" aria-hidden="true" />
      <div className="relative overflow-hidden rounded-2xl border border-slate-700/60 bg-[#0F172A] shadow-lift">
        <div className="flex items-center gap-2 border-b border-slate-800 bg-[#0B1224] px-4 py-3">
          <span className="h-3 w-3 rounded-full bg-[#FF5F57]" />
          <span className="h-3 w-3 rounded-full bg-[#FEBC2E]" />
          <span className="h-3 w-3 rounded-full bg-[#28C840]" />
          <div className="ml-4 hidden h-6 w-64 items-center rounded-md bg-slate-800/70 px-3 text-[10px] text-slate-400 sm:flex">
            app.gymbossvvo.in/dashboard
          </div>
        </div>
        <div className="flex">
          <div className="hidden w-40 flex-col gap-1.5 border-r border-slate-800 bg-[#0B1224] p-3 sm:flex">
            {["Dashboard", "Members", "Plans", "Payments", "Reports"].map((item, i) => (
              <div key={item} className={`flex items-center gap-2 rounded-md px-2.5 py-2 text-[11px] font-medium ${i === 0 ? "bg-brand/15 text-brand" : "text-slate-400"}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${i === 0 ? "bg-brand" : "bg-slate-600"}`} />
                {item}
              </div>
            ))}
          </div>
          <div className="flex-1 p-4 sm:p-5">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="font-display text-sm font-bold text-white">Dashboard</p>
                <p className="text-[10px] text-slate-500">Iron Paradise Fitness — Indiranagar</p>
              </div>
              <span className="rounded-full border border-brand/30 bg-brand/10 px-2.5 py-1 text-[10px] font-semibold text-brand">9 Days Left</span>
            </div>
            <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
              {kpis.map((k) => (
                <div key={k.label} className="rounded-lg border border-slate-800 bg-slate-800/40 p-3">
                  <p className="text-[9px] font-medium uppercase tracking-wide text-slate-500">{k.label}</p>
                  <p className={`font-num mt-1 text-base font-bold ${k.accent}`}>{k.value}</p>
                </div>
              ))}
            </div>
            <div className="mt-3 rounded-lg border border-slate-800">
              {rows.map((r) => (
                <div key={r[0]} className="flex items-center justify-between border-b border-slate-800 px-3 py-2 text-[11px] last:border-0">
                  <span className="font-medium text-slate-300">{r[0]}</span>
                  <span className="hidden text-slate-500 sm:inline">{r[1]}</span>
                  <span className="font-num font-semibold text-emerald-400">{r[2]}</span>
                  <span className={`rounded-full px-2 py-0.5 text-[9px] font-semibold ${r[3] === "Active" ? "bg-emerald-500/15 text-emerald-400" : "bg-amber-500/15 text-amber-400"}`}>{r[3]}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
