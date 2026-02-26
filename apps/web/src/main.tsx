import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider, useAuth } from "./auth/AuthContext";
import { ProtectedRoute } from "./auth/ProtectedRoute";

// Admin screens
import { AdminDashboard } from "./pages/admin/Dashboard";
import { StaffManagement } from "./pages/admin/StaffManagement";
import { AuditLog } from "./pages/admin/AuditLog";

// Manager screens
import { ManagerDashboard } from "./pages/manager/Dashboard";
import { SwapApprovalQueue } from "./pages/manager/SwapApprovalQueue";
import { OvertimeFairness } from "./pages/manager/OvertimeFairness";

// Staff screens
import { StaffDashboard } from "./pages/staff/Dashboard";
import { AvailabilitySetup } from "./pages/staff/AvailabilitySetup";

// Shared
import { LoginPage } from "./pages/LoginPage";
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

            {/* Admin Routes */}
            <Route element={<ProtectedRoute allowRoles={["admin"]} />}>
              <Route path="/admin" element={<AdminDashboard />} />
              <Route path="/admin/staff" element={<StaffManagement />} />
              <Route path="/admin/audit" element={<AuditLog />} />
            </Route>

            {/* Manager Routes */}
            <Route element={<ProtectedRoute allowRoles={["manager"]} />}>
              <Route path="/manager" element={<ManagerDashboard />} />
              <Route path="/manager/swaps" element={<SwapApprovalQueue />} />
              <Route path="/manager/analytics" element={<OvertimeFairness />} />
            </Route>

            {/* Staff Routes */}
            <Route element={<ProtectedRoute allowRoles={["staff"]} />}>
              <Route path="/staff" element={<StaffDashboard />} />
              <Route path="/staff/availability" element={<AvailabilitySetup />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
