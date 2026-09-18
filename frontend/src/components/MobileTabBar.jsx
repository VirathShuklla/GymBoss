import { NavLink } from "react-router-dom";
import { LayoutDashboard, Users, IndianRupee, Layers, Menu } from "lucide-react";

const TABS = [
  { to: "/app/dashboard", label: "Home", icon: LayoutDashboard, end: true },
  { to: "/app/members", label: "Members", icon: Users },
  { to: "/app/payments", label: "Payments", icon: IndianRupee },
  { to: "/app/plans", label: "Plans", icon: Layers },
];

export function MobileTabBar({ onMore }) {
  return (
    <nav className="mobile-tabbar lg:hidden" data-testid="mobile-tabbar">
      {TABS.map((t) => (
        <NavLink
          key={t.to}
          to={t.to}
          end={t.end}
          data-testid={`tab-${t.label.toLowerCase()}`}
          className={({ isActive }) => `mobile-tab ${isActive ? "mobile-tab-active" : ""}`}
        >
          <t.icon className="h-[22px] w-[22px]" strokeWidth={2.2} />
          <span>{t.label}</span>
        </NavLink>
      ))}
      <button type="button" onClick={onMore} className="mobile-tab" data-testid="tab-more">
        <Menu className="h-[22px] w-[22px]" strokeWidth={2.2} />
        <span>More</span>
      </button>
    </nav>
  );
}
