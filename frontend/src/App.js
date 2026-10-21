import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { isInApp, STORE_BLOCKED } from "./lib/inApp";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import Landing from "./pages/Landing";
import { installWhatsAppTracking } from "./lib/track";

// Everything except the landing page is code-split so first-time visitors download only what they see.
const Login = lazy(() => import("./pages/auth/Login"));
const Register = lazy(() => import("./pages/auth/Register"));
const ForgotPassword = lazy(() => import("./pages/auth/ForgotPassword"));
const ResetPassword = lazy(() => import("./pages/auth/ResetPassword"));
const SuperAdmin = lazy(() => import("./pages/SuperAdmin"));
const AppLayout = lazy(() => import("./layouts/AppLayout"));
const Dashboard = lazy(() => import("./pages/app/Dashboard"));
const Members = lazy(() => import("./pages/app/Members"));
const Plans = lazy(() => import("./pages/app/Plans"));
const Payments = lazy(() => import("./pages/app/Payments"));
const Enquiries = lazy(() => import("./pages/app/Enquiries"));
const Expenses = lazy(() => import("./pages/app/Expenses"));
const Outlets = lazy(() => import("./pages/app/Outlets"));
const Staff = lazy(() => import("./pages/app/Staff"));
const Finance = lazy(() => import("./pages/app/Finance"));
const Reports = lazy(() => import("./pages/app/Reports"));
const ExportCenter = lazy(() => import("./pages/app/ExportCenter"));
const Settings = lazy(() => import("./pages/app/Settings"));
const Subscription = lazy(() => import("./pages/app/Subscription"));
const Support = lazy(() => import("./pages/app/Support"));
const Profile = lazy(() => import("./pages/app/Profile"));
const ComingSoon = lazy(() => import("./pages/app/ComingSoon"));
const MobileApp = lazy(() => import("./mobile/MobileApp"));
const Attendance = lazy(() => import("./pages/app/Attendance"));
const CheckIn = lazy(() => import("./pages/CheckIn"));
const Legal = lazy(() => import("./pages/Legal"));
const BillingPortal = lazy(() => import("./pages/BillingPortal"));

const PORTAL_HOST = process.env.REACT_APP_PORTAL_HOST;

// Store builds never reach selling pages; the payments subdomain opens straight into billing.
function PlatformGate({ children }) {
  const { pathname } = useLocation();
  if (isInApp() && STORE_BLOCKED.test(pathname)) return <Navigate to={pathname.includes("subscription") ? "/m/profile" : "/m"} replace />;
  if (PORTAL_HOST && window.location.hostname === PORTAL_HOST && pathname === "/") return <Navigate to="/billing" replace />;
  return children;
}

installWhatsAppTracking();

function FullPageLoader() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background" data-testid="app-loader">
      <div className="h-10 w-10 animate-spin rounded-full border-[3px] border-brand border-t-transparent" />
    </div>
  );
}

function ProtectedRoute({ children }) {
  const { status, user } = useAuth();
  const location = useLocation();
  if (status === "loading") return <FullPageLoader />;
  if (status !== "authed") return <Navigate to="/login" state={{ from: location }} replace />;
  if (user?.role === "super_admin") return <Navigate to="/superadmin" replace />;
  return children;
}

function SuperAdminRoute({ children }) {
  const { status, user } = useAuth();
  if (status === "loading") return <FullPageLoader />;
  if (status !== "authed" || user?.role !== "super_admin") return <Navigate to="/login" replace />;
  return children;
}

function FinanceRoute({ children }) {
  const { user } = useAuth();
  const allowed = ["owner", "admin", "manager"].includes(user?.role) || user?.finance_enabled;
  if (!allowed) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card px-6 py-24 text-center" data-testid="finance-access-denied">
        <p className="font-display text-lg font-bold text-foreground">No finance access</p>
        <p className="mt-2 max-w-sm text-sm text-muted-foreground">Your account doesn't have access to finance pages. Ask your gym owner to enable it in Staff settings.</p>
      </div>
    );
  }
  return children;
}

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <Suspense fallback={<FullPageLoader />}>
          <Routes>
            <Route path="/" element={<PlatformGate><Landing /></PlatformGate>} />
            <Route path="/billing" element={<PlatformGate><BillingPortal /></PlatformGate>} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/privacy" element={<Legal kind="privacy" />} />
            <Route path="/terms" element={<Legal kind="terms" />} />
            <Route path="/superadmin" element={<SuperAdminRoute><SuperAdmin /></SuperAdminRoute>} />
            <Route path="/app" element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
              <Route index element={<Navigate to="dashboard" replace />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="members" element={<Members />} />
              <Route path="attendance" element={<Attendance />} />
              <Route path="plans" element={<Plans />} />
              <Route path="payments" element={<Payments />} />
              <Route path="enquiries" element={<Enquiries />} />
              <Route path="expenses" element={<Expenses />} />
              <Route path="outlets" element={<Outlets />} />
              <Route path="staff" element={<Staff />} />
              <Route path="finance" element={<FinanceRoute><Finance /></FinanceRoute>} />
              <Route path="reports" element={<FinanceRoute><Reports /></FinanceRoute>} />
              <Route path="export-center" element={<FinanceRoute><ExportCenter /></FinanceRoute>} />
              <Route path="settings" element={<Settings />} />
              <Route path="subscription" element={<PlatformGate><Subscription /></PlatformGate>} />
              <Route path="support" element={<Support />} />
              <Route path="profile" element={<Profile />} />
              <Route path=":module" element={<ComingSoon />} />
            </Route>
            <Route path="/checkin/:token" element={<CheckIn />} />
            <Route path="/m/*" element={<MobileApp />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          </Suspense>
          <Toaster richColors position="top-right" />
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

export default App;
