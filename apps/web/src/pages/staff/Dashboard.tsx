/**
 * @file /apps/web/src/pages/staff/Dashboard.tsx
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

import React, { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { MySchedule } from './MySchedule';
import { NotificationCentre } from './NotificationCentre';

export function StaffDashboard() {
  const location = useLocation();
  const [showNotifications, setShowNotifications] = useState(false);

  if (location.pathname === '/staff') {
    return (
      <>
        <MySchedule />
        <NotificationCentre open={showNotifications} onClose={() => setShowNotifications(false)} />
      </>
    );
  }

  return <Outlet />;
}
