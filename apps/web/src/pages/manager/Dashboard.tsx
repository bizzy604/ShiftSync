import React, { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { ScheduleBuilder } from './ScheduleBuilder';

export function ManagerDashboard() {
  const location = useLocation();

  // If on the base manager path, show the Schedule Builder
  if (location.pathname === '/manager') {
    return <ScheduleBuilder />;
  }

  return <Outlet />;
}
