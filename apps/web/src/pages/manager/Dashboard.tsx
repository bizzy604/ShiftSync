/**
 * @file /apps/web/src/pages/manager/Dashboard.tsx
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
import { ScheduleBuilder } from './ScheduleBuilder';

/**
 * Manager dashboard entry that renders the planner at the index route
 * and nested manager pages for sub-routes.
 */
export function ManagerDashboard() {
  const location = useLocation();

  // If on the base manager path, show the Schedule Builder
  if (location.pathname === '/manager') {
    return <ScheduleBuilder />;
  }

  return <Outlet />;
}
