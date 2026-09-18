import {
  Users, Receipt as ReceiptIcon, IndianRupee, Building2, MessageCircle,
  BellRing, UserCog, UserPlus, BarChart3,
} from "lucide-react";

const FEATURES = [
  { icon: Users, title: "Membership Management", desc: "Track members, plans, renewals, freezes and dues across the full member lifecycle." },
  { icon: ReceiptIcon, title: "Invoices & Receipts", desc: "Send professional payment receipts and invoices to members instantly on WhatsApp." },
  { icon: IndianRupee, title: "Payment Tracking", desc: "Record Cash, UPI, Card and Bank payments with dues, discounts and receipts." },
  { icon: Building2, title: "Multi-Outlet Management", desc: "Run multiple branches from one account with outlet-wise data and switching." },
  { icon: MessageCircle, title: "WhatsApp Communication", desc: "Send reminders, wishes and announcements to members directly on WhatsApp." },
  { icon: BellRing, title: "Smart Reminders", desc: "Never miss an expiry or due payment with timely member reminders." },
  { icon: UserCog, title: "Staff Management", desc: "Role-based accounts for owners, managers, receptionists and trainers." },
  { icon: UserPlus, title: "Lead Management", desc: "Capture enquiries, schedule follow-ups and convert leads into members." },
  { icon: BarChart3, title: "Reports & Analytics", desc: "Revenue, collections, dues and growth reports with one-click exports." },
];

export function Features() {
  return (
    <section id="features" className="bg-white py-20 sm:py-28" data-testid="features-section">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="font-display text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
            Powerful Features for <span className="text-brand">Modern Gym Management</span>
          </h2>
          <p className="mt-4 text-base text-slate-600 sm:text-lg">
            Everything you need to manage and grow your gym from one place.
          </p>
        </div>
        <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.title} data-testid={`feature-${f.title.toLowerCase().replace(/\s/g, "-")}`}
                 className="group rounded-xl border border-slate-200 bg-white p-6 shadow-card transition-all hover:-translate-y-1 hover:border-brand/30 hover:shadow-lift">
              <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-brand-soft text-brand transition-colors group-hover:bg-brand group-hover:text-white">
                <f.icon className="h-5 w-5" strokeWidth={2.2} />
              </div>
              <h3 className="mt-4 font-display text-lg font-bold text-slate-900">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
