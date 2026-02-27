import React, { useEffect, useState, useMemo } from 'react';
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
import { useSearchParams } from 'react-router-dom';
import { useNotifications } from '../../lib/api/hooks';
import { useAuth } from '../../auth/AuthContext';

import { AppLayout } from '../../components/NavBar';
import { Avatar } from '../../components/Avatar';
import { Badge } from '../../components/Badge';

import {
    useMyAssignments,
    useAvailableDrops,
    useSwapRequests,
    useSwapAction,
    usePickupDrop,
    useCreateDropRequest
} from '../../lib/api/hooks';
import { MyAssignmentResponse } from '../../lib/api/types';
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
            <div className="flex items-start justify-between mb-2 gap-2 flex-wrap">
                <div>
                    <div className="flex items-center gap-2 text-sm text-gray-600 mb-1 flex-wrap">
                        <MapPin size={13} />
                        <span>{shift.location_name}</span>
                        <span>·</span>
                        <span>{shift.required_skill}</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-navy font-medium flex-wrap">
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

            <div className="flex items-center gap-2 mt-3 pt-3 border-t border-border-gray flex-wrap">
                {status === 'assigned' ? (
                    <>
                        <button
                            onClick={() => onSwap(assignment)}
                            className="px-3 py-1.5 text-xs font-semibold border border-staff-purple/30 text-staff-purple rounded-lg hover:bg-staff-purple-50 transition-base flex-1 sm:flex-none"
                        >
                            Request Swap
                        </button>
                        <button
                            onClick={() => onDrop(id)}
                            disabled={dropping}
                            className="px-3 py-1.5 text-xs font-semibold border border-danger/20 text-danger rounded-lg hover:bg-danger-50 transition-base disabled:opacity-50 flex-1 sm:flex-none"
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
    const { user } = useAuth();
    const [searchParams] = useSearchParams();
    const [weekOffset, setWeekOffset] = useState(0);
    const [showNotificationBanner, setShowNotificationBanner] = useState(true);
    const [showAvailableShifts, setShowAvailableShifts] = useState(false);

    // Swap Flow State
    const [isSwapModalOpen, setIsSwapModalOpen] = useState(false);
    const [selectedAssignmentForSwap, setSelectedAssignmentForSwap] = useState<MyAssignmentResponse | null>(null);

    // Notifications State
    const [isNotificationOpen, setIsNotificationOpen] = useState(false);

    const { data: assignmentsData, isLoading: isLoadingAssignments } = useMyAssignments();
    const { data: availableData, isLoading: isLoadingAvailable, refetch: refetchAvailableDrops } = useAvailableDrops();
    const { data: swapsData } = useSwapRequests();
    const { data: notificationsData } = useNotifications();
    const unreadCount = notificationsData?.unread_count || 0;
    const highlightedDropRequestId = searchParams.get('requestId');
    const openDropsFromNotification = searchParams.get('open_drops') === '1' || !!highlightedDropRequestId;

    const pickupMutation = usePickupDrop();
    const dropMutation = useCreateDropRequest();
    const cancelRequestMutation = useSwapAction('cancel');

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

    const handleCancelPendingRequest = (requestId: string, isDrop: boolean) => {
        if (!window.confirm('Cancel this pending request?')) return;
        cancelRequestMutation.mutate({
            id: requestId,
            data: { note: 'Cancelled by requester' },
            isDrop,
        });
    };

    const isLoading = isLoadingAssignments || isLoadingAvailable;
    const myPendingRequests = (swapsData?.requests || []).filter((request) =>
        request.initiated_by === user?.id && ['OPEN', 'PENDING_ACCEPTEE', 'PENDING_MANAGER'].includes(request.status)
    );
    const highlightedDropStillOpen = highlightedDropRequestId
        ? (availableData?.available || []).some((drop) => drop.drop_request_id === highlightedDropRequestId)
        : false;

    useEffect(() => {
        if (!openDropsFromNotification) return;
        setShowAvailableShifts(true);
        refetchAvailableDrops();
    }, [openDropsFromNotification, refetchAvailableDrops]);

    useEffect(() => {
        if (!showAvailableShifts || !highlightedDropRequestId) return;
        const el = document.getElementById(`drop-${highlightedDropRequestId}`);
        if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }, [showAvailableShifts, highlightedDropRequestId, availableData?.available.length]);

    return (
        <AppLayout
            title="My Schedule"
            role="staff"
            notificationCount={unreadCount}
            onBellClick={() => setIsNotificationOpen(true)}
        >
            <div className="w-full h-full min-h-0 px-2 py-2 md:px-3 md:py-3 lg:px-4 lg:py-4 flex flex-col gap-3">
                {/* Notification Banner */}
                {showNotificationBanner && swapsData?.requests.some(r => r.status === 'APPROVED') && (
                    <div className="px-4 py-3 bg-staff-purple-50 border border-staff-purple/20 rounded-xl flex items-center gap-3 animate-fade-in shrink-0">
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
                <div className="shrink-0 bg-white border border-border-gray rounded-xl px-3 sm:px-4 py-2.5 sm:py-3 shadow-sm">
                    <div className="flex items-center justify-center gap-2 sm:gap-6">
                        <button
                            onClick={() => setWeekOffset(prev => prev - 1)}
                            className="p-1.5 rounded-xl hover:bg-gray-100 text-gray-500 transition-all active:scale-90"
                        >
                            <ChevronLeft size={20} />
                        </button>
                        <h1 className="text-base sm:text-xl font-black text-navy text-center whitespace-nowrap">
                            {format(weekStart, 'MMM d')} – {format(addDays(weekStart, 6), 'd, yyyy')}
                        </h1>
                        <button
                            onClick={() => setWeekOffset(prev => prev + 1)}
                            className="p-1.5 rounded-xl hover:bg-gray-100 text-gray-500 transition-all active:scale-90"
                        >
                            <ChevronRight size={20} />
                        </button>
                    </div>
                    <div className="mt-2 flex items-center justify-center gap-2 flex-wrap">
                        <Badge variant="purple">{weeklyAssignments.length} shifts this week</Badge>
                        <Badge variant="purple">{totalHours.toFixed(1)} hours</Badge>
                    </div>
                </div>

                {/* Day Groups */}
                <div className="grid grid-cols-1 lg:grid-cols-2 2xl:grid-cols-3 gap-4 mb-4">
                    {isLoading ? (
                        <div className="py-20 flex flex-col items-center justify-center text-gray-300 lg:col-span-2 2xl:col-span-3">
                            <Loader2 size={40} className="animate-spin mb-4" />
                            <span className="text-sm font-medium">Fetching your schedule…</span>
                        </div>
                    ) : (
                        weekDays.map((day) => {
                            const dayAssignments = weeklyAssignments.filter(a => isSameDay(parseISO(a.shift.shift_date), day));
                            return (
                                <div key={day.toISOString()} className="group bg-white border border-border-gray rounded-xl p-3 shadow-sm">
                                    <div className="flex items-center gap-2.5 mb-2">
                                        <p className="text-sm font-black text-navy uppercase tracking-widest">{format(day, 'eeee, MMM d')}</p>
                                        <div className="h-px flex-1 bg-gray-100 group-hover:bg-gray-200 transition-colors" />
                                    </div>

                                    <div className="space-y-2.5">
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
                                            <div className="bg-gray-50/50 rounded-xl border border-dashed border-border-gray p-3 text-center">
                                                <p className="text-sm text-gray-400 font-medium">No shifts scheduled</p>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            );
                        })
                    )}
                </div>

                <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
                    {/* My Pending Requests */}
                    <div className="border border-border-gray rounded-2xl overflow-hidden shadow-sm bg-white">
                        <div className="px-4 sm:px-5 py-4 bg-gray-50 border-b border-border-gray flex items-center justify-between gap-3 flex-wrap">
                            <span className="text-sm font-bold text-navy">My Pending Swap/Drop Requests</span>
                            <Badge variant="amber">{myPendingRequests.length}</Badge>
                        </div>
                        <div className="p-4 space-y-3 xl:max-h-[42vh] xl:overflow-y-auto">
                            {myPendingRequests.map((request) => (
                                <div key={request.id} className="border border-border-gray rounded-xl p-3 flex items-center justify-between gap-3 flex-wrap">
                                    <div>
                                        <p className="text-sm font-semibold text-navy capitalize">
                                            {request.type} request - {request.status.replace("_", " ")}
                                        </p>
                                        <p className="text-xs text-gray-500">
                                            {request.shift_date ? format(parseISO(request.shift_date), 'MMM d') : 'Unknown date'} - {request.shift_label || 'Shift'} - {request.shift_time || 'Time unknown'}
                                        </p>
                                    </div>
                                    <button
                                        onClick={() => handleCancelPendingRequest(request.id, request.type === 'drop')}
                                        disabled={cancelRequestMutation.isPending}
                                        className="px-3 py-1.5 text-xs font-semibold border border-danger/30 text-danger rounded-lg hover:bg-danger-50 transition-base disabled:opacity-50"
                                    >
                                        {cancelRequestMutation.isPending ? 'Cancelling...' : 'Cancel Request'}
                                    </button>
                                </div>
                            ))}
                            {myPendingRequests.length === 0 && (
                                <div className="py-6 text-center text-sm text-gray-400">
                                    You have no pending swap or drop requests.
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Available Shifts */}
                    <div className="border border-border-gray rounded-2xl overflow-hidden shadow-sm bg-white">
                    <button
                        onClick={() => setShowAvailableShifts(!showAvailableShifts)}
                        className="w-full px-4 sm:px-5 py-4 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-all gap-3"
                    >
                        <div className="flex items-center gap-2 min-w-0">
                            <AlertCircle size={18} className="text-success" />
                            <span className="text-sm font-bold text-navy truncate">Open Shifts Available for Pickup</span>
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
                        <div className="p-4 space-y-3 animate-fade-in divide-y divide-gray-50 xl:max-h-[42vh] xl:overflow-y-auto">
                            {highlightedDropRequestId && !isLoadingAvailable && !highlightedDropStillOpen && (
                                <div className="rounded-xl border border-amber-warn/40 bg-amber-warn-50 p-3 text-xs text-amber-warn">
                                    This request is no longer open for pickup.
                                </div>
                            )}
                            {availableData?.available.map((drop) => (
                                <div
                                    id={`drop-${drop.drop_request_id}`}
                                    key={drop.drop_request_id}
                                    className={`flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pt-3 first:pt-0 ${highlightedDropRequestId === drop.drop_request_id ? 'rounded-lg bg-staff-purple-50/60 px-2 py-2 ring-1 ring-staff-purple/30' : ''}`}
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
                                        className="w-full sm:w-auto px-5 py-2 text-xs font-black bg-success text-white rounded-xl hover:bg-success-dark transition-all shadow-md hover:shadow-lg active:scale-95 disabled:opacity-50"
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
