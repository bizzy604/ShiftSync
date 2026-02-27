/**
 * @file /apps/web/src/pages/admin/Dashboard.tsx
 *
 * @description
 * UI page module for `Dashboard` workflows and role-specific interaction flows.
 *
 * @dependencies
 * - (No in-repo dependents detected.)
 *
 * @importance
 * This module defines user-facing workflows; changes here affect day-to-day product
 * usability.
 */

import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { AdminOverview } from './AdminOverview';

export function AdminDashboard() {
  const location = useLocation();

  if (location.pathname === '/admin') {
    return <AdminOverview />;
  }

  return <Outlet />;
}
