import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import "./mobile.css";
import MobileLayout from "./MobileLayout";
import Onboarding from "./screens/Onboarding";
import Welcome from "./screens/Welcome";
import Login from "./screens/Login";
import Register from "./screens/Register";
import Home from "./screens/Home";
import Manage from "./screens/Manage";
import Profile from "./screens/Profile";

function Loader() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background" data-testid="m-loader">
      <div className="h-9 w-9 animate-spin rounded-full border-[3px] border-brand border-t-transparent" />
    </div>
  );
}

function Entry() {
  const { status } = useAuth();
  if (status === "loading") return <Loader />;
  if (status === "authed") return <Navigate to="/m/home" replace />;
  const seen = localStorage.getItem("gb-m-onboarded");
  return <Navigate to={seen ? "/m/welcome" : "/m/onboarding"} replace />;
}

function Protected({ children }) {
  const { status } = useAuth();
  const loc = useLocation();
  if (status === "loading") return <Loader />;
  if (status !== "authed") return <Navigate to="/m/welcome" replace state={{ from: loc }} />;
  return children;
}

export default function MobileApp() {
  return (
    <div className="m-root bg-background">
      <Routes>
        <Route index element={<Entry />} />
        <Route path="onboarding" element={<Onboarding />} />
        <Route path="welcome" element={<Welcome />} />
        <Route path="login" element={<Login />} />
        <Route path="register" element={<Register />} />
        <Route element={<Protected><MobileLayout /></Protected>}>
          <Route path="home" element={<Home />} />
          <Route path="manage" element={<Manage />} />
          <Route path="profile" element={<Profile />} />
        </Route>
        <Route path="*" element={<Navigate to="/m" replace />} />
      </Routes>
    </div>
  );
}
