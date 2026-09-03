import { Link } from "react-router-dom";

export function FinalCta() {
  return (
    <section className="bg-gradient-to-br from-brand via-[#6D28D9] to-[#4C1D95] py-20 sm:py-24" data-testid="final-cta-section">
      <div className="mx-auto max-w-4xl px-4 text-center sm:px-6">
        <h2 className="font-display text-3xl font-extrabold tracking-tight text-white sm:text-4xl lg:text-5xl">
          Ready to Take Control of Your Gym?
        </h2>
        <p className="mx-auto mt-5 max-w-2xl text-base text-white/90 sm:text-lg">
          Start your 10-day free trial and manage your members, payments and operations from one simple dashboard.
        </p>
        <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Link to="/register" data-testid="final-cta-trial"
                className="w-full rounded-full bg-white px-8 py-3.5 text-base font-bold text-brand shadow-lift transition-all hover:-translate-y-0.5 sm:w-auto">
            Start Free Trial
          </Link>
          <Link to="/login" data-testid="final-cta-login"
                className="w-full rounded-full border-2 border-white/60 px-8 py-3.5 text-base font-semibold text-white transition-colors hover:bg-white/10 sm:w-auto">
            Login
          </Link>
        </div>
        <p className="mt-6 text-sm text-white/75">10 days free · No credit card · ₹999/month after trial</p>
      </div>
    </section>
  );
}
