import { Users, IndianRupee, MessageCircle, ClipboardCheck, UserCog, BarChart3, Smartphone, UserPlus, ArrowRight } from "lucide-react";

const FEATURES = [
  { icon: IndianRupee, title: "Know who owes you, in one tap", desc: "Every payment, due and discount in one place. Cash, UPI, card or bank, with a PDF receipt for every member.", replaces: "Excel sheets and guesswork" },
  { icon: Users, title: "Never miss a renewal again", desc: "Members, plans, freezes and expiries tracked for you. See who is expiring this week before they quietly stop coming.", replaces: "Registers and notebooks" },
  { icon: MessageCircle, title: "Reminders that get you paid", desc: "Send due reminders, renewal nudges, receipts and announcements on WhatsApp in one tap, using ready templates.", replaces: "Calling members every morning" },
  { icon: ClipboardCheck, title: "Attendance without the register", desc: "Members scan a QR at your entrance or use an eSSL / ZKTeco fingerprint machine. Expired members can be blocked automatically.", replaces: "Attendance registers" },
  { icon: UserPlus, title: "Turn enquiries into members", desc: "Log every walk-in and call, schedule follow-ups, and convert a lead into a member in one click.", replaces: "Lost phone numbers" },
  { icon: UserCog, title: "Your staff, your rules", desc: "Separate logins for managers, receptionists and trainers. You decide who can see money and who can only view.", replaces: "Sharing one password" },
  { icon: BarChart3, title: "Know your real profit", desc: "Revenue, expenses, dues and growth across all your branches, with one-click Excel exports for your CA.", replaces: "Month-end calculations" },
  { icon: Smartphone, title: "Run your gym from your phone", desc: "A fast mobile app for owners: collect payments, check in members and see today's numbers from anywhere.", replaces: "Being stuck at the front desk" },
];

export function Features() {
  return (
    <section id="features" className="bg-white py-20 sm:py-28" data-testid="features-section">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl">
          <p className="text-sm font-bold uppercase tracking-widest text-brand">Everything in one place</p>
          <h2 className="mt-3 font-display text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
            Stop losing money to missed dues and forgotten renewals.
          </h2>
          <p className="mt-4 text-base text-slate-600 sm:text-lg">
            GymBoss replaces your register, Excel sheets and daily reminder calls with one simple system, built for Indian gyms.
          </p>
        </div>
        <div className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((f) => (
            <div key={f.title} data-testid={`feature-${f.title.toLowerCase().replace(/[^a-z]+/g, "-")}`}
                 className="group flex flex-col rounded-2xl border border-slate-200 bg-white p-6 transition-[transform,border-color,box-shadow] duration-300 hover:-translate-y-1 hover:border-brand/30 hover:shadow-lift">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-soft text-brand transition-colors group-hover:bg-brand group-hover:text-white">
                <f.icon className="h-5 w-5" strokeWidth={2.2} />
              </div>
              <h3 className="mt-5 font-display text-lg font-bold leading-snug text-slate-900">{f.title}</h3>
              <p className="mt-2 flex-1 text-sm leading-relaxed text-slate-600">{f.desc}</p>
              <p className="mt-4 border-t border-slate-100 pt-3 text-xs text-slate-500"><span className="font-semibold text-slate-400">Replaces:</span> {f.replaces}</p>
            </div>
          ))}
        </div>
        <a href="#pricing" className="mt-10 inline-flex items-center gap-1.5 text-sm font-semibold text-brand hover:underline" data-testid="features-see-pricing">
          All of this is included in every plan. See pricing<ArrowRight className="h-4 w-4" />
        </a>
      </div>
    </section>
  );
}
