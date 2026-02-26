import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider, useAuth } from "./auth/AuthContext";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { AdminDashboard } from "./pages/admin/Dashboard";
import { ManagerDashboard } from "./pages/manager/Dashboard";
import { LoginPage } from "./pages/LoginPage";
import { StaffDashboard } from "./pages/staff/Dashboard";
import "./styles.css";

const queryClient = new QueryClient();

function IndexRedirect() {
  const { user } = useAuth();
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return <Navigate to={`/${user.role}`} replace />;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<IndexRedirect />} />

            <Route element={<ProtectedRoute allowRoles={["admin"]} />}>
              <Route path="/admin" element={<AdminDashboard />} />
            </Route>

            <Route element={<ProtectedRoute allowRoles={["manager"]} />}>
              <Route path="/manager" element={<ManagerDashboard />} />
            </Route>

            <Route element={<ProtectedRoute allowRoles={["staff"]} />}>
              <Route path="/staff" element={<StaffDashboard />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
