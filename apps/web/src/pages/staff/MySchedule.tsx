import React, { useState, useMemo } from 'react';
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
    Loader2,
    AlertCircle,
} from 'lucide-react';
import { format, parseISO, startOfWeek, addDays, isSameDay } from 'date-fns';
import { useNotifications } from '../../lib/api/hooks';

import { AppLayout } from '../../components/NavBar';
import { Avatar } from '../../components/Avatar';
import { Badge } from '../../components/Badge';

import {
    useMyAssignments,
    useAvailableDrops,
    useSwapRequests,
    usePickupDrop,
    useCreateDropRequest
} from '../../lib/api/hooks';
import { MyAssignmentResponse, AvailableDropRequest } from '../../lib/api/types';
import { SwapRequestFlow } from './SwapRequestFlow';
import { NotificationCentre } from './NotificationCentre';

/* ========== Sub-Components ========== */

interface ShiftCardProps {
    assignment: MyAssignmentResponse;
    swapInfo?: string;
    onDrop: (id: string) => void;
    onSwap: (assignment: MyAssignmentResponse) => void;
    dropping: boolean;
}

function ShiftCard({ assignment, swapInfo, onDrop, onSwap, dropping }: ShiftCardProps) {
    const { shift, status, id } = assignment;

    return (
        <div
            className={`bg-white rounded-xl border border-border-gray shadow-sm p-4 border-l-4 ${status === 'assigned' ? 'border-l-staff-purple' : 'border-l-amber-warn'
                } hover:shadow-md transition-base`}
        >
            <div className="flex items-start justify-between mb-2">
                <div>
                    <div className="flex items-center gap-2 text-sm text-gray-600 mb-1">
                        <MapPin size={13} />
                        <span>{shift.location_name}</span>
                        <span>·</span>
                        <span>{shift.required_skill}</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-navy font-medium">
                        <Clock size={13} />
                        <span>{shift.start_local.slice(11, 16)} – {shift.end_local.slice(11, 16)}</span>
                    </div>
                </div>
                <Badge variant={status === 'assigned' ? 'green' : 'amber'}>
                    {status === 'assigned' ? 'Confirmed' : 'Swap Pending'}
                </Badge>
            </div>

            {swapInfo && (
                <p className="text-xs text-gray-500 mt-2 flex items-center gap-1.5">
                    <ArrowLeftRight size={12} /> {swapInfo}
                </p>
            )}

            <div className="flex items-center gap-2 mt-3 pt-3 border-t border-border-gray">
                {status === 'assigned' ? (
                    <>
                        <button
                            onClick={() => onSwap(assignment)}
                            className="px-3 py-1.5 text-xs font-semibold border border-staff-purple/30 text-staff-purple rounded-lg hover:bg-staff-purple-50 transition-base"
                        >
                            Request Swap
                        </button>
                        <button
                            onClick={() => onDrop(id)}
                            disabled={dropping}
                            className="px-3 py-1.5 text-xs font-semibold border border-danger/20 text-danger rounded-lg hover:bg-danger-50 transition-base disabled:opacity-50"
                        >
                            {dropping ? 'Dropping...' : 'Drop Shift'}
                        </button>
                    </>
                ) : (
                    <button className="px-3 py-1.5 text-xs font-semibold bg-staff-purple text-white rounded-lg hover:bg-staff-purple-light transition-base">
                        View Swap Status
                    </button>
                )}
            </div>
        </div>
    );
}

/* ========== Main Component ========== */

export function MySchedule() {
    const [weekOffset, setWeekOffset] = useState(0);
    const [showNotificationBanner, setShowNotificationBanner] = useState(true);
    const [showAvailableShifts, setShowAvailableShifts] = useState(false);

    // Swap Flow State
    const [isSwapModalOpen, setIsSwapModalOpen] = useState(false);
    const [selectedAssignmentForSwap, setSelectedAssignmentForSwap] = useState<MyAssignmentResponse | null>(null);

    // Notifications State
    const [isNotificationOpen, setIsNotificationOpen] = useState(false);

    const { data: assignmentsData, isLoading: isLoadingAssignments } = useMyAssignments();
    const { data: availableData, isLoading: isLoadingAvailable } = useAvailableDrops();
    const { data: swapsData } = useSwapRequests();
    const { data: notificationsData } = useNotifications();
    const unreadCount = notificationsData?.unread_count || 0;

    const pickupMutation = usePickupDrop();
    const dropMutation = useCreateDropRequest();

    // Week Calculation
    const weekStart = useMemo(() => {
        const d = new Date();
        d.setDate(d.getDate() + (weekOffset * 7));
        return startOfWeek(d, { weekStartsOn: 1 }); // Monday
    }, [weekOffset]);

    const weekDays = useMemo(() => {
        return Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));
    }, [weekStart]);

    // Filtering
    const weeklyAssignments = useMemo(() => {
        if (!assignmentsData?.assignments) return [];
        return assignmentsData.assignments.filter(a => {
            const shiftDate = parseISO(a.shift.shift_date);
            return shiftDate >= weekStart && shiftDate < addDays(weekStart, 7);
        });
    }, [assignmentsData, weekStart]);

    const totalHours = useMemo(() => {
        return weeklyAssignments.reduce((sum, a) => {
            const start = parseISO(a.shift.start_utc);
            const end = parseISO(a.shift.end_utc);
            return sum + (end.getTime() - start.getTime()) / (1000 * 60 * 60);
        }, 0);
    }, [weeklyAssignments]);

    const handlePickup = (requestId: string) => {
        pickupMutation.mutate({ id: requestId, data: { note: 'Staff picking up drop' } });
    };

    const handleDrop = (assignmentId: string) => {
        if (window.confirm('Are you sure you want to drop this shift? It will be available for others to pick up.')) {
            dropMutation.mutate({ assignment_id: assignmentId });
        }
    };

    const handleSwapRequest = (assignment: MyAssignmentResponse) => {
        setSelectedAssignmentForSwap(assignment);
        setIsSwapModalOpen(true);
    };

    const isLoading = isLoadingAssignments || isLoadingAvailable;

    return (
        <AppLayout
            title="My Schedule"
            role="staff"
            notificationCount={unreadCount}
            onBellClick={() => setIsNotificationOpen(true)}
        >
            <div className="max-w-3xl mx-auto p-6">
                {/* Notification Banner */}
                {showNotificationBanner && swapsData?.requests.some(r => r.status === 'APPROVED') && (
                    <div className="mb-4 px-4 py-3 bg-staff-purple-50 border border-staff-purple/20 rounded-xl flex items-center gap-3 animate-fade-in">
                        <Info size={16} className="text-staff-purple flex-shrink-0" />
                        <p className="text-sm text-staff-purple flex-1">
                            Your recent swap request was approved by the manager.
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
                <div className="mb-8">
                    <div className="flex items-center justify-center gap-6 mb-4">
                        <button
                            onClick={() => setWeekOffset(prev => prev - 1)}
                            className="p-2 rounded-xl hover:bg-gray-100 text-gray-500 transition-all active:scale-90"
                        >
                            <ChevronLeft size={24} />
                        </button>
                        <h1 className="text-2xl font-black text-navy min-w-[240px] text-center">
                            {format(weekStart, 'MMM d')} – {format(addDays(weekStart, 6), 'd, yyyy')}
                        </h1>
                        <button
                            onClick={() => setWeekOffset(prev => prev + 1)}
                            className="p-2 rounded-xl hover:bg-gray-100 text-gray-500 transition-all active:scale-90"
                        >
                            <ChevronRight size={24} />
                        </button>
                    </div>
                    <div className="flex items-center justify-center gap-3 flex-wrap">
                        <Badge variant="purple">{weeklyAssignments.length} shifts this week</Badge>
                        <Badge variant="purple">{totalHours.toFixed(1)} hours</Badge>
                    </div>
                </div>

                {/* Day Groups */}
                <div className="space-y-6 mb-8">
                    {isLoading ? (
                        <div className="py-20 flex flex-col items-center justify-center text-gray-300">
                            <Loader2 size={40} className="animate-spin mb-4" />
                            <span className="text-sm font-medium">Fetching your schedule…</span>
                        </div>
                    ) : (
                        weekDays.map((day) => {
                            const dayAssignments = weeklyAssignments.filter(a => isSameDay(parseISO(a.shift.shift_date), day));
                            return (
                                <div key={day.toISOString()} className="group">
                                    <div className="flex items-center gap-3 mb-3">
                                        <p className="text-sm font-black text-navy uppercase tracking-widest">{format(day, 'eeee, MMM d')}</p>
                                        <div className="h-px flex-1 bg-gray-100 group-hover:bg-gray-200 transition-colors" />
                                    </div>

                                    <div className="space-y-3">
                                        {dayAssignments.length > 0 ? (
                                            dayAssignments.map((a) => (
                                                <ShiftCard
                                                    key={a.id}
                                                    assignment={a}
                                                    onDrop={handleDrop}
                                                    onSwap={handleSwapRequest}
                                                    dropping={dropMutation.isPending}
                                                />
                                            ))
                                        ) : (
                                            <div className="bg-gray-50/50 rounded-xl border border-dashed border-border-gray p-4 text-center">
                                                <p className="text-sm text-gray-400 font-medium">No shifts scheduled</p>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            );
                        })
                    )}
                </div>

                {/* Available Shifts */}
                <div className="border border-border-gray rounded-2xl overflow-hidden shadow-sm bg-white">
                    <button
                        onClick={() => setShowAvailableShifts(!showAvailableShifts)}
                        className="w-full px-5 py-4 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-all"
                    >
                        <div className="flex items-center gap-2">
                            <AlertCircle size={18} className="text-success" />
                            <span className="text-sm font-bold text-navy">Open Shifts Available for Pickup</span>
                        </div>
                        <div className="flex items-center gap-3">
                            <Badge variant="green">{availableData?.available.length || 0}</Badge>
                            <ChevronDown
                                size={18}
                                className={`text-gray-400 transition-transform duration-300 ${showAvailableShifts ? 'rotate-180' : ''}`}
                            />
                        </div>
                    </button>
                    {showAvailableShifts && (
                        <div className="p-4 space-y-3 animate-fade-in divide-y divide-gray-50">
                            {availableData?.available.map((drop) => (
                                <div
                                    key={drop.drop_request_id}
                                    className="flex items-center justify-between pt-3 first:pt-0"
                                >
                                    <div className="space-y-1">
                                        <div className="flex items-center gap-2 text-sm text-navy font-bold">
                                            <MapPin size={13} className="text-gray-400" />
                                            <span>{drop.shift.location.name}</span>
                                            <span className="text-gray-300">·</span>
                                            <span className="text-staff-purple">{drop.shift.required_skill}</span>
                                        </div>
                                        <p className="text-xs text-gray-500 font-medium">
                                            {format(parseISO(drop.shift.date), 'MMM d')} · {drop.shift.start_local.slice(11, 16)} – {drop.shift.end_local.slice(11, 16)}
                                        </p>
                                    </div>
                                    <button
                                        onClick={() => handlePickup(drop.drop_request_id)}
                                        disabled={pickupMutation.isPending}
                                        className="px-5 py-2 text-xs font-black bg-success text-white rounded-xl hover:bg-success-dark transition-all shadow-md hover:shadow-lg active:scale-95 disabled:opacity-50"
                                    >
                                        {pickupMutation.isPending ? 'Picking up...' : 'Claim'}
                                    </button>
                                </div>
                            ))}
                            {availableData?.available.length === 0 && (
                                <div className="py-8 text-center">
                                    <p className="text-sm text-gray-400">No open shifts matching your skills right now.</p>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>

            <SwapRequestFlow
                open={isSwapModalOpen}
                onClose={() => setIsSwapModalOpen(false)}
                myAssignment={selectedAssignmentForSwap}
            />

            <NotificationCentre
                open={isNotificationOpen}
                onClose={() => setIsNotificationOpen(false)}
            />
        </AppLayout>
    );
}
