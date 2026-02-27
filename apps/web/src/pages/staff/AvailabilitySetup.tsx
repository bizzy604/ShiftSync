/**
 * @file /apps/web/src/pages/staff/AvailabilitySetup.tsx
 *
 * @description
 * UI page module for `AvailabilitySetup` workflows and role-specific interaction
 * flows.
 *
 * @dependencies
 * - (No in-repo dependents detected.)
 *
 * @importance
 * This module defines user-facing workflows; changes here affect day-to-day product
 * usability.
 */

import React, { useState, useEffect } from 'react';
import { Save, Plus, X, Info, Clock, Loader2 } from 'lucide-react';
import { AppLayout } from '../../components/NavBar';
import { Badge } from '../../components/Badge';
import { Modal } from '../../components/Modal';
import { NotificationCentre } from './NotificationCentre';
import { useMe, useUserAvailability, useUpdateAvailability, useNotifications } from '../../lib/api/hooks';
import { format, parseISO } from 'date-fns';

/* ========== Types & Utils ========== */

interface DayAvailability {
    day: string;
    dayNum: number;
    available: boolean;
    startTime: string;
    endTime: string;
}

interface Exception {
    id: string;
    date: string;
    rawDate: string;
    type: 'unavailable' | 'available';
    startTime?: string;
    endTime?: string;
}

const DAYS = [
    { name: 'Monday', num: 0 },
    { name: 'Tuesday', num: 1 },
    { name: 'Wednesday', num: 2 },
    { name: 'Thursday', num: 3 },
    { name: 'Friday', num: 4 },
    { name: 'Saturday', num: 5 },
    { name: 'Sunday', num: 6 },
];

const timeOptions: string[] = [];
for (let h = 0; h < 24; h++) {
    for (const m of ['00', '30']) {
        const hour = h.toString().padStart(2, '0');
        timeOptions.push(`${hour}:${m}`);
    }
}

function formatTime(time: string): string {
    if (!time) return '';
    const [h, m] = time.split(':').map(Number);
    const ampm = h >= 12 ? 'PM' : 'AM';
    const displayH = h === 0 ? 12 : h > 12 ? h - 12 : h;
    return `${displayH}:${m.toString().padStart(2, '0')} ${ampm}`;
}

function toIsoDate(rawDate: string): string {
    return rawDate.includes('T') ? rawDate.split('T')[0] : rawDate;
}

const DEFAULT_START = '09:00';
const DEFAULT_END = '17:00';

/* ========== Main Component ========== */

export function AvailabilitySetup() {
    const { data: me } = useMe();
    const { data: availData, isLoading } = useUserAvailability(me?.id || '');
    const updateAvailability = useUpdateAvailability();

    const [availability, setAvailability] = useState<DayAvailability[]>([]);
    const [exceptions, setExceptions] = useState<Exception[]>([]);
    const [hasChanges, setHasChanges] = useState(false);
    const [showAddException, setShowAddException] = useState(false);
    const [isNotificationOpen, setIsNotificationOpen] = useState(false);

    // Notifications data
    const { data: notificationsData } = useNotifications();
    const unreadCount = notificationsData?.unread_count || 0;

    const [newExceptionDate, setNewExceptionDate] = useState('');
    const [newExceptionType, setNewExceptionType] = useState<'unavailable' | 'available'>('unavailable');
    const [newExceptionStartTime, setNewExceptionStartTime] = useState(DEFAULT_START);
    const [newExceptionEndTime, setNewExceptionEndTime] = useState(DEFAULT_END);

    // Initialize state from API data
    useEffect(() => {
        if (!availData) return;

        // Map recurring
        const recurringMap = new Map();
        availData.recurring.forEach(r => {
            if (r.day_of_week !== null) {
                recurringMap.set(r.day_of_week, r);
            }
        });

        const initialAvail = DAYS.map(d => {
            const entry = recurringMap.get(d.num);
            return {
                day: d.name,
                dayNum: d.num,
                available: !!entry,
                startTime: entry?.start_clock || DEFAULT_START,
                endTime: entry?.end_clock || DEFAULT_END,
            };
        });
        setAvailability(initialAvail);

        // Map exceptions
        const initialExceptions: Exception[] = availData.exceptions
            .filter((ex) => !!ex.specific_date)
            .map((ex) => {
                const rawDate = toIsoDate(ex.specific_date!);
                return {
                    id: ex.id,
                    date: format(parseISO(rawDate), 'MMM d, yyyy'),
                    rawDate,
                    type: (ex.is_available ? 'available' : 'unavailable') as 'available' | 'unavailable',
                    startTime: ex.start_clock || undefined,
                    endTime: ex.end_clock || undefined,
                };
            });
        setExceptions(initialExceptions);
        setHasChanges(false);
    }, [availData]);

    const toggleDay = (index: number) => {
        setAvailability((prev) => {
            const next = [...prev];
            next[index] = { ...next[index], available: !next[index].available };
            return next;
        });
        setHasChanges(true);
    };

    const updateTime = (index: number, field: 'startTime' | 'endTime', value: string) => {
        setAvailability((prev) => {
            const next = [...prev];
            next[index] = { ...next[index], [field]: value };
            return next;
        });
        setHasChanges(true);
    };

    const removeException = (id: string) => {
        setExceptions((prev) => prev.filter((e) => e.id !== id));
        setHasChanges(true);
    };

    const addException = () => {
        if (!newExceptionDate) return;
        const startTime = newExceptionType === 'available' ? newExceptionStartTime : undefined;
        const endTime = newExceptionType === 'available' ? newExceptionEndTime : undefined;
        setExceptions((prev) => [
            ...prev,
            {
                id: `temp-${Date.now()}`,
                date: format(parseISO(newExceptionDate), 'MMM d, yyyy'),
                rawDate: newExceptionDate,
                type: newExceptionType,
                startTime,
                endTime,
            },
        ]);
        setShowAddException(false);
        setNewExceptionDate('');
        setNewExceptionType('unavailable');
        setNewExceptionStartTime(DEFAULT_START);
        setNewExceptionEndTime(DEFAULT_END);
        setHasChanges(true);
    };

    const handleSave = () => {
        if (!me) return;

        const payload = {
            recurring: availability
                .filter(a => a.available)
                .map(a => ({
                    day_of_week: a.dayNum,
                    start_clock_time: a.startTime,
                    end_clock_time: a.endTime
                })),
            exceptions: exceptions.map(ex => ({
                date: toIsoDate(ex.rawDate),
                is_available: ex.type === 'available',
                start_clock_time: ex.type === 'available' ? (ex.startTime || '09:00') : undefined,
                end_clock_time: ex.type === 'available' ? (ex.endTime || '17:00') : undefined
            }))
        };

        updateAvailability.mutate({ id: me.id, data: payload as any }, {
            onSuccess: () => {
                setHasChanges(false);
            }
        });
    };

    if (isLoading) {
        return (
            <AppLayout
                title="Availability"
                role="staff"
                notificationCount={unreadCount}
                onBellClick={() => setIsNotificationOpen(true)}
            >
                <div className="flex items-center justify-center py-40">
                    <Loader2 className="animate-spin text-staff-purple" size={40} />
                </div>

                <NotificationCentre
                    open={isNotificationOpen}
                    onClose={() => setIsNotificationOpen(false)}
                />
            </AppLayout>
        );
    }

    return (
        <AppLayout
            title="Availability"
            role="staff"
            notificationCount={unreadCount}
            onBellClick={() => setIsNotificationOpen(true)}
        >
            <div className="max-w-3xl mx-auto p-4 md:p-6">
                {/* Header */}
                <div className="flex items-start justify-between mb-6 gap-3 flex-wrap">
                    <div>
                        <h1 className="text-xl sm:text-2xl font-black text-navy uppercase tracking-tight">My Availability</h1>
                        <p className="text-sm text-gray-500 mt-1">
                            Current Timezone: <span className="font-bold text-staff-purple">{me?.home_timezone || 'America/Los_Angeles'}</span>
                        </p>
                    </div>
                    <button
                        onClick={handleSave}
                        disabled={!hasChanges || updateAvailability.isPending}
                        className={`w-full sm:w-auto justify-center px-6 py-2.5 text-sm font-black uppercase tracking-widest rounded-xl transition-all flex items-center gap-2 shadow-lg active:scale-95 ${hasChanges
                            ? 'bg-teal text-white hover:bg-teal-dark'
                            : 'bg-gray-100 text-gray-400 cursor-not-allowed shadow-none'
                            }`}
                    >
                        {updateAvailability.isPending ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                        {updateAvailability.isPending ? 'Saving...' : 'Save Changes'}
                    </button>
                </div>

                {/* Weekly Recurring Availability */}
                <div className="bg-white rounded-2xl border border-border-gray shadow-sm mb-6 overflow-hidden">
                    <div className="px-6 py-4 bg-gray-50 border-b border-border-gray">
                        <h2 className="text-xs font-black text-navy uppercase tracking-widest">Weekly Recurring Availability</h2>
                    </div>
                    <div className="divide-y divide-border-gray">
                        {availability.map((day, i) => (
                            <div
                                key={day.day}
                                className={`flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4 px-4 sm:px-6 py-4 sm:py-5 ${!day.available ? 'bg-gray-50/50 opacity-60' : ''}`}
                            >
                                <span className="w-full sm:w-24 text-sm font-black text-navy uppercase">{day.day}</span>

                                {/* Toggle */}
                                <button
                                    onClick={() => toggleDay(i)}
                                    className={`relative w-12 h-6 rounded-full transition-all duration-300 ${day.available ? 'bg-staff-purple' : 'bg-gray-300'
                                        }`}
                                >
                                    <span
                                        className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow-md transition-all duration-300 ${day.available ? 'translate-x-6' : 'translate-x-0'
                                            }`}
                                    />
                                </button>

                                {day.available ? (
                                    <div className="flex flex-wrap items-center gap-2 w-full sm:flex-1 animate-fade-in">
                                        <div className="relative">
                                            <select
                                                value={day.startTime}
                                                onChange={(e) => updateTime(i, 'startTime', e.target.value)}
                                                className="pl-3 pr-8 py-2 rounded-xl border border-border-gray bg-white text-xs font-bold text-navy appearance-none focus:ring-2 focus:ring-staff-purple/20 transition-all outline-none"
                                            >
                                                {timeOptions.map((t) => (
                                                    <option key={t} value={t}>
                                                        {formatTime(t)}
                                                    </option>
                                                ))}
                                            </select>
                                            <Clock size={12} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                                        </div>
                                        <span className="text-gray-300 font-bold">—</span>
                                        <div className="relative">
                                            <select
                                                value={day.endTime}
                                                onChange={(e) => updateTime(i, 'endTime', e.target.value)}
                                                className="pl-3 pr-8 py-2 rounded-xl border border-border-gray bg-white text-xs font-bold text-navy appearance-none focus:ring-2 focus:ring-staff-purple/20 transition-all outline-none"
                                            >
                                                {timeOptions.map((t) => (
                                                    <option key={t} value={t}>
                                                        {formatTime(t)}
                                                    </option>
                                                ))}
                                            </select>
                                            <Clock size={12} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                                        </div>
                                    </div>
                                ) : (
                                    <span className="text-xs text-gray-400 font-bold uppercase tracking-widest italic w-full sm:w-auto">Unavailable</span>
                                )}
                            </div>
                        ))}
                    </div>
                </div>

                {/* Info callout */}
                <div className="flex items-start gap-3 mb-8 px-5 py-4 bg-navy/5 border border-navy/10 rounded-2xl">
                    <Info size={18} className="text-staff-purple flex-shrink-0 mt-0.5" />
                    <p className="text-xs text-navy font-medium leading-relaxed">
                        Changes take effect for future schedules. Regular shifts already assigned to you will not be automatically updated. Contact your manager for immediate schedule changes.
                    </p>
                </div>

                {/* One-Time Exceptions */}
                <div className="bg-white rounded-2xl border border-border-gray shadow-sm overflow-hidden mb-12">
                    <div className="px-6 py-4 bg-gray-50 border-b border-border-gray flex items-center justify-between">
                        <h2 className="text-xs font-black text-navy uppercase tracking-widest">One-Time Exceptions</h2>
                    </div>
                    <div className="p-6">
                        <p className="text-xs text-gray-500 mb-6 font-medium">Use exceptions to override your regular availability for vacations or personal days.</p>

                        {exceptions.length > 0 ? (
                            <div className="space-y-3 mb-6">
                                {exceptions.map((ex) => (
                                    <div
                                        key={ex.id}
                                        className={`flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 px-5 py-4 rounded-xl border border-border-gray animate-fade-in ${ex.type === 'available' ? 'bg-success/5 border-success/10' : 'bg-danger/5 border-danger/10'
                                            }`}
                                    >
                                        <div className="flex items-center gap-4 min-w-0">
                                            <div className={`p-2 rounded-lg ${ex.type === 'available' ? 'bg-success/10 text-success' : 'bg-danger/10 text-danger'}`}>
                                                <Clock size={14} />
                                            </div>
                                            <div>
                                                <span className="text-sm text-navy font-black tracking-tight">{ex.date}</span>
                                                <div className="flex items-center gap-2 mt-0.5">
                                                    <Badge variant={ex.type === 'available' ? 'green' : 'red'}>
                                                        {ex.type === 'available' ? 'Available' : 'Unavailable'}
                                                    </Badge>
                                                    {ex.startTime && (
                                                        <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">
                                                            {formatTime(ex.startTime)} - {formatTime(ex.endTime || '')}
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                        <button
                                            onClick={() => removeException(ex.id)}
                                            className="p-2 text-gray-400 hover:text-danger hover:bg-danger/5 rounded-lg transition-all self-end sm:self-auto"
                                        >
                                            <X size={18} />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="py-10 text-center bg-gray-50/50 rounded-2xl border border-dashed border-border-gray mb-6">
                                <p className="text-xs text-gray-400 font-bold uppercase tracking-widest">No exceptions added</p>
                            </div>
                        )}

                        <button
                            onClick={() => setShowAddException(true)}
                            className="flex items-center justify-center gap-2 w-full py-3.5 bg-staff-purple/5 text-staff-purple font-black text-xs uppercase tracking-widest rounded-xl hover:bg-staff-purple/10 border border-staff-purple/10 transition-all active:scale-95"
                        >
                            <Plus size={16} /> Add One-Time Exception
                        </button>
                    </div>
                </div>
            </div>

            {/* Add Exception Modal */}
            <Modal
                open={showAddException}
                onClose={() => setShowAddException(false)}
                title="Schedule Exception"
                subtitle="Override your recurring schedule for a specific date"
                width="max-w-md"
                footer={
                    <div className="flex flex-col-reverse sm:flex-row justify-end gap-3">
                        <button
                            onClick={() => setShowAddException(false)}
                            className="w-full sm:w-auto px-6 py-2.5 text-xs font-black uppercase tracking-widest text-gray-500 hover:text-navy transition-all"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={addException}
                            disabled={!newExceptionDate || (newExceptionType === 'available' && (!newExceptionStartTime || !newExceptionEndTime))}
                            className="w-full sm:w-auto px-8 py-2.5 text-xs font-black uppercase tracking-widest bg-staff-purple text-white rounded-xl hover:bg-staff-purple-light shadow-lg hover:shadow-staff-purple/20 transition-all disabled:opacity-50 active:scale-95"
                        >
                            Add Exception
                        </button>
                    </div>
                }
            >
                <div className="space-y-6 pt-2">
                    <div>
                        <label className="block text-[10px] font-black text-navy uppercase tracking-widest mb-2 opacity-60">Select Date</label>
                        <input
                            type="date"
                            value={newExceptionDate}
                            onChange={(e) => setNewExceptionDate(e.target.value)}
                            className="w-full px-4 py-3 rounded-xl border border-border-gray bg-white text-sm font-bold text-navy focus:ring-2 focus:ring-staff-purple/20 transition-all outline-none"
                        />
                    </div>
                    <div>
                        <label className="block text-[10px] font-black text-navy uppercase tracking-widest mb-2 opacity-60">Availability Type</label>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            <button
                                onClick={() => setNewExceptionType('unavailable')}
                                className={`py-4 rounded-xl border-2 transition-all flex flex-col items-center gap-2 ${newExceptionType === 'unavailable'
                                    ? 'bg-danger/5 border-danger text-danger'
                                    : 'border-border-gray text-gray-400 hover:bg-gray-50'
                                    }`}
                            >
                                <X size={20} />
                                <span className="text-[10px] font-black uppercase tracking-widest">Unavailable</span>
                            </button>
                            <button
                                onClick={() => setNewExceptionType('available')}
                                className={`py-4 rounded-xl border-2 transition-all flex flex-col items-center gap-2 ${newExceptionType === 'available'
                                    ? 'bg-success/5 border-success text-success'
                                    : 'border-border-gray text-gray-400 hover:bg-gray-50'
                                    }`}
                            >
                                <Plus size={20} />
                                <span className="text-[10px] font-black uppercase tracking-widest">Available</span>
                            </button>
                        </div>
                    </div>
                    {newExceptionType === 'available' && (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            <div>
                                <label className="block text-[10px] font-black text-navy uppercase tracking-widest mb-2 opacity-60">Start Time</label>
                                <select
                                    value={newExceptionStartTime}
                                    onChange={(e) => setNewExceptionStartTime(e.target.value)}
                                    className="w-full px-4 py-3 rounded-xl border border-border-gray bg-white text-sm font-bold text-navy outline-none"
                                >
                                    {timeOptions.map((t) => (
                                        <option key={`start-${t}`} value={t}>
                                            {formatTime(t)}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="block text-[10px] font-black text-navy uppercase tracking-widest mb-2 opacity-60">End Time</label>
                                <select
                                    value={newExceptionEndTime}
                                    onChange={(e) => setNewExceptionEndTime(e.target.value)}
                                    className="w-full px-4 py-3 rounded-xl border border-border-gray bg-white text-sm font-bold text-navy outline-none"
                                >
                                    {timeOptions.map((t) => (
                                        <option key={`end-${t}`} value={t}>
                                            {formatTime(t)}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        </div>
                    )}
                </div>
            </Modal>

            <NotificationCentre
                open={isNotificationOpen}
                onClose={() => setIsNotificationOpen(false)}
            />
        </AppLayout>
    );
}
