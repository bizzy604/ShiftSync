import React, { useState, useMemo } from 'react';
import { AlertTriangle, Clock, Check, Bell, User, X, Loader2, Info } from 'lucide-react';
import { format, parseISO, differenceInMinutes, addMinutes, isBefore } from 'date-fns';

import { SidePanel } from '../../components/SidePanel';
import { Avatar } from '../../components/Avatar';
import { Badge } from '../../components/Badge';

import { useSwapRequest, useUsers, useAssignmentPreview, useSwapAction, useShiftSuggestions, useNotifyQualifiedStaff } from '../../lib/api/hooks';
import { SwapRequestResponse, UserResponse, ConstraintSuggestion } from '../../lib/api/types';

/* ========== Sub-Components ========== */

interface QualifiedStaffRowProps {
    user: UserResponse;
    shiftId: string;
}

function QualifiedStaffRow({ user, shiftId }: QualifiedStaffRowProps) {
    const { data: preview, isLoading } = useAssignmentPreview(shiftId, user.id);

    if (isLoading) return (
        <div className="p-3 border border-border-gray rounded-xl flex items-center justify-center">
            <Loader2 size={16} className="animate-spin text-gray-300" />
        </div>
    );

    const isQualified = preview?.valid && !preview?.requires_override;
    const warning = preview?.warnings?.[0]?.description || preview?.violations?.[0]?.description;

    return (
        <div className={`p-3.5 rounded-xl border transition-base bg-white border-border-gray hover:border-gray-400 ${!isQualified ? 'opacity-60 grayscale-[0.5]' : ''}`}>
            <div className="flex items-center gap-3">
                <Avatar name={user.name} size="md" online={user.is_active} />
                <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-navy">{user.name}</p>
                    <p className="text-xs text-gray-500">
                        {preview?.projected_weekly_hours}h · {isQualified ? 'Eligible' : 'Constraint Risk'}
                    </p>
                </div>
                <div className="flex-shrink-0">
                    {isQualified ? (
                        <Badge variant="green">Qualified</Badge>
                    ) : (
                        <Badge variant="amber" title={warning}>Check Rules</Badge>
                    )}
                </div>
            </div>
            {warning && (
                <div className="mt-2 flex items-start gap-1 text-[10px] text-amber-warn font-medium">
                    <Info size={10} className="mt-0.5" />
                    <span>{warning}</span>
                </div>
            )}
        </div>
    );
}

/* ========== Main Component ========== */

interface EmergencyCoverageProps {
    open: boolean;
    onClose: () => void;
    requestId: string;
}

export function EmergencyCoverage({ open, onClose, requestId }: EmergencyCoverageProps) {
    const { data: request, isLoading: isLoadingRequest } = useSwapRequest(requestId);
    const { data: usersData, isLoading: isLoadingUsers } = useUsers();

    const approveMutation = useSwapAction('approve');
    const declineMutation = useSwapAction('decline');
    const notifyMutation = useNotifyQualifiedStaff();

    const { data: suggestions, isLoading: isLoadingSuggestions } = useShiftSuggestions(request?.requester_assignment_id || '');

    const handleApprove = () => {
        if (!request) return;
        approveMutation.mutate({ id: request.id, data: { note: 'Emergency approved by manager' }, isDrop: request.type === 'drop' });
        onClose();
    };

    const handleDecline = () => {
        if (!request) return;
        declineMutation.mutate({ id: request.id, data: { note: 'Manager declined drop request' }, isDrop: request.type === 'drop' });
        onClose();
    };

    const handleNotifyAll = () => {
        if (!request) return;
        notifyMutation.mutate(request.id);
    };

    const isLoading = isLoadingRequest || isLoadingUsers || isLoadingSuggestions;

    // Derived values
    const shiftDate = request?.shift_date ? format(parseISO(request.shift_date), 'eeee, MMM d') : '';
    const shiftInfo = `${request?.shift_label || 'Shift'} · ${request?.shift_time || ''}`;

    const expiresAt = request?.expires_at ? parseISO(request.expires_at) : null;
    const now = new Date();
    const minutesLeft = expiresAt ? differenceInMinutes(expiresAt, now) : 0;
    const isUrgent = expiresAt && minutesLeft < 60 && minutesLeft > 0;

    const filteredUsers = useMemo(() => {
        if (!usersData?.users || !suggestions) return [];
        const suggestionIds = new Set(suggestions.map(s => s.user_id));
        return usersData.users.filter(u => suggestionIds.has(u.id));
    }, [usersData, suggestions]);

    if (!requestId) return null;

    return (
        <SidePanel
            open={open}
            onClose={onClose}
            title="🚨 Emergency Coverage"
            subtitle={`${shiftDate} · ${shiftInfo}`}
            width="sm:w-[420px]"
            headerColor="bg-danger"
        >
            <div className="p-5 space-y-6">
                {isLoading ? (
                    <div className="py-20 flex flex-col items-center justify-center text-gray-300">
                        <Loader2 size={40} className="animate-spin mb-4" />
                        <span className="text-sm font-medium">Loading coverage options…</span>
                    </div>
                ) : (
                    <>
                        {/* Dropped by */}
                        <div className="flex items-center gap-2 text-sm text-gray-600">
                            <User size={14} />
                            <span>Dropped by: <strong className="text-navy">{request?.requester_name}</strong></span>
                        </div>

                        {/* Shift Status */}
                        <div className="bg-gray-50 rounded-xl p-4 shadow-inner">
                            <div className="flex items-center justify-between mb-3">
                                <h4 className="text-sm font-bold text-navy">Coverage Status</h4>
                                {request?.status === 'PENDING_MANAGER' ? (
                                    <Badge variant="amber">Pickup Pending Approval</Badge>
                                ) : (
                                    <Badge variant="red">Currently Uncovered</Badge>
                                )}
                            </div>

                            {expiresAt && (
                                <div className="flex items-center gap-2 mb-2 text-danger">
                                    <Clock size={14} className={isUrgent ? 'animate-pulse' : ''} />
                                    <span className="text-sm font-bold">
                                        {minutesLeft > 0 ? `Closes in ${minutesLeft} minutes` : 'Window Closed'}
                                    </span>
                                </div>
                            )}

                            <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                                <div
                                    className={`h-2 rounded-full transition-all duration-700 ${request?.status === 'PENDING_MANAGER' ? 'bg-success' : 'bg-danger'}`}
                                    style={{ width: request?.status === 'PENDING_MANAGER' ? '100%' : '5%' }}
                                />
                            </div>
                            <p className="text-[11px] text-gray-500 italic">
                                {request?.status === 'PENDING_MANAGER' ? 'A staff member has claimed this, awaiting your approval below.' : 'No staff have picked up this drop yet.'}
                            </p>
                        </div>

                        {/* Pickup Pending Approval Section */}
                        {request?.status === 'PENDING_MANAGER' && (
                            <div className="bg-teal-50 rounded-xl p-4 border border-teal/20 animate-fade-in ring-4 ring-teal/5">
                                <div className="flex items-center justify-between mb-4">
                                    <h4 className="text-sm font-black text-teal uppercase tracking-wider">Pickup Claimed!</h4>
                                    <Badge variant="teal">Action Required</Badge>
                                </div>
                                <div className="flex items-center gap-3 mb-5 bg-white p-3 rounded-lg shadow-sm">
                                    <Avatar name={request.pickup_name || 'Staff'} size="md" />
                                    <div>
                                        <p className="text-sm font-bold text-navy">{request.pickup_name}</p>
                                        <p className="text-xs text-gray-500">Ready to cover this shift</p>
                                    </div>
                                </div>
                                <div className="flex gap-2">
                                    <button
                                        onClick={handleApprove}
                                        disabled={approveMutation.isPending}
                                        className="flex-1 py-2.5 text-sm font-bold bg-teal text-white rounded-lg hover:bg-teal-dark transition-all shadow-md active:scale-95 disabled:opacity-50"
                                    >
                                        {approveMutation.isPending ? 'Approving...' : 'Approve Pickup'}
                                    </button>
                                    <button
                                        onClick={handleDecline}
                                        disabled={declineMutation.isPending}
                                        className="px-4 py-2.5 text-sm font-semibold border border-danger/30 text-danger rounded-lg hover:bg-danger-50 transition-base disabled:opacity-50"
                                    >
                                        Reject
                                    </button>
                                </div>
                            </div>
                        )}

                        {/* Qualified Staff */}
                        <div>
                            <div className="flex items-center justify-between mb-3">
                                <h4 className="text-sm font-bold text-navy">Qualified & Available Staff</h4>
                                <span className="text-[10px] bg-gray-100 px-2 py-0.5 rounded font-bold">{filteredUsers.length} Found</span>
                            </div>
                            <p className="text-xs text-gray-500 mb-4">Matches skill profile and no hard constraints.</p>

                            <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2 scrollbar-thin">
                                {filteredUsers.map((u) => (
                                    <QualifiedStaffRow key={u.id} user={u} shiftId={request?.requester_assignment_id || ''} />
                                ))}
                                {filteredUsers.length === 0 && (
                                    <div className="py-10 text-center">
                                        <p className="text-sm text-gray-400">No other qualified staff found.</p>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Actions */}
                        <div className="space-y-3 pt-4 border-t border-border-gray">
                            <button
                                onClick={handleNotifyAll}
                                disabled={notifyMutation.isPending || filteredUsers.length === 0}
                                className="w-full py-3 bg-navy text-white text-sm font-bold rounded-xl hover:bg-navy/90 transition-all shadow-lg flex items-center justify-center gap-2 group disabled:opacity-50"
                            >
                                <Bell size={18} className={notifyMutation.isPending ? 'animate-spin' : 'group-hover:animate-bounce'} />
                                {notifyMutation.isPending ? 'Sending Notifications...' : 'Notify All Qualified'}
                            </button>
                            <button
                                onClick={onClose}
                                className="w-full py-3 border border-border-gray text-gray-500 text-sm font-bold rounded-xl hover:bg-gray-50 transition-all text-center"
                            >
                                Close Panel
                            </button>
                        </div>
                    </>
                )}
            </div>
        </SidePanel>
    );
}
