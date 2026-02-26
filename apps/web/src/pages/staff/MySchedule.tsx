import React, { useState } from 'react';
import {
    ChevronLeft,
    ChevronRight,
    ArrowLeftRight,
    Trash2,
    Eye,
    Clock,
    MapPin,
    ChevronDown,
    X,
    Info,
} from 'lucide-react';
import { AppLayout } from '../../components/NavBar';
import { Avatar } from '../../components/Avatar';
import { Badge } from '../../components/Badge';

/* ========== Mock Data ========== */

interface ShiftCard {
    id: string;
    day: string;
    date: string;
    location: string;
    skill: string;
    time: string;
    hours: number;
    status: 'confirmed' | 'swap-pending';
    swapInfo?: string;
}

const mockShifts: ShiftCard[] = [
    {
        id: '1',
        day: 'Monday, Aug 11',
        date: 'Aug 11',
        location: 'Ocean Ave',
        skill: 'Bartender',
        time: '2:00 PM – 10:00 PM',
        hours: 8,
        status: 'confirmed',
    },
    {
        id: '2',
        day: 'Wednesday, Aug 13',
        date: 'Aug 13',
        location: 'Ocean Ave',
        skill: 'Bartender',
        time: '6:00 PM – 11:00 PM',
        hours: 5,
        status: 'confirmed',
    },
    {
        id: '3',
        day: 'Friday, Aug 15',
        date: 'Aug 15',
        location: 'Beach Blvd',
        skill: 'Bartender',
        time: '4:00 PM – 11:00 PM',
        hours: 7,
        status: 'swap-pending',
        swapInfo: 'Swap request sent to Maria L. · 3 hours ago',
    },
];

const emptyDays = ['Thursday, Aug 14', 'Saturday, Aug 16', 'Sunday, Aug 17'];

const availableShifts = [
    { id: 'a1', location: 'Ocean Ave', date: 'Saturday, Aug 16', time: '4pm – 11pm', skill: 'Bartender' },
    { id: 'a2', location: 'Ocean Ave', date: 'Sunday, Aug 17', time: '10am – 6pm', skill: 'Bartender' },
];

/* ========== Main Component ========== */

export function MySchedule() {
    const [showNotificationBanner, setShowNotificationBanner] = useState(true);
    const [showAvailableShifts, setShowAvailableShifts] = useState(false);

    const totalShifts = mockShifts.length;
    const totalHours = mockShifts.reduce((sum, s) => sum + s.hours, 0);

    return (
        <AppLayout title="My Schedule" role="staff" notificationCount={2}>
            <div className="max-w-3xl mx-auto p-6">
                {/* Notification Banner */}
                {showNotificationBanner && (
                    <div className="mb-4 px-4 py-3 bg-staff-purple-50 border border-staff-purple/20 rounded-xl flex items-center gap-3 animate-fade-in">
                        <Info size={16} className="text-staff-purple flex-shrink-0" />
                        <p className="text-sm text-staff-purple flex-1">
                            Maria L. accepted your swap request for Friday Aug 15. Awaiting manager approval.
                        </p>
                        <button
                            onClick={() => setShowNotificationBanner(false)}
                            className="text-staff-purple/60 hover:text-staff-purple transition-base"
                        >
                            <X size={16} />
                        </button>
                    </div>
                )}

                {/* Week Header */}
                <div className="mb-6">
                    <div className="flex items-center justify-center gap-3 mb-3">
                        <button className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500 transition-base">
                            <ChevronLeft size={20} />
                        </button>
                        <h1 className="text-xl font-bold text-navy">Aug 11 – 17, 2025</h1>
                        <button className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500 transition-base">
                            <ChevronRight size={20} />
                        </button>
                    </div>
                    <div className="flex items-center justify-center gap-3 flex-wrap">
                        <Badge variant="purple">{totalShifts} shifts this week</Badge>
                        <Badge variant="purple">{totalHours} hours</Badge>
                        <Badge variant="gray">Available Mon, Tue, Thu</Badge>
                    </div>
                </div>

                {/* Shift Cards */}
                <div className="space-y-3 mb-6">
                    {mockShifts.map((shift) => (
                        <div key={shift.id}>
                            <p className="text-sm font-bold text-navy mb-1.5">{shift.day}</p>
                            <div
                                className={`bg-white rounded-xl border border-border-gray shadow-sm p-4 border-l-4 ${shift.status === 'confirmed' ? 'border-l-staff-purple' : 'border-l-amber-warn'
                                    } hover:shadow-md transition-base`}
                            >
                                <div className="flex items-start justify-between mb-2">
                                    <div>
                                        <div className="flex items-center gap-2 text-sm text-gray-600 mb-1">
                                            <MapPin size={13} />
                                            <span>{shift.location}</span>
                                            <span>·</span>
                                            <span>{shift.skill}</span>
                                        </div>
                                        <div className="flex items-center gap-2 text-sm text-navy font-medium">
                                            <Clock size={13} />
                                            <span>{shift.time}</span>
                                            <span className="text-gray-400">·</span>
                                            <span className="text-gray-500">{shift.hours} hours</span>
                                        </div>
                                    </div>
                                    <Badge variant={shift.status === 'confirmed' ? 'green' : 'amber'}>
                                        {shift.status === 'confirmed' ? 'Confirmed' : 'Swap Pending'}
                                    </Badge>
                                </div>

                                {shift.swapInfo && (
                                    <p className="text-xs text-gray-500 mt-2 flex items-center gap-1.5">
                                        <ArrowLeftRight size={12} /> {shift.swapInfo}
                                    </p>
                                )}

                                <div className="flex items-center gap-2 mt-3 pt-3 border-t border-border-gray">
                                    {shift.status === 'confirmed' ? (
                                        <>
                                            <button className="px-3 py-1.5 text-xs font-semibold border border-staff-purple/30 text-staff-purple rounded-lg hover:bg-staff-purple-50 transition-base">
                                                Request Swap
                                            </button>
                                            <button className="px-3 py-1.5 text-xs font-semibold border border-danger/20 text-danger rounded-lg hover:bg-danger-50 transition-base">
                                                Drop Shift
                                            </button>
                                        </>
                                    ) : (
                                        <button className="px-3 py-1.5 text-xs font-semibold bg-staff-purple text-white rounded-lg hover:bg-staff-purple-light transition-base">
                                            View Swap Status
                                        </button>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}

                    {/* Empty days */}
                    {emptyDays.map((day) => (
                        <div key={day}>
                            <p className="text-sm font-bold text-navy mb-1.5">{day}</p>
                            <div className="bg-gray-50 rounded-xl border border-dashed border-border-gray p-4 text-center">
                                <p className="text-sm text-gray-400">No shift</p>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Available Shifts */}
                <div className="border border-border-gray rounded-xl overflow-hidden">
                    <button
                        onClick={() => setShowAvailableShifts(!showAvailableShifts)}
                        className="w-full px-4 py-3 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-base"
                    >
                        <span className="text-sm font-bold text-navy">Available Shifts</span>
                        <ChevronDown
                            size={16}
                            className={`text-gray-500 transition-transform ${showAvailableShifts ? 'rotate-180' : ''}`}
                        />
                    </button>
                    {showAvailableShifts && (
                        <div className="p-4 space-y-3 animate-fade-in">
                            {availableShifts.map((shift) => (
                                <div
                                    key={shift.id}
                                    className="flex items-center justify-between p-3 bg-success-50 rounded-lg border border-success/20"
                                >
                                    <div>
                                        <div className="flex items-center gap-2 text-sm text-navy font-medium">
                                            <MapPin size={13} />
                                            <span>{shift.location}</span>
                                            <span>·</span>
                                            <span>{shift.skill}</span>
                                        </div>
                                        <p className="text-xs text-gray-600 mt-0.5">
                                            {shift.date} · {shift.time}
                                        </p>
                                    </div>
                                    <button className="px-4 py-1.5 text-xs font-semibold bg-success text-white rounded-lg hover:bg-success/90 transition-base">
                                        Pick Up Shift
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </AppLayout>
    );
}
