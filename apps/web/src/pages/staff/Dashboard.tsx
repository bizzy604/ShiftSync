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
