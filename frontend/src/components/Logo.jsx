export function Logo({ dark = false, compact = false }) {
  return (
    <div className="flex items-center gap-2.5" data-testid="gymboss-logo">
      <img src="/logo.png" alt="GymBoss_VVO" className="h-9 w-9 shrink-0 rounded-xl object-cover shadow-glow" />
      {!compact && (
        <div className="leading-none">
          <span className={`font-display text-lg font-extrabold tracking-tight ${dark ? "text-white" : "text-slate-900 dark:text-white"}`}>
            GymBoss
          </span>
          <span className="font-display text-lg font-extrabold tracking-tight text-brand">_VVO</span>
        </div>
      )}
    </div>
  );
}
