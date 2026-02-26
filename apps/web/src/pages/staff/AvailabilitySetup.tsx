import React, { useState } from 'react';
import { Save, Plus, X, Info, Clock } from 'lucide-react';
import { AppLayout } from '../../components/NavBar';
import { Badge } from '../../components/Badge';
import { Modal } from '../../components/Modal';

/* ========== Types & Mock Data ========== */

interface DayAvailability {
    day: string;
    available: boolean;
    startTime: string;
    endTime: string;
}

interface Exception {
    id: string;
    date: string;
    type: 'unavailable' | 'available';
    startTime?: string;
    endTime?: string;
}

const initialAvailability: DayAvailability[] = [
    { day: 'Monday', available: true, startTime: '09:00', endTime: '17:00' },
    { day: 'Tuesday', available: true, startTime: '12:00', endTime: '22:00' },
    { day: 'Wednesday', available: false, startTime: '09:00', endTime: '17:00' },
    { day: 'Thursday', available: true, startTime: '09:00', endTime: '17:00' },
    { day: 'Friday', available: true, startTime: '14:00', endTime: '23:00' },
    { day: 'Saturday', available: true, startTime: '10:00', endTime: '20:00' },
    { day: 'Sunday', available: false, startTime: '09:00', endTime: '17:00' },
];

const initialExceptions: Exception[] = [
    { id: '1', date: 'Aug 20, 2025', type: 'unavailable' },
];

const timeOptions: string[] = [];
for (let h = 0; h < 24; h++) {
    for (const m of ['00', '30']) {
        const hour = h.toString().padStart(2, '0');
        timeOptions.push(`${hour}:${m}`);
    }
}

function formatTime(time: string): string {
    const [h, m] = time.split(':').map(Number);
    const ampm = h >= 12 ? 'PM' : 'AM';
    const displayH = h === 0 ? 12 : h > 12 ? h - 12 : h;
    return `${displayH}:${m.toString().padStart(2, '0')} ${ampm}`;
}

/* ========== Main Component ========== */

export function AvailabilitySetup() {
    const [availability, setAvailability] = useState(initialAvailability);
    const [exceptions, setExceptions] = useState(initialExceptions);
    const [hasChanges, setHasChanges] = useState(false);
    const [showAddException, setShowAddException] = useState(false);
    const [newExceptionDate, setNewExceptionDate] = useState('');
    const [newExceptionType, setNewExceptionType] = useState<'unavailable' | 'available'>('unavailable');

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
        setExceptions((prev) => [
            ...prev,
            { id: Date.now().toString(), date: newExceptionDate, type: newExceptionType },
        ]);
        setShowAddException(false);
        setNewExceptionDate('');
        setHasChanges(true);
    };

    return (
        <AppLayout title="Availability" role="staff" notificationCount={2}>
            <div className="max-w-3xl mx-auto p-6">
                {/* Header */}
                <div className="flex items-start justify-between mb-6">
                    <div>
                        <h1 className="text-2xl font-bold text-navy">My Availability</h1>
                        <p className="text-sm text-gray-500 mt-1">
                            Your availability is shown in your home timezone: America/Los_Angeles (Pacific Time)
                        </p>
                    </div>
                    <button
                        disabled={!hasChanges}
                        className={`px-5 py-2.5 text-sm font-semibold rounded-lg transition-base flex items-center gap-2 ${hasChanges
                                ? 'bg-teal text-white hover:bg-teal-dark shadow-md'
                                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                            }`}
                    >
                        <Save size={16} /> Save Changes
                    </button>
                </div>

                {/* Weekly Recurring Availability */}
                <div className="bg-white rounded-xl border border-border-gray shadow-sm mb-6 overflow-hidden">
                    <div className="px-5 py-4 bg-gray-50 border-b border-border-gray">
                        <h2 className="text-sm font-bold text-navy">Weekly Recurring Availability</h2>
                    </div>
                    <div className="divide-y divide-border-gray">
                        {availability.map((day, i) => (
                            <div
                                key={day.day}
                                className={`flex items-center gap-4 px-5 py-4 ${!day.available ? 'bg-gray-50' : ''}`}
                            >
                                <span className="w-24 text-sm font-semibold text-navy">{day.day}</span>

                                {/* Toggle */}
                                <button
                                    onClick={() => toggleDay(i)}
                                    className={`relative w-11 h-6 rounded-full transition-colors ${day.available ? 'bg-staff-purple' : 'bg-gray-300'
                                        }`}
                                >
                                    <span
                                        className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${day.available ? 'translate-x-5' : 'translate-x-0'
                                            }`}
                                    />
                                </button>

                                {day.available ? (
                                    <div className="flex items-center gap-2 flex-1">
                                        <select
                                            value={day.startTime}
                                            onChange={(e) => updateTime(i, 'startTime', e.target.value)}
                                            className="px-3 py-2 rounded-lg border border-border-gray bg-white text-sm text-navy focus:outline-none focus:ring-2 focus:ring-staff-purple/40 transition-base"
                                        >
                                            {timeOptions.map((t) => (
                                                <option key={t} value={t}>
                                                    {formatTime(t)}
                                                </option>
                                            ))}
                                        </select>
                                        <span className="text-gray-400">–</span>
                                        <select
                                            value={day.endTime}
                                            onChange={(e) => updateTime(i, 'endTime', e.target.value)}
                                            className="px-3 py-2 rounded-lg border border-border-gray bg-white text-sm text-navy focus:outline-none focus:ring-2 focus:ring-staff-purple/40 transition-base"
                                        >
                                            {timeOptions.map((t) => (
                                                <option key={t} value={t}>
                                                    {formatTime(t)}
                                                </option>
                                            ))}
                                        </select>
                                    </div>
                                ) : (
                                    <span className="text-sm text-gray-400 italic">Unavailable</span>
                                )}
                            </div>
                        ))}
                    </div>
                </div>

                {/* Info callout */}
                <div className="flex items-start gap-2 mb-6 px-4 py-3 bg-blue-50 rounded-lg border border-blue-200">
                    <Info size={14} className="text-blue-600 mt-0.5 flex-shrink-0" />
                    <p className="text-xs text-blue-700">
                        ℹ Changes take effect for future schedules. Shifts already assigned are not affected.
                    </p>
                </div>

                {/* One-Time Exceptions */}
                <div className="bg-white rounded-xl border border-border-gray shadow-sm overflow-hidden">
                    <div className="px-5 py-4 bg-gray-50 border-b border-border-gray flex items-center justify-between">
                        <h2 className="text-sm font-bold text-navy">One-Time Exceptions</h2>
                    </div>
                    <div className="p-5">
                        <p className="text-xs text-gray-500 mb-4">Override your regular availability for specific dates</p>

                        {exceptions.length > 0 && (
                            <div className="space-y-2 mb-4">
                                {exceptions.map((ex) => (
                                    <div
                                        key={ex.id}
                                        className="flex items-center justify-between px-4 py-3 bg-gray-50 rounded-lg border border-border-gray"
                                    >
                                        <div className="flex items-center gap-2">
                                            <Clock size={14} className="text-gray-400" />
                                            <span className="text-sm text-navy font-medium">{ex.date}</span>
                                            <span className="text-sm text-gray-500">—</span>
                                            <span className="text-sm text-gray-600">
                                                {ex.type === 'unavailable' ? 'Unavailable all day' : 'Available'}
                                            </span>
                                        </div>
                                        <button
                                            onClick={() => removeException(ex.id)}
                                            className="p-1 text-gray-400 hover:text-danger transition-base"
                                        >
                                            <X size={16} />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}

                        <button
                            onClick={() => setShowAddException(true)}
                            className="flex items-center gap-2 text-sm text-staff-purple font-semibold hover:text-staff-purple-light transition-base"
                        >
                            <Plus size={16} /> Add Exception
                        </button>
                    </div>
                </div>
            </div>

            {/* Add Exception Modal */}
            <Modal
                open={showAddException}
                onClose={() => setShowAddException(false)}
                title="Add Exception"
                subtitle="Override your regular availability for a specific date"
                width="max-w-md"
                footer={
                    <div className="flex justify-end gap-3">
                        <button
                            onClick={() => setShowAddException(false)}
                            className="px-4 py-2 text-sm text-gray-600 hover:text-navy transition-base"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={addException}
                            disabled={!newExceptionDate}
                            className="px-5 py-2 text-sm font-semibold bg-staff-purple text-white rounded-lg hover:bg-staff-purple-light disabled:opacity-50 transition-base"
                        >
                            Save Exception
                        </button>
                    </div>
                }
            >
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-navy mb-1.5">Date</label>
                        <input
                            type="date"
                            value={newExceptionDate}
                            onChange={(e) => setNewExceptionDate(e.target.value)}
                            className="w-full px-4 py-2.5 rounded-lg border border-border-gray bg-gray-50 text-sm text-navy focus:outline-none focus:ring-2 focus:ring-staff-purple/40 transition-base"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-navy mb-1.5">Type</label>
                        <div className="flex gap-3">
                            <button
                                onClick={() => setNewExceptionType('unavailable')}
                                className={`flex-1 py-2.5 text-sm font-medium rounded-lg border transition-base ${newExceptionType === 'unavailable'
                                        ? 'bg-staff-purple-50 border-staff-purple text-staff-purple'
                                        : 'border-border-gray text-gray-600 hover:bg-gray-50'
                                    }`}
                            >
                                Unavailable
                            </button>
                            <button
                                onClick={() => setNewExceptionType('available')}
                                className={`flex-1 py-2.5 text-sm font-medium rounded-lg border transition-base ${newExceptionType === 'available'
                                        ? 'bg-staff-purple-50 border-staff-purple text-staff-purple'
                                        : 'border-border-gray text-gray-600 hover:bg-gray-50'
                                    }`}
                            >
                                Available
                            </button>
                        </div>
                    </div>
                </div>
            </Modal>
        </AppLayout>
    );
}
