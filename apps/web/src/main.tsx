/**
 * @file /apps/web/src/main.tsx
 *
 * @description
 * Application bootstrap and route composition for the web frontend.
 *
 * @dependencies
 * - (No in-repo dependents detected.)
 *
 * @importance
 * This module is critical for application access flow and role-based navigation
 * safety.
 */

import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider, useAuth } from "./auth/AuthContext";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { RealtimeProvider } from "./components/RealtimeProvider";
import { ToastProvider } from "./components/ToastProvider";

// Admin screens
import { AdminDashboard } from "./pages/admin/Dashboard";
import { StaffManagement } from "./pages/admin/StaffManagement";
import { AuditLog } from "./pages/admin/AuditLog";
import { SkillCatalog } from "./pages/admin/SkillCatalog";

// Manager screens
import { ManagerDashboard } from "./pages/manager/Dashboard";
import { SwapApprovalQueue } from "./pages/manager/SwapApprovalQueue";
import { OvertimeFairness } from "./pages/manager/OvertimeFairness";
import { ShiftHistory } from "./pages/manager/ShiftHistory";

// Staff screens
import { StaffDashboard } from "./pages/staff/Dashboard";
import { AvailabilitySetup } from "./pages/staff/AvailabilitySetup";
import { SwapInbox } from "./pages/staff/SwapInbox";
import { NotificationSettings } from "./pages/common/NotificationSettings";

// Shared
import { LoginPage } from "./pages/LoginPage";
import "./styles.css";

const queryClient = new QueryClient();

/**
 * Redirect users from `/` to their role home or login when unauthenticated.
 */
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
        <ToastProvider>
          <BrowserRouter>
            <RealtimeProvider>
              <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/" element={<IndexRedirect />} />

                {/* Admin Routes */}
                <Route element={<ProtectedRoute allowRoles={["admin"]} />}>
                  <Route path="/admin" element={<AdminDashboard />} />
                  <Route path="/admin/staff" element={<StaffManagement />} />
                  <Route path="/admin/audit" element={<AuditLog />} />
                  <Route path="/admin/skills" element={<SkillCatalog />} />
                </Route>

                {/* Manager Routes */}
                <Route element={<ProtectedRoute allowRoles={["manager", "admin"]} />}>
                  <Route path="/manager" element={<ManagerDashboard />} />
                  <Route path="/manager/swaps" element={<SwapApprovalQueue />} />
                  <Route path="/manager/analytics" element={<OvertimeFairness />} />
                  <Route path="/manager/history" element={<ShiftHistory />} />
                </Route>

                {/* Staff Routes */}
                <Route element={<ProtectedRoute allowRoles={["staff"]} />}>
                  <Route path="/staff" element={<StaffDashboard />} />
                  <Route path="/staff/availability" element={<AvailabilitySetup />} />
                  <Route path="/staff/swaps" element={<SwapInbox />} />
                </Route>

                <Route element={<ProtectedRoute allowRoles={["admin", "manager", "staff"]} />}>
                  <Route path="/settings/notifications" element={<NotificationSettings />} />
                </Route>
              </Routes>
            </RealtimeProvider>
          </BrowserRouter>
        </ToastProvider>
      </AuthProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
