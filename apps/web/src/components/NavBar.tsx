/**
 * @file /apps/web/src/components/NavBar.tsx
 *
 * @description
 * Shared UI/component module for `NavBar` used across multiple screens.
 *
 * @dependencies
 * - (No in-repo dependents detected.)
 *
 * @importance
 * This module provides reusable UI primitives that influence consistency and
 * maintainability.
 */

import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
    ArrowLeftRight,
    BarChart3,
    Bell,
    Calendar,
    Clock,
    FileText,
    LayoutDashboard,
    LogOut,
    Menu,
    Settings,
    Users,
} from 'lucide-react';

import { useAuth } from '../auth/AuthContext';
import { Avatar } from './Avatar';

interface NavBarProps {
    centerContent?: React.ReactNode;
    notificationCount?: number;
    onBellClick?: () => void;
    onMenuClick?: () => void;
}

export function NavBar({ centerContent, notificationCount = 0, onBellClick, onMenuClick }: NavBarProps) {
    const { user, logout } = useAuth();
    const navigate = useNavigate();

    return (
        <header className="bg-navy text-white h-14 flex items-center px-3 md:px-4 gap-3 md:gap-4 shadow-md z-40 flex-shrink-0">
            <button
                onClick={onMenuClick}
                className="md:hidden p-2 rounded-lg hover:bg-white/10 transition-base"
                aria-label="Toggle navigation"
            >
                <Menu size={18} />
            </button>

            <Link to={`/${user?.role}`} className="flex items-center gap-2 hover:opacity-90 transition-base">
                <Calendar size={20} className="text-teal-light" />
                <span className="text-base md:text-lg font-bold tracking-tight">ShiftSync</span>
            </Link>

            <div className="flex-1 min-w-0 flex items-center justify-center overflow-x-auto px-1 [&>*]:shrink-0">
                {centerContent}
            </div>

            <div className="flex items-center gap-2 md:gap-3 ml-auto">
                <button
                    onClick={onBellClick}
                    className="relative p-2 rounded-lg hover:bg-white/10 transition-base"
                    aria-label="Open notifications"
                >
                    <Bell size={20} />
                    {notificationCount > 0 && (
                        <span className="absolute -top-0.5 -right-0.5 w-5 h-5 bg-danger text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                            {notificationCount}
                        </span>
                    )}
                </button>
                <div className="flex items-center gap-2">
                    <Avatar name={user?.name ?? 'User'} size="sm" color="bg-teal" />
                    <span className="text-sm font-medium hidden lg:block max-w-[140px] truncate">{user?.name}</span>
                </div>
                <button
                    onClick={async () => {
                        await logout();
                        navigate('/login');
                    }}
                    className="p-2 rounded-lg hover:bg-white/10 transition-base"
                    title="Sign out"
                >
                    <LogOut size={18} />
                </button>
            </div>
        </header>
    );
}

/* ========== Sidebar Navigation ========== */

interface NavItem {
    label: string;
    path: string;
    icon: React.ReactNode;
}

const managerNavItems: NavItem[] = [
    { label: 'Schedule Builder', path: '/manager', icon: <Calendar size={18} /> },
    { label: 'Swap Requests', path: '/manager/swaps', icon: <ArrowLeftRight size={18} /> },
    { label: 'Analytics', path: '/manager/analytics', icon: <BarChart3 size={18} /> },
    { label: 'Shift History', path: '/manager/history', icon: <FileText size={18} /> },
    { label: 'Notifications', path: '/settings/notifications', icon: <Bell size={18} /> },
];

const staffNavItems: NavItem[] = [
    { label: 'My Schedule', path: '/staff', icon: <Calendar size={18} /> },
    { label: 'Swap Inbox', path: '/staff/swaps', icon: <ArrowLeftRight size={18} /> },
    { label: 'Availability', path: '/staff/availability', icon: <Clock size={18} /> },
    { label: 'Notifications', path: '/settings/notifications', icon: <Bell size={18} /> },
];

const adminNavItems: NavItem[] = [
    { label: 'Overview', path: '/admin', icon: <LayoutDashboard size={18} /> },
    { label: 'Staff Management', path: '/admin/staff', icon: <Users size={18} /> },
    { label: 'Skill Catalog', path: '/admin/skills', icon: <Settings size={18} /> },
    { label: 'Audit Log', path: '/admin/audit', icon: <FileText size={18} /> },
    { label: 'Notifications', path: '/settings/notifications', icon: <Bell size={18} /> },
    { label: 'Ops Mode', path: '/manager', icon: <Calendar size={18} /> },
];

interface SidebarProps {
    role: 'admin' | 'manager' | 'staff';
    onNavigate?: () => void;
    children?: React.ReactNode;
    className?: string;
    showChildren?: boolean;
}

export function Sidebar({ role, onNavigate, children, className = '', showChildren = true }: SidebarProps) {
    const location = useLocation();
    const items = role === 'admin' ? adminNavItems : role === 'manager' ? managerNavItems : staffNavItems;

    const accentColor = role === 'admin' ? 'admin-slate' : role === 'manager' ? 'teal' : 'staff-purple';

    return (
        <aside className={`w-56 h-full bg-gray-bg border-r border-border-gray flex flex-col flex-shrink-0 ${className}`}>
            <nav className="p-3 space-y-1">
                {items.map((item) => {
                    const isActive = location.pathname === item.path;
                    return (
                        <Link
                            key={item.path}
                            to={item.path}
                            onClick={onNavigate}
                            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-base ${isActive
                                ? `bg-${accentColor}/10 text-${accentColor} border-l-3 border-${accentColor}`
                                : 'text-gray-600 hover:bg-gray-200 hover:text-navy'
                                }`}
                            style={
                                isActive
                                    ? {
                                        backgroundColor:
                                            role === 'admin'
                                                ? 'rgba(58,79,102,0.1)'
                                                : role === 'manager'
                                                    ? 'rgba(10,124,110,0.1)'
                                                    : 'rgba(92,61,143,0.1)',
                                        color:
                                            role === 'admin'
                                                ? '#3A4F66'
                                                : role === 'manager'
                                                    ? '#0A7C6E'
                                                    : '#5C3D8F',
                                    }
                                    : {}
                            }
                        >
                            {item.icon}
                            {item.label}
                        </Link>
                    );
                })}
            </nav>
            {showChildren && children && <div className="flex-1 overflow-y-auto">{children}</div>}
        </aside>
    );
}

/* ========== App Layout with NavBar + Sidebar ========== */

interface AppLayoutProps {
    title: string;
    role: 'admin' | 'manager' | 'staff';
    centerContent?: React.ReactNode;
    sidebar?: React.ReactNode;
    notificationCount?: number;
    onBellClick?: () => void;
    mainClassName?: string;
    children: React.ReactNode;
}

export function AppLayout({
    title,
    role,
    centerContent,
    sidebar,
    notificationCount,
    onBellClick,
    mainClassName,
    children,
}: AppLayoutProps) {
    const [mobileNavOpen, setMobileNavOpen] = useState(false);

    return (
        <div className="app-shell">
            <NavBar
                centerContent={centerContent}
                notificationCount={notificationCount}
                onBellClick={onBellClick}
                onMenuClick={() => setMobileNavOpen((prev) => !prev)}
            />
            <div className="flex flex-1 overflow-hidden">
                <div className="hidden md:block">
                    <Sidebar role={role}>{sidebar}</Sidebar>
                </div>

                {mobileNavOpen && (
                    <>
                        <button
                            type="button"
                            className="fixed top-14 inset-x-0 bottom-0 bg-black/30 z-30 md:hidden"
                            onClick={() => setMobileNavOpen(false)}
                            aria-label="Close navigation"
                        />
                        <div className="fixed top-14 bottom-0 left-0 z-40 md:hidden w-[86vw] max-w-[320px]">
                            <Sidebar
                                role={role}
                                onNavigate={() => setMobileNavOpen(false)}
                                className="w-full h-full"
                                showChildren={false}
                            />
                        </div>
                    </>
                )}

                <main className={`flex-1 overflow-y-auto min-w-0 ${mainClassName ?? ''}`}>{children}</main>
            </div>
        </div>
    );
}
