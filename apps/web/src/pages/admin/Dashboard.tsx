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
