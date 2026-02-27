import React, { useEffect, useMemo, useState } from 'react';
import { Bell, CheckCircle2, Loader2, Mail } from 'lucide-react';

import { useAuth } from '../../auth/AuthContext';
import { AppLayout } from '../../components/NavBar';
import { Badge } from '../../components/Badge';
import {
    useNotificationPreferences,
    useNotifications,
    useUpdateNotificationPreferences,
} from '../../lib/api/hooks';
import { NotificationPref } from '../../lib/api/types';
import { NotificationCentre } from '../staff/NotificationCentre';

const CHANNEL_OPTIONS: { value: NotificationPref; title: string; description: string; icon: React.ReactNode }[] = [
    {
        value: 'in_app',
        title: 'In-app only',
        description: 'Receive alerts in ShiftSync only.',
        icon: <Bell size={18} />,
    },
    {
        value: 'in_app_email',
        title: 'In-app + email',
        description: 'Receive alerts in ShiftSync and by email.',
        icon: <Mail size={18} />,
    },
];

function prefLabel(pref: NotificationPref) {
    return pref === 'in_app_email' ? 'In-app + email' : 'In-app only';
}

export function NotificationSettings() {
    const { user } = useAuth();
    const [isNotificationOpen, setIsNotificationOpen] = useState(false);
    const [selectedPref, setSelectedPref] = useState<NotificationPref>('in_app');

    const { data: notificationsData } = useNotifications();
    const { data: prefData, isLoading: isLoadingPref } = useNotificationPreferences();
    const updatePrefMutation = useUpdateNotificationPreferences();
    const unreadCount = notificationsData?.unread_count || 0;

    useEffect(() => {
        if (prefData?.notification_pref) {
            setSelectedPref(prefData.notification_pref);
        }
    }, [prefData?.notification_pref]);

    const hasChanges = useMemo(
        () => !!prefData && selectedPref !== prefData.notification_pref,
        [prefData, selectedPref]
    );

    if (!user) return null;

    return (
        <AppLayout
            title="Notification Settings"
            role={user.role}
            notificationCount={unreadCount}
            onBellClick={() => setIsNotificationOpen(true)}
        >
            <div className="max-w-3xl mx-auto p-4 md:p-6">
                <div className="mb-6">
                    <p className="text-xs text-gray-500 mb-1">Account &gt; Notification Settings</p>
                    <h1 className="text-xl sm:text-2xl font-bold text-navy">Notification Settings</h1>
                    <p className="text-sm text-gray-500 mt-1">
                        Choose how ShiftSync sends your alerts.
                    </p>
                </div>

                <div className="bg-white rounded-xl border border-border-gray shadow-sm p-4 sm:p-5">
                    {isLoadingPref ? (
                        <div className="py-12 flex flex-col items-center text-gray-400">
                            <Loader2 size={28} className="animate-spin mb-3" />
                            <p>Loading notification preferences...</p>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {CHANNEL_OPTIONS.map((option) => {
                                const selected = selectedPref === option.value;
                                return (
                                    <button
                                        key={option.value}
                                        type="button"
                                        onClick={() => setSelectedPref(option.value)}
                                        className={`w-full text-left p-4 rounded-xl border transition-base flex items-start gap-3 ${selected
                                            ? 'border-teal bg-teal/5'
                                            : 'border-border-gray hover:bg-gray-50'
                                            }`}
                                    >
                                        <div className={`p-2 rounded-lg ${selected ? 'bg-teal/10 text-teal' : 'bg-gray-100 text-gray-500'}`}>
                                            {option.icon}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-semibold text-navy">{option.title}</p>
                                            <p className="text-xs text-gray-500 mt-1">{option.description}</p>
                                        </div>
                                        {selected && <CheckCircle2 size={18} className="text-teal mt-0.5" />}
                                    </button>
                                );
                            })}
                        </div>
                    )}

                    <div className="mt-5 pt-4 border-t border-border-gray flex items-center justify-between gap-3 flex-wrap">
                        <div className="flex items-center gap-2">
                            <span className="text-xs text-gray-500">Current channel:</span>
                            <Badge variant="slate">{prefLabel(selectedPref)}</Badge>
                        </div>
                        <button
                            onClick={() => updatePrefMutation.mutate({ notification_pref: selectedPref })}
                            disabled={!hasChanges || updatePrefMutation.isPending || isLoadingPref}
                            className="w-full sm:w-auto px-5 py-2.5 rounded-lg bg-teal text-white text-sm font-semibold hover:bg-teal-dark transition-base disabled:opacity-50"
                        >
                            {updatePrefMutation.isPending ? 'Saving...' : 'Save Preferences'}
                        </button>
                    </div>
                </div>

                <div className="mt-5 text-xs text-gray-500 bg-gray-50 border border-border-gray rounded-lg p-3">
                    In this environment, emails are simulated and written to `simulated_emails.log` when your channel is set to `In-app + email`.
                </div>
            </div>

            <NotificationCentre
                open={isNotificationOpen}
                onClose={() => setIsNotificationOpen(false)}
            />
        </AppLayout>
    );
}

