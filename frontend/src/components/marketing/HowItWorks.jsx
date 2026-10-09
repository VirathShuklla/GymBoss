import { Building2, Users, TrendingUp } from "lucide-react";

const STEPS = [
  { icon: Building2, title: "Sign up in 2 minutes", desc: "Create your account with your gym name and phone number. No credit card, no setup fee." },
  { icon: Users, title: "Add your plans and members", desc: "Enter your membership plans and existing members. Most gyms are fully set up on day one." },
  { icon: TrendingUp, title: "Collect more, chase less", desc: "GymBoss shows who is due and expiring every day, so you spend your time on the gym floor, not on paperwork." },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="bg-slate-50 py-20 sm:py-28" data-testid="how-it-works-section">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="font-display text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
            Up and running <span className="text-brand">today</span>
          </h2>
          <p className="mt-4 text-base text-slate-600 sm:text-lg">
            Three steps. No training, no IT person needed.
          </p>
        </div>
        <div className="relative mt-16 grid gap-10 sm:grid-cols-3 sm:gap-8">
          <div className="absolute left-0 right-0 top-9 hidden border-t-2 border-dashed border-slate-300 sm:block" aria-hidden="true" />
          {STEPS.map((s, i) => (
            <div key={s.title} className="relative text-center" data-testid={`step-${i + 1}`}>
              <div className="relative mx-auto flex h-[72px] w-[72px] items-center justify-center rounded-2xl bg-brand text-white shadow-glow">
                <s.icon className="h-7 w-7" strokeWidth={2.2} />
                <span className="absolute -right-2 -top-2 flex h-7 w-7 items-center justify-center rounded-full border-2 border-white bg-slate-900 font-num text-xs font-bold text-white">
                  {i + 1}
                </span>
              </div>
              <h3 className="mt-6 font-display text-lg font-bold text-slate-900">{s.title}</h3>
              <p className="mx-auto mt-2 max-w-xs text-sm leading-relaxed text-slate-600">{s.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
