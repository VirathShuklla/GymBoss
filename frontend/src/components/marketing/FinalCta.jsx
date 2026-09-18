import { Link } from "react-router-dom";
import { usePublicConfig } from "../../hooks/usePublicConfig";
import { inr } from "../../lib/format";

export function FinalCta() {
  const config = usePublicConfig();
  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-brand via-[#6D28D9] to-[#4C1D95] py-20 sm:py-24" data-testid="final-cta-section">
      <div className="pointer-events-none absolute -left-20 top-10 h-72 w-72 rounded-full bg-white/10 blur-3xl" aria-hidden="true" />
      <div className="relative mx-auto max-w-6xl px-4 sm:px-6">
        <div className="grid items-center gap-8 lg:grid-cols-[1.35fr_1fr]">
          <div className="text-center lg:text-left">
            <h2 className="font-display text-3xl font-extrabold tracking-tight text-white sm:text-4xl lg:text-5xl">
              Ready to Take Control of Your Gym?
            </h2>
            <p className="mx-auto mt-5 max-w-2xl text-base text-white/90 sm:text-lg lg:mx-0">
              Start your 10-day free trial and manage your members, payments and operations from one simple dashboard.
            </p>
            <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row lg:justify-start">
              <Link to="/register" data-testid="final-cta-trial"
                    className="w-full rounded-full bg-white px-8 py-3.5 text-base font-bold text-brand shadow-lift transition-all hover:-translate-y-0.5 sm:w-auto">
                Start Free Trial
              </Link>
              <Link to="/login" data-testid="final-cta-login"
                    className="w-full rounded-full border-2 border-white/60 px-8 py-3.5 text-base font-semibold text-white transition-colors hover:bg-white/10 sm:w-auto">
                Login
              </Link>
            </div>
            <p className="mt-6 text-sm text-white/75">10 days free · No credit card · {inr(config?.plan_price_inr || 999)}/month after trial</p>
          </div>

          <div className="relative flex justify-center lg:justify-end" data-testid="final-cta-mascot">
            <span className="pointer-events-none absolute inset-x-0 top-1/2 mx-auto h-64 w-64 -translate-y-1/2 rounded-full bg-white/15 blur-2xl" aria-hidden="true" />
            <span className="chip-float absolute right-2 top-4 z-20 hidden rounded-full bg-white px-3.5 py-1.5 text-xs font-black uppercase tracking-wide text-brand shadow-lift sm:block">
              Let's Go!
            </span>
            <img src="/mascots/motivating.png" alt="GymBoss mascot cheering" loading="lazy"
                 className="mascot-float relative z-10 w-[220px] drop-shadow-2xl sm:w-[280px]" />
          </div>
        </div>
      </div>
    </section>
  );
}
