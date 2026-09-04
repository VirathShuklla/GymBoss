import { useState } from "react";
import { NavLink, Outlet, useNavigate, useLocation, Link } from "react-router-dom";
import {
  LayoutDashboard, Users, ClipboardCheck, Layers, IndianRupee, UserPlus,
  Receipt, Building2, UserCog, BarChart3, FileBarChart, Download, Settings,
  LifeBuoy, Menu, PanelLeftClose, PanelLeftOpen, Bell, ChevronDown, LogOut, Crown, MessageCircle, Zap,
} from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { Logo } from "../components/Logo";
import { ThemeToggle } from "../components/ThemeToggle";
import { usePublicConfig, waLink } from "../hooks/usePublicConfig";
import { inr } from "../lib/format";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";
import { Button } from "../components/ui/button";

const NAV = [
  { to: "/app/dashboard", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/app/members", label: "Members", icon: Users },
  { to: "/app/attendance", label: "Attendance", icon: ClipboardCheck },
  { to: "/app/plans", label: "Plans & Catalogue", icon: Layers },
  { to: "/app/payments", label: "Payments", icon: IndianRupee },
  { to: "/app/enquiries", label: "Enquiries", icon: UserPlus },
  { to: "/app/expenses", label: "Expenses", icon: Receipt },
  { to: "/app/outlets", label: "Outlets", icon: Building2 },
  { to: "/app/staff", label: "Staff", icon: UserCog },
  { to: "/app/finance", label: "Finance", icon: BarChart3, finance: true },
  { to: "/app/reports", label: "Reports", icon: FileBarChart, finance: true },
  { to: "/app/export-center", label: "Export Center", icon: Download, finance: true },
  { to: "/app/settings", label: "Settings", icon: Settings },
  { to: "/app/support", label: "Help & Support", icon: LifeBuoy },
];

function TrialExpired({ onSubscribe, onLogout, price = 999 }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 text-center" data-testid="trial-expired-screen">
      <Logo />
      <div className="mt-8 max-w-md rounded-2xl border border-border bg-card p-8 shadow-card">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-warning/15 text-warning">
          <Zap className="h-6 w-6" />
        </div>
        <h1 className="mt-5 font-display text-2xl font-bold text-foreground">Your free trial has ended</h1>
        <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
          Your gym data is safe and exactly where you left it. Continue using GymBoss_VVO for just{" "}
          <span className="font-num font-bold text-foreground">{inr(price)}</span>/month.
        </p>
        <Button className="mt-6 w-full rounded-lg bg-brand font-semibold hover:bg-brand-hover" data-testid="subscribe-now-button" onClick={onSubscribe}>
          Subscribe Now — {inr(price)}/month
        </Button>
        <button onClick={onLogout} className="mt-5 text-sm font-medium text-muted-foreground hover:text-foreground" data-testid="trial-expired-logout">
          Logout
        </button>
      </div>
    </div>
  );
}

export default function AppLayout() {
  const { user, organisation, outlets, subscription, logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [outletId, setOutletId] = useState(() => localStorage.getItem("gb-outlet") || "all");
  const navigate = useNavigate();
  const location = useLocation();
  const config = usePublicConfig();

  const expired = ["expired", "payment_due"].includes(subscription?.status);
  const allowedWhenExpired = ["/app/subscription", "/app/support", "/app/profile", "/app/settings"];
  if (expired && !allowedWhenExpired.some((p) => location.pathname.startsWith(p))) {
    return <TrialExpired price={subscription?.plan_price_inr} onSubscribe={() => navigate("/app/subscription")} onLogout={async () => { await logout(); navigate("/login"); }} />;
  }

  const daysLeft = subscription?.trial_days_left ?? 0;
  const trialWarn = subscription?.status === "trial" && daysLeft <= 3;

  const handleOutlet = (v) => {
    setOutletId(v);
    localStorage.setItem("gb-outlet", v);
  };

  const sidebarContent = (scope) => (
    <div className="flex h-full flex-col">
      <div className={`flex h-16 items-center border-b border-border ${collapsed ? "justify-center px-2" : "px-5"}`}>
        <Link to="/app/dashboard"><Logo compact={collapsed} /></Link>
      </div>
      {!collapsed && (
        <div className="border-b border-border px-4 py-4" data-testid={`sidebar-gym-card-${scope}`}>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand/15 font-display text-sm font-bold text-brand">
              {organisation?.name?.slice(0, 2).toUpperCase() || "GB"}
            </div>
            <div className="min-w-0">
              <p className="truncate font-display text-sm font-bold text-foreground" data-testid={`sidebar-gym-name-${scope}`}>{organisation?.name}</p>
              <p className="truncate text-xs text-muted-foreground">{outlets.find((o) => o.id === outletId)?.name || "All Outlets"}</p>
            </div>
          </div>
          {subscription?.status === "trial" && (
            <div className={`mt-3 rounded-lg border px-3 py-2.5 ${trialWarn ? "border-warning/40 bg-warning/10" : "border-brand/25 bg-brand/10"}`} data-testid={`trial-badge-${scope}`}>
              <div className="flex items-center justify-between">
                <span className={`text-[11px] font-bold uppercase tracking-wide ${trialWarn ? "text-warning" : "text-brand"}`}>Free Trial</span>
                <span className={`font-num text-xs font-bold ${trialWarn ? "text-warning" : "text-brand"}`} data-testid={`trial-days-left-${scope}`}>
                  {daysLeft} {daysLeft === 1 ? "day" : "days"} left
                </span>
              </div>
              <Link to="/app/subscription" data-testid={`upgrade-now-button-${scope}`}
                    className="mt-2 flex items-center justify-center gap-1.5 rounded-md bg-brand py-1.5 text-xs font-semibold text-white transition-colors hover:bg-brand-hover">
                <Crown className="h-3.5 w-3.5" /> Upgrade Now
              </Link>
            </div>
          )}
        </div>
      )}
      <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 py-3" data-testid={`sidebar-nav-${scope}`}>
        {NAV.filter((item) => {
          if (!item.finance) return true;
          return ["owner", "admin", "manager"].includes(user?.role) || user?.finance_enabled;
        }).map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={() => setMobileOpen(false)}
            data-testid={`nav-${item.label.toLowerCase().replace(/[^a-z]+/g, "-")}-${scope}`}
            title={collapsed ? item.label : undefined}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                collapsed ? "justify-center" : ""
              } ${isActive ? "bg-brand/12 text-brand" : "text-muted-foreground hover:bg-secondary hover:text-foreground"}`
            }
          >
            <item.icon className="h-[18px] w-[18px] shrink-0" strokeWidth={2} />
            {!collapsed && item.label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-border p-3">
        {config?.whatsapp_number && (
          <a href={waLink(config.whatsapp_number, "Hi, I need help with GymBoss_VVO.")} target="_blank" rel="noopener noreferrer"
             data-testid={`sidebar-contact-us-${scope}`}
             className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-[#25D366] transition-colors hover:bg-secondary ${collapsed ? "justify-center" : ""}`}>
            <MessageCircle className="h-[18px] w-[18px] shrink-0" />
            {!collapsed && "Contact Us"}
          </a>
        )}
        {!collapsed && <p className="px-3 pt-2 text-[10px] text-muted-foreground/60">Version 1.0.0</p>}
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen bg-background" data-testid="app-shell">
      <aside className={`fixed inset-y-0 left-0 z-40 hidden border-r border-border bg-sidebar transition-all lg:block ${collapsed ? "w-[68px]" : "w-[248px]"}`}>
        {sidebarContent("desktop")}
      </aside>
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/50" onClick={() => setMobileOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-[268px] border-r border-border bg-sidebar">{sidebarContent("mobile")}</aside>
        </div>
      )}
      <div className={`flex min-w-0 flex-1 flex-col transition-all ${collapsed ? "lg:pl-[68px]" : "lg:pl-[248px]"}`}>
        <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-border bg-sidebar/95 px-4 backdrop-blur-sm sm:px-6" data-testid="top-navbar">
          <button className="rounded-lg p-2 text-muted-foreground hover:bg-secondary hover:text-foreground lg:hidden"
                  onClick={() => setMobileOpen(true)} data-testid="mobile-menu-button" aria-label="Open menu">
            <Menu className="h-5 w-5" />
          </button>
          <button className="hidden rounded-lg p-2 text-muted-foreground hover:bg-secondary hover:text-foreground lg:block"
                  onClick={() => setCollapsed(!collapsed)} data-testid="sidebar-collapse-button" aria-label="Toggle sidebar">
            {collapsed ? <PanelLeftOpen className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />}
          </button>
          <Select value={outletId} onValueChange={handleOutlet}>
            <SelectTrigger className="h-9 w-[170px] rounded-lg text-sm" data-testid="outlet-switcher">
              <Building2 className="mr-1.5 h-4 w-4 text-muted-foreground" />
              <SelectValue placeholder="All Outlets" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all" data-testid="outlet-option-all">All Outlets</SelectItem>
              {outlets.map((o) => (
                <SelectItem key={o.id} value={o.id} data-testid={`outlet-option-${o.id}`}>{o.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <div className="flex-1" />
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="relative rounded-lg p-2 text-muted-foreground hover:bg-secondary hover:text-foreground" data-testid="notifications-button" aria-label="Notifications">
                <Bell className="h-[18px] w-[18px]" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-64 p-3">
              <p className="text-center text-sm text-muted-foreground" data-testid="notifications-empty">No notifications yet</p>
            </DropdownMenuContent>
          </DropdownMenu>
          <ThemeToggle testid="topbar-theme-toggle" />
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="flex items-center gap-2 rounded-lg py-1.5 pl-1.5 pr-2.5 hover:bg-secondary" data-testid="user-menu-button">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand/15 font-display text-xs font-bold text-brand">
                  {user?.full_name?.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase()}
                </div>
                <span className="hidden max-w-[120px] truncate text-sm font-medium text-foreground sm:block">{user?.full_name}</span>
                <ChevronDown className="hidden h-4 w-4 text-muted-foreground sm:block" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-52">
              <DropdownMenuItem onClick={() => navigate("/app/profile")} data-testid="menu-my-profile">My Profile</DropdownMenuItem>
              <DropdownMenuItem onClick={() => navigate("/app/settings")} data-testid="menu-gym-settings">Gym Settings</DropdownMenuItem>
              <DropdownMenuItem onClick={() => navigate("/app/subscription")} data-testid="menu-subscription">Subscription</DropdownMenuItem>
              <DropdownMenuItem onClick={() => navigate("/app/support")} data-testid="menu-help">Help</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-danger focus:text-danger" data-testid="menu-logout"
                                onClick={async () => { await logout(); navigate("/login"); }}>
                <LogOut className="mr-2 h-4 w-4" /> Logout
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>
        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <div className="mx-auto w-full max-w-[1440px]">
            <Outlet context={{ outletId: outletId === "all" ? undefined : outletId }} />
          </div>
        </main>
      </div>
    </div>
  );
}
