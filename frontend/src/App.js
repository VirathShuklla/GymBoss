import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import Landing from "./pages/Landing";
import Login from "./pages/auth/Login";
import Register from "./pages/auth/Register";
import ForgotPassword from "./pages/auth/ForgotPassword";
import ResetPassword from "./pages/auth/ResetPassword";
import SuperAdmin from "./pages/SuperAdmin";
import AppLayout from "./layouts/AppLayout";
import Dashboard from "./pages/app/Dashboard";
import Members from "./pages/app/Members";
import Plans from "./pages/app/Plans";
import Attendance from "./pages/app/Attendance";
import Payments from "./pages/app/Payments";
import Enquiries from "./pages/app/Enquiries";
import Announcements from "./pages/app/Announcements";
import Expenses from "./pages/app/Expenses";
import Outlets from "./pages/app/Outlets";
import Staff from "./pages/app/Staff";
import Finance from "./pages/app/Finance";
import Reports from "./pages/app/Reports";
import ExportCenter from "./pages/app/ExportCenter";
import Settings from "./pages/app/Settings";
import Subscription from "./pages/app/Subscription";
import Support from "./pages/app/Support";
import Profile from "./pages/app/Profile";
import ComingSoon from "./pages/app/ComingSoon";

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

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/superadmin" element={<SuperAdminRoute><SuperAdmin /></SuperAdminRoute>} />
            <Route path="/app" element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
              <Route index element={<Navigate to="dashboard" replace />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="members" element={<Members />} />
              <Route path="attendance" element={<Attendance />} />
              <Route path="plans" element={<Plans />} />
              <Route path="payments" element={<Payments />} />
              <Route path="enquiries" element={<Enquiries />} />
              <Route path="announcements" element={<Announcements />} />
              <Route path="expenses" element={<Expenses />} />
              <Route path="outlets" element={<Outlets />} />
              <Route path="staff" element={<Staff />} />
              <Route path="finance" element={<Finance />} />
              <Route path="reports" element={<Reports />} />
              <Route path="export-center" element={<ExportCenter />} />
              <Route path="settings" element={<Settings />} />
              <Route path="subscription" element={<Subscription />} />
              <Route path="support" element={<Support />} />
              <Route path="profile" element={<Profile />} />
              <Route path=":module" element={<ComingSoon />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          <Toaster richColors position="top-right" />
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

export default App;
