import { useEffect } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { Home, LayoutGrid, User, ClipboardCheck } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { ExpiredBanner } from "../components/TrialBanner";

const NAV = [
  { to: "/m/home", label: "Home", icon: Home },
  { to: "/m/attendance", label: "Attendance", icon: ClipboardCheck },
  { to: "/m/manage", label: "Manage", icon: LayoutGrid },
  { to: "/m/profile", label: "Profile", icon: User },
];

export default function MobileLayout() {
  const { subscription } = useAuth();
  const { pathname } = useLocation();
  useEffect(() => { window.scrollTo(0, 0); }, [pathname]);
  const expired = ["expired", "payment_due"].includes(subscription?.status);
  return (
    <div className="min-h-screen bg-background" data-testid="m-app-shell">
      <main className="mx-auto max-w-md px-5 pb-[calc(88px+env(safe-area-inset-bottom))] pt-[calc(18px+env(safe-area-inset-top))]">
        {expired && pathname !== "/m/profile" && <ExpiredBanner planPath="/m/profile" price={subscription?.plan_price_inr} status={subscription?.status} />}
        <Outlet />
      </main>
      <nav className="m-bottomnav" data-testid="m-bottomnav">
        <div className="mx-auto flex max-w-md items-center justify-around">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              data-testid={`m-nav-${n.label.toLowerCase()}`}
              className={({ isActive }) => `m-navitem ${isActive ? "m-navitem-active" : ""}`}
            >
              <n.icon className="h-[22px] w-[22px]" strokeWidth={1.9} />
              <span>{n.label}</span>
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  );
}
