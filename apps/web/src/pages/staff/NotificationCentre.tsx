import React, { useState } from 'react';
import {
    Calendar,
    ArrowLeftRight,
    CheckCircle,
    AlertTriangle,
    XCircle,
    Bell as BellIcon,
    Eye,
} from 'lucide-react';

/* ========== Types & Mock Data ========== */

interface Notification {
    id: string;
    icon: 'calendar' | 'swap' | 'check' | 'alert' | 'x';
    title: string;
    body: string;
    time: string;
    read: boolean;
    actionLabel?: string;
}

const mockNotifications: Notification[] = [
    {
        id: '1',
        icon: 'calendar',
        title: 'Schedule Published',
        body: 'Your schedule for Aug 11–17 has been published by Jordan (Manager)',
        time: '5 minutes ago',
        read: false,
    },
    {
        id: '2',
        icon: 'swap',
        title: 'Swap Request Accepted',
        body: 'Maria L. accepted your swap for Friday Aug 15. Awaiting manager approval.',
        time: '2 hours ago',
        read: false,
        actionLabel: 'View Swap Status',
    },
    {
        id: '3',
        icon: 'check',
        title: 'Swap Approved',
        body: 'Your swap with Sam K. for Monday Aug 11 was approved by Jordan (Manager).',
        time: 'Yesterday',
        read: true,
    },
    {
        id: '4',
        icon: 'alert',
        title: 'Open Shift Available',
        body: 'A Bartender shift on Saturday Aug 16 (4pm–11pm) at Ocean Ave is open for pickup.',
        time: 'Yesterday',
        read: true,
        actionLabel: 'View & Claim',
    },
    {
        id: '5',
        icon: 'x',
        title: 'Swap Request Declined',
        body: 'Jordan (Manager) declined the swap between you and Alex R. Reason: insufficient rest period.',
        time: '2 days ago',
        read: true,
    },
];

const iconMap = {
    calendar: { Component: Calendar, color: 'text-staff-purple' },
    swap: { Component: ArrowLeftRight, color: 'text-staff-purple' },
    check: { Component: CheckCircle, color: 'text-success' },
    alert: { Component: AlertTriangle, color: 'text-amber-warn' },
    x: { Component: XCircle, color: 'text-danger' },
};

/* ========== Main Component ========== */

interface NotificationCentreProps {
    open: boolean;
    onClose: () => void;
}

export function NotificationCentre({ open, onClose }: NotificationCentreProps) {
    const [notifications, setNotifications] = useState(mockNotifications);

    if (!open) return null;

    const markAllRead = () => {
        setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    };

    const allRead = notifications.every((n) => n.read);

    return (
        <>
            {/* Backdrop */}
            <div className="fixed inset-0 z-40" onClick={onClose} />

            {/* Panel */}
            <div className="fixed top-14 right-4 z-50 w-[380px] max-h-[520px] bg-white rounded-xl shadow-2xl border border-border-gray flex flex-col animate-fade-in overflow-hidden">
                {/* Header */}
                <div className="px-5 py-4 border-b border-border-gray flex items-center justify-between flex-shrink-0">
                    <h3 className="text-base font-bold text-navy">Notifications</h3>
                    {!allRead && (
                        <button
                            onClick={markAllRead}
                            className="text-xs text-staff-purple font-semibold hover:underline"
                        >
                            Mark all read
                        </button>
                    )}
                </div>

                {/* Notification List */}
                <div className="flex-1 overflow-y-auto">
                    {notifications.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-12 text-center">
                            <BellIcon size={32} className="text-gray-300 mb-3" />
                            <h4 className="text-sm font-bold text-navy">You're all caught up!</h4>
                            <p className="text-xs text-gray-500">No new notifications.</p>
                        </div>
                    ) : (
                        <div className="divide-y divide-border-gray">
                            {notifications.map((n) => {
                                const { Component: IconComp, color } = iconMap[n.icon];

                                return (
                                    <div
                                        key={n.id}
                                        className={`flex gap-3 px-5 py-4 transition-base hover:bg-gray-50 ${!n.read
                                                ? 'bg-blue-50/50 border-l-4 border-l-staff-purple'
                                                : 'border-l-4 border-l-transparent'
                                            }`}
                                    >
                                        <div className={`mt-0.5 flex-shrink-0 ${color}`}>
                                            <IconComp size={18} />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className={`text-sm ${!n.read ? 'font-bold' : 'font-medium'} text-navy`}>
                                                {n.title}
                                            </p>
                                            <p className="text-xs text-gray-600 mt-0.5 leading-relaxed">{n.body}</p>
                                            <div className="flex items-center justify-between mt-2">
                                                <span className="text-[11px] text-gray-400">{n.time}</span>
                                                {n.actionLabel && (
                                                    <button className="text-[11px] text-staff-purple font-semibold hover:underline">
                                                        {n.actionLabel}
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="px-5 py-3 border-t border-border-gray text-center flex-shrink-0">
                    <button className="text-xs text-staff-purple font-semibold hover:underline">
                        View all notifications
                    </button>
                </div>
            </div>
        </>
    );
}
