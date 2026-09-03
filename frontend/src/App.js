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
