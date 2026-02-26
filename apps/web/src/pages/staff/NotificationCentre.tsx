import React from 'react';
import {
    Calendar,
    ArrowLeftRight,
    CheckCircle,
    AlertTriangle,
    XCircle,
    Bell as BellIcon,
    Loader2,
} from 'lucide-react';
import { useNotifications, useMarkAllNotificationsRead } from '../../lib/api/hooks';
import { formatDistanceToNow, parseISO } from 'date-fns';

/* ========== Types & Utils ========== */

const iconMap: Record<string, { Component: any; color: string }> = {
    'SHIFT_PUBLISHED': { Component: Calendar, color: 'text-staff-purple' },
    'SWAP_REQUEST_RECEIVED': { Component: ArrowLeftRight, color: 'text-staff-purple' },
    'SWAP_REQUEST_ACCEPTED': { Component: ArrowLeftRight, color: 'text-staff-purple' },
    'SWAP_REQUEST_APPROVED': { Component: CheckCircle, color: 'text-success' },
    'DROP_REQUEST_APPROVED': { Component: CheckCircle, color: 'text-success' },
    'DROP_REQUEST_RECEIVED': { Component: AlertTriangle, color: 'text-amber-warn' },
    'SWAP_REQUEST_DECLINED': { Component: XCircle, color: 'text-danger' },
    'DROP_REQUEST_DECLINED': { Component: XCircle, color: 'text-danger' },
    'DEFAULT': { Component: BellIcon, color: 'text-gray-400' },
};

function getIcon(type: string) {
    return iconMap[type] || iconMap['DEFAULT'];
}

/* ========== Main Component ========== */

interface NotificationCentreProps {
    open: boolean;
    onClose: () => void;
}

export function NotificationCentre({ open, onClose }: NotificationCentreProps) {
    const { data, isLoading } = useNotifications();
    const markAllReadMutation = useMarkAllNotificationsRead();

    if (!open) return null;

    const notifications = data?.notifications || [];
    const unreadCount = data?.unread_count || 0;

    const handleMarkAllRead = () => {
        markAllReadMutation.mutate();
    };

    return (
        <>
            {/* Backdrop */}
            <div className="fixed inset-0 z-40" onClick={onClose} />

            {/* Panel */}
            <div className="fixed top-14 right-4 z-50 w-[400px] max-h-[600px] bg-white rounded-3xl shadow-2xl border border-border-gray flex flex-col animate-fade-in overflow-hidden">
                {/* Header */}
                <div className="px-6 py-5 border-b border-border-gray flex items-center justify-between flex-shrink-0 bg-gray-50/50">
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

                {/* Notification List */}
                <div className="flex-1 overflow-y-auto custom-scrollbar">
                    {isLoading ? (
                        <div className="py-20 flex flex-col items-center justify-center text-gray-300">
                            <Loader2 size={32} className="animate-spin mb-4" />
                            <span className="text-[10px] font-black uppercase tracking-widest text-gray-400">Loading alerts…</span>
                        </div>
                    ) : notifications.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-20 text-center px-10">
                            <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mb-4">
                                <BellIcon size={28} className="text-gray-200" />
                            </div>
                            <h4 className="text-sm font-black text-navy uppercase tracking-tight">All caught up</h4>
                            <p className="text-xs text-gray-400 font-medium leading-relaxed mt-1">
                                No notifications for you right now. We'll alert you here when something important happens.
                            </p>
                        </div>
                    ) : (
                        <div className="divide-y divide-border-gray">
                            {notifications.map((n) => {
                                const { Component: IconComp, color } = getIcon(n.type);
                                const isUnread = !n.read_at;

                                return (
                                    <div
                                        key={n.id}
                                        className={`flex gap-4 px-6 py-5 transition-all hover:bg-gray-50 group ${isUnread
                                            ? 'bg-staff-purple/5 border-l-4 border-l-staff-purple'
                                            : 'border-l-4 border-l-transparent'
                                            }`}
                                    >
                                        <div className={`mt-1 flex-shrink-0 p-2 rounded-xl ${isUnread ? 'bg-white shadow-sm' : 'bg-gray-50'} ${color}`}>
                                            <IconComp size={20} />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-start justify-between gap-2 mb-1">
                                                <p className={`text-sm ${isUnread ? 'font-black' : 'font-bold'} text-navy leading-tight`}>
                                                    {n.type.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase())}
                                                </p>
                                                <span className="text-[10px] text-gray-400 font-bold uppercase tracking-tight whitespace-nowrap">
                                                    {formatDistanceToNow(parseISO(n.created_at), { addSuffix: true })}
                                                </span>
                                            </div>
                                            <p className="text-xs text-gray-500 font-medium leading-relaxed mb-2">{n.message}</p>

                                            {n.payload?.link && (
                                                <button className="text-[10px] text-staff-purple font-black uppercase tracking-widest hover:underline transition-all">
                                                    View Details →
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="px-6 py-4 border-t border-border-gray bg-gray-50/30 text-center flex-shrink-0">
                    <button className="text-[10px] text-gray-400 font-black uppercase tracking-widest hover:text-navy transition-all">
                        Archive All Activity
                    </button>
                </div>
            </div>
        </>
    );
}
