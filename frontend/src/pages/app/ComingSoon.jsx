import { useParams, Link } from "react-router-dom";
import { Hammer } from "lucide-react";

const TITLES = {
  members: "Members",
  attendance: "Attendance",
  plans: "Plans & Catalogue",
  payments: "Payments",
  enquiries: "Enquiries",
  announcements: "Announcements",
  expenses: "Expenses",
  outlets: "Outlets",
  staff: "Staff",
  finance: "Finance",
  reports: "Reports",
  "export-center": "Export Center",
  settings: "Settings",
  support: "Help & Support",
  subscription: "Subscription",
  profile: "My Profile",
};

export default function ComingSoon() {
  const { module } = useParams();
  const title = TITLES[module] || "This module";
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card px-6 py-24 text-center" data-testid="coming-soon-page">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand/12 text-brand">
        <Hammer className="h-7 w-7" />
      </div>
      <h1 className="mt-5 font-display text-xl font-bold text-foreground">{title}</h1>
      <p className="mt-2 max-w-sm text-sm text-muted-foreground">
        This module is being built in the next milestone and will be available shortly.
      </p>
      <Link to="/app/dashboard" className="mt-6 rounded-lg bg-brand px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-hover" data-testid="back-to-dashboard">
        Back to Dashboard
      </Link>
    </div>
  );
}
