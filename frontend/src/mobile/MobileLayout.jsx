import { NavLink, Outlet } from "react-router-dom";
import { Home, LayoutGrid, User } from "lucide-react";

const NAV = [
  { to: "/m/home", label: "Home", icon: Home },
  { to: "/m/manage", label: "Manage", icon: LayoutGrid },
  { to: "/m/profile", label: "Profile", icon: User },
];

export default function MobileLayout() {
  return (
    <div className="min-h-screen bg-background" data-testid="m-app-shell">
      <main className="mx-auto max-w-md px-5 pb-[calc(96px+env(safe-area-inset-bottom))] pt-[calc(18px+env(safe-area-inset-top))]">
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
              <n.icon className="h-[22px] w-[22px]" strokeWidth={2.2} />
              <span>{n.label}</span>
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  );
}
