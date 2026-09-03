import { Dumbbell } from "lucide-react";

export function Logo({ dark = false, compact = false }) {
  return (
    <div className="flex items-center gap-2.5" data-testid="gymboss-logo">
      <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand shadow-glow">
        <Dumbbell className="h-5 w-5 text-white" strokeWidth={2.5} />
      </div>
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
