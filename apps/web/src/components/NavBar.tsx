import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
    Bell,
    Calendar,
    ChevronDown,
    ChevronLeft,
    ChevronRight,
    LayoutDashboard,
    LogOut,
    Menu,
    Users,
    FileText,
    Clock,
    ArrowLeftRight,
    BarChart3,
    AlertTriangle,
    Settings,
    X,
} from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { Avatar } from './Avatar';

interface NavBarProps {
    centerContent?: React.ReactNode;
    notificationCount?: number;
    onBellClick?: () => void;
}

export function NavBar({ centerContent, notificationCount = 0, onBellClick }: NavBarProps) {
    const { user, logout } = useAuth();
    const navigate = useNavigate();

    return (
        <header className="bg-navy text-white h-14 flex items-center px-4 gap-4 shadow-md z-40 flex-shrink-0">
            {/* Left — Logo */}
            <Link to={`/${user?.role}`} className="flex items-center gap-2 hover:opacity-90 transition-base">
                <Calendar size={22} className="text-teal-light" />
                <span className="text-lg font-bold tracking-tight">ShiftSync</span>
            </Link>

            {/* Center */}
            <div className="flex-1 flex items-center justify-center">{centerContent}</div>

            {/* Right */}
            <div className="flex items-center gap-3">
                <button
                    onClick={onBellClick}
                    className="relative p-2 rounded-lg hover:bg-white/10 transition-base"
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
                    <span className="text-sm font-medium hidden md:block">{user?.name}</span>
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
];

const staffNavItems: NavItem[] = [
    { label: 'My Schedule', path: '/staff', icon: <Calendar size={18} /> },
    { label: 'Swap Inbox', path: '/staff/swaps', icon: <ArrowLeftRight size={18} /> },
    { label: 'Availability', path: '/staff/availability', icon: <Clock size={18} /> },
];

const adminNavItems: NavItem[] = [
    { label: 'Overview', path: '/admin', icon: <LayoutDashboard size={18} /> },
    { label: 'Staff Management', path: '/admin/staff', icon: <Users size={18} /> },
    { label: 'Audit Log', path: '/admin/audit', icon: <FileText size={18} /> },
];

interface SidebarProps {
    role: 'admin' | 'manager' | 'staff';
    children?: React.ReactNode;
}

export function Sidebar({ role, children }: SidebarProps) {
    const location = useLocation();
    const items = role === 'admin' ? adminNavItems : role === 'manager' ? managerNavItems : staffNavItems;

    const accentColor = role === 'admin' ? 'admin-slate' : role === 'manager' ? 'teal' : 'staff-purple';

    return (
        <aside className="w-56 bg-gray-bg border-r border-border-gray flex flex-col flex-shrink-0">
            <nav className="p-3 space-y-1">
                {items.map((item) => {
                    const isActive = location.pathname === item.path;
                    return (
                        <Link
                            key={item.path}
                            to={item.path}
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
            {children && <div className="flex-1 overflow-y-auto">{children}</div>}
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
    children: React.ReactNode;
}

export function AppLayout({
    title,
    role,
    centerContent,
    sidebar,
    notificationCount,
    onBellClick,
    children,
}: AppLayoutProps) {
    return (
        <div className="app-shell">
            <NavBar
                centerContent={centerContent}
                notificationCount={notificationCount}
                onBellClick={onBellClick}
            />
            <div className="flex flex-1 overflow-hidden">
                <Sidebar role={role}>{sidebar}</Sidebar>
                <main className="flex-1 overflow-y-auto">{children}</main>
            </div>
        </div>
    );
}
