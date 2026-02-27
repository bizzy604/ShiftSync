import React from 'react';
import {
    AlertTriangle,
    ArrowLeftRight,
    Bell as BellIcon,
    Calendar,
    CheckCircle,
    Loader2,
    XCircle,
} from 'lucide-react';
import { formatDistanceToNow, parseISO } from 'date-fns';
import { useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '../../auth/AuthContext';
import {
    useMarkAllNotificationsRead,
    useMarkNotificationRead,
    useNotifications,
} from '../../lib/api/hooks';
import { NotificationResponse, Role } from '../../lib/api/types';

/* ========== Types & Utils ========== */

const iconMap: Record<string, { Component: any; color: string }> = {
    'schedule.published': { Component: Calendar, color: 'text-staff-purple' },
    'shift.assigned': { Component: Calendar, color: 'text-staff-purple' },
    'shift.changed': { Component: Calendar, color: 'text-amber-warn' },
    'shift.unassigned': { Component: XCircle, color: 'text-danger' },
    'swap.requested': { Component: ArrowLeftRight, color: 'text-staff-purple' },
    'swap.approved': { Component: CheckCircle, color: 'text-success' },
    'swap.rejected': { Component: XCircle, color: 'text-danger' },
    'swap.cancelled': { Component: XCircle, color: 'text-gray-500' },
    'swap.manager_action_required': { Component: AlertTriangle, color: 'text-amber-warn' },
    'drop.available': { Component: AlertTriangle, color: 'text-amber-warn' },
    'drop.picked_up': { Component: CheckCircle, color: 'text-success' },
    'drop.approved': { Component: CheckCircle, color: 'text-success' },
    'drop.rejected': { Component: XCircle, color: 'text-danger' },
    'drop.expired': { Component: AlertTriangle, color: 'text-danger' },
    'staff.availability_changed': { Component: BellIcon, color: 'text-teal' },
    'staff.decertified': { Component: AlertTriangle, color: 'text-danger' },
    'overtime.warning': { Component: AlertTriangle, color: 'text-amber-warn' },
    DEFAULT: { Component: BellIcon, color: 'text-gray-400' },
};

function getIcon(type: string) {
    return iconMap[type] || iconMap.DEFAULT;
}

function formatTypeTitle(type: string) {
    return type
        .replace(/[._]/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase());
}

function requestIdFromPayload(payload: any): string | null {
    if (!payload || typeof payload !== 'object') return null;
    return payload.swapRequestId || payload.requestId || payload.dropRequestId || null;
}

function shiftIdFromPayload(payload: any): string | null {
    if (!payload || typeof payload !== 'object') return null;
    return payload.shiftId || null;
}

function withQuery(base: string, key: string, value: string | null): string {
    if (!value) return base;
    return `${base}?${key}=${encodeURIComponent(value)}`;
}

function staffDropTarget(requestId: string | null): string {
    const params = new URLSearchParams();
    params.set('open_drops', '1');
    if (requestId) params.set('requestId', requestId);
    return `/staff?${params.toString()}`;
}

function buildTarget(notification: NotificationResponse, role: Role | undefined): string {
    const requestId = requestIdFromPayload(notification.payload);
    const shiftId = shiftIdFromPayload(notification.payload);

    if (role === 'manager') {
        if (notification.type === 'overtime.warning') return '/manager/analytics';
        if (notification.type === 'swap.manager_action_required') {
            return withQuery('/manager/swaps', 'requestId', requestId);
        }
        if (notification.type.startsWith('swap.') || notification.type.startsWith('drop.')) {
            return withQuery('/manager/swaps', 'requestId', requestId);
        }
        if (notification.type === 'staff.availability_changed' || notification.type === 'staff.decertified') {
            return '/manager';
        }
        return '/manager';
    }

    if (role === 'staff') {
        if (notification.type.startsWith('swap.')) return withQuery('/staff/swaps', 'requestId', requestId);
        if (notification.type.startsWith('drop.')) return staffDropTarget(requestId);
        if (notification.type.startsWith('shift.') || notification.type === 'schedule.published') {
            return withQuery('/staff', 'shiftId', shiftId);
        }
        return '/staff';
    }

    if (role === 'admin') {
        if (notification.type === 'staff.decertified' || notification.type === 'staff.availability_changed') {
            return '/admin/staff';
        }
        return '/admin';
    }

    return '/';
}

/* ========== Main Component ========== */

interface NotificationCentreProps {
    open: boolean;
    onClose: () => void;
}

export function NotificationCentre({ open, onClose }: NotificationCentreProps) {
    const { user } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();

    const { data, isLoading } = useNotifications();
    const markAllReadMutation = useMarkAllNotificationsRead();
    const markReadMutation = useMarkNotificationRead();

    if (!open) return null;

    const notifications = data?.notifications || [];
    const unreadCount = data?.unread_count || 0;

    const handleMarkAllRead = () => {
        markAllReadMutation.mutate();
    };

    const handleNotificationClick = (notification: NotificationResponse) => {
        if (!notification.read_at && !markReadMutation.isPending) {
            markReadMutation.mutate(notification.id);
        }
        const target = buildTarget(notification, user?.role);
        const current = `${location.pathname}${location.search}`;
        if (target !== current) {
            navigate(target);
        }
        onClose();
    };

    return (
        <>
            <div className="fixed inset-0 z-40" onClick={onClose} />

            <div className="fixed top-14 left-2 right-2 md:left-auto md:right-4 z-50 w-auto md:w-[400px] max-h-[calc(100vh-4rem)] bg-white rounded-2xl sm:rounded-3xl shadow-2xl border border-border-gray flex flex-col animate-fade-in overflow-hidden">
                <div className="px-4 sm:px-6 py-5 border-b border-border-gray flex items-center justify-between flex-wrap gap-2 flex-shrink-0 bg-gray-50/50">
                    <div>
                        <h3 className="text-base font-black text-navy uppercase tracking-tight">Notifications</h3>
                        {unreadCount > 0 && (
                            <p className="text-[10px] text-staff-purple font-black uppercase tracking-widest mt-0.5">
                                {unreadCount} NEW MESSAGES
                            </p>
                        )}
                    </div>
                    {unreadCount > 0 && (
                        <button
                            onClick={handleMarkAllRead}
                            disabled={markAllReadMutation.isPending}
                            className="text-xs text-staff-purple font-black uppercase tracking-widest hover:text-staff-purple-dark transition-all disabled:opacity-50"
                        >
                            {markAllReadMutation.isPending ? 'Working...' : 'Mark all read'}
                        </button>
                    )}
                </div>

                <div className="flex-1 overflow-y-auto custom-scrollbar">
                    {isLoading ? (
                        <div className="py-20 flex flex-col items-center justify-center text-gray-300">
                            <Loader2 size={32} className="animate-spin mb-4" />
                            <span className="text-[10px] font-black uppercase tracking-widest text-gray-400">
                                Loading alerts...
                            </span>
                        </div>
                    ) : notifications.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-20 text-center px-10">
                            <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mb-4">
                                <BellIcon size={28} className="text-gray-200" />
                            </div>
                            <h4 className="text-sm font-black text-navy uppercase tracking-tight">All caught up</h4>
                            <p className="text-xs text-gray-400 font-medium leading-relaxed mt-1">
                                No notifications for you right now. We will alert you here when something important
                                happens.
                            </p>
                        </div>
                    ) : (
                        <div className="divide-y divide-border-gray">
                            {notifications.map((notification) => {
                                const { Component: IconComp, color } = getIcon(notification.type);
                                const isUnread = !notification.read_at;

                                return (
                                    <button
                                        key={notification.id}
                                        type="button"
                                        onClick={() => handleNotificationClick(notification)}
                                        className={`w-full text-left flex gap-4 px-4 sm:px-6 py-5 transition-all hover:bg-gray-50 group ${isUnread
                                            ? 'bg-staff-purple/5 border-l-4 border-l-staff-purple'
                                            : 'border-l-4 border-l-transparent'
                                            }`}
                                    >
                                        <div
                                            className={`mt-1 flex-shrink-0 p-2 rounded-xl ${isUnread ? 'bg-white shadow-sm' : 'bg-gray-50'
                                                } ${color}`}
                                        >
                                            <IconComp size={20} />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-start justify-between gap-2 mb-1">
                                                <p
                                                    className={`text-sm ${isUnread ? 'font-black' : 'font-bold'
                                                        } text-navy leading-tight`}
                                                >
                                                    {formatTypeTitle(notification.type)}
                                                </p>
                                                <span className="text-[10px] text-gray-400 font-bold uppercase tracking-tight whitespace-nowrap">
                                                    {formatDistanceToNow(parseISO(notification.created_at), {
                                                        addSuffix: true,
                                                    })}
                                                </span>
                                            </div>
                                            <p className="text-xs text-gray-500 font-medium leading-relaxed mb-2">
                                                {notification.message}
                                            </p>
                                            <span className="text-[10px] text-staff-purple font-black uppercase tracking-widest">
                                                Open
                                            </span>
                                        </div>
                                    </button>
                                );
                            })}
                        </div>
                    )}
                </div>

                <div className="px-4 sm:px-6 py-4 border-t border-border-gray bg-gray-50/30 text-center flex-shrink-0">
                    <p className="text-[10px] text-gray-400 font-black uppercase tracking-widest">
                        Click a notification to open the related screen
                    </p>
                </div>
            </div>
        </>
    );
}
