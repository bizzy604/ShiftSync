/**
 * @file /apps/web/src/auth/ProtectedRoute.tsx
 *
 * @description
 * Authentication and route-guard module for `ProtectedRoute` behavior.
 *
 * @dependencies
 * - (No in-repo dependents detected.)
 *
 * @importance
 * This module is critical for application access flow and role-based navigation
 * safety.
 */

import { Navigate, Outlet } from "react-router-dom";

import { Role } from "../lib/api";
import { useAuth } from "./AuthContext";

type Props = {
  allowRoles?: Role[];
};

export function ProtectedRoute({ allowRoles }: Props) {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="center-screen">Loading session...</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowRoles && !allowRoles.includes(user.role)) {
    return <Navigate to={`/${user.role}`} replace />;
  }

  return <Outlet />;
}
