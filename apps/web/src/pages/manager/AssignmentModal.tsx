import React, { useState } from 'react';
import { useQueries } from '@tanstack/react-query';
import { Search, Check, AlertTriangle, X, Loader2, CheckCircle } from 'lucide-react';
import { format, parseISO } from 'date-fns';

import { Modal } from '../../components/Modal';
import { Avatar } from '../../components/Avatar';

import { ShiftResponse } from '../../lib/api/types';
import { useUsers, useAssignments, useCreateAssignment, keys } from '../../lib/api/hooks';
import { previewAssignment } from '../../lib/api/client';

export interface AssignmentModalProps {
    shift: ShiftResponse;
    open: boolean;
    onClose: () => void;
}

export function AssignmentModal({ shift, open, onClose }: AssignmentModalProps) {
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedStaff, setSelectedStaff] = useState<string | null>(null);
    const [expandedViolation, setExpandedViolation] = useState<string | null>(null);
    const [overrideReason, setOverrideReason] = useState('');
    const [showOverrideInput, setShowOverrideInput] = useState<string | null>(null);
    const [isSuccess, setIsSuccess] = useState(false);

    // 1. Fetch Users & Assignments
    const { data: usersData, isLoading: isLoadingUsers } = useUsers(shift.location_id);
    const { data: assignmentsData } = useAssignments(shift.id);
    const createAssignmentMutation = useCreateAssignment();

    const allStaff = usersData?.users.filter(u => u.role === 'staff' && u.is_active) || [];
    const assignedUserIds = new Set(
        assignmentsData?.assignments.filter(a => a.status === 'assigned').map(a => a.user_id) || []
    );

    // Filter out already assigned staff, and match search query
    const eligibleStaff = allStaff.filter(u => !assignedUserIds.has(u.id));
    const searchFilteredStaff = eligibleStaff.filter(u => u.name.toLowerCase().includes(searchQuery.toLowerCase()));

    // 2. Fetch Constraints Preview for all eligible staff
    const previewQueries = useQueries({
        queries: searchFilteredStaff.map(user => ({
            queryKey: keys.assignmentPreview(shift.id, user.id),
            queryFn: () => previewAssignment(shift.id, user.id),
            enabled: !!shift.id && !!user.id && open,
            staleTime: 60000,
        }))
    });

    const isFetchingPreviews = previewQueries.some(q => q.isLoading);

    const handleAssign = () => {
        if (!selectedStaff) return;
        createAssignmentMutation.mutate(
            { shiftId: shift.id, data: { user_id: selectedStaff, override_reason: overrideReason || undefined } },
            {
                onSuccess: () => {
                    setIsSuccess(true);
                    setTimeout(() => {
                        resetAndClose();
                    }, 2000);
                }
            }
        );
    };

    const resetAndClose = () => {
        setIsSuccess(false);
        setSelectedStaff(null);
        setExpandedViolation(null);
        setOverrideReason('');
        setShowOverrideInput(null);
        setSearchQuery('');
        onClose();
    };

    const shiftDateStr = format(parseISO(shift.date), "eeee, MMMM d, yyyy");

    function formatTime(t24: string) {
        if (!t24) return '';
        const [h, m] = t24.split(':').map(Number);
        const period = h >= 12 ? 'pm' : 'am';
        const h12 = h % 12 || 12;
        return `${h12}${m > 0 ? `:${m.toString().padStart(2, '0')}` : ''}${period}`;
    }

    if (isSuccess) {
        const assignedName = allStaff.find(u => u.id === selectedStaff)?.name;
        return (
            <Modal open={open} onClose={resetAndClose} title="Assignment Complete" width="max-w-md">
                <div className="py-8 flex flex-col items-center text-center animate-fade-in">
                    <div className="w-16 h-16 rounded-full bg-success-50 flex items-center justify-center mb-4">
                        <CheckCircle size={36} className="text-success" />
                    </div>
                    <h3 className="text-lg font-bold text-navy mb-1">{assignedName} assigned</h3>
                    <p className="text-sm text-gray-500">
                        {format(parseISO(shift.date), "eeee")} {formatTime(shift.start_local)}–{formatTime(shift.end_local)} · {shift.required_skill.name}
                    </p>
                    <button
                        onClick={resetAndClose}
                        className="mt-6 px-6 py-2.5 bg-teal text-white font-semibold rounded-lg hover:bg-teal-dark transition-base"
                    >
                        Done
                    </button>
                </div>
            </Modal>
        );
    }

    return (
        <Modal
            open={open}
            onClose={resetAndClose}
            title={`Assign Staff — ${shift.required_skill.name} Shift`}
            subtitle={shiftDateStr}
            width="max-w-xl"
            footer={
                <div className="flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-between gap-3">
                    <button onClick={resetAndClose} className="w-full sm:w-auto text-sm text-gray-500 hover:text-navy transition-base">
                        Cancel
                    </button>
                    <button
                        onClick={handleAssign}
                        disabled={!selectedStaff || createAssignmentMutation.isPending || (!!showOverrideInput && overrideReason.length < 10)}
                        className="w-full sm:w-auto justify-center px-5 py-2.5 bg-teal text-white font-semibold rounded-lg hover:bg-teal-dark disabled:opacity-50 disabled:cursor-not-allowed transition-base flex items-center gap-2"
                    >
                        {createAssignmentMutation.isPending ? (
                            <>
                                <Loader2 size={16} className="animate-spin" /> Assigning…
                            </>
                        ) : selectedStaff ? (
                            `Assign selected staff`
                        ) : (
                            'Select a staff member'
                        )}
                    </button>
                </div>
            }
        >
            {/* Shift Details */}
            <div className="bg-gray-50 rounded-lg p-4 mb-5">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                    <div>
                        <span className="text-gray-500">Time:</span>
                        <span className="ml-2 font-medium text-navy">{formatTime(shift.start_local)} – {formatTime(shift.end_local)}</span>
                    </div>
                    <div>
                        <span className="text-gray-500">Required skill:</span>
                        <span className="ml-2 font-medium text-navy">{shift.required_skill.name}</span>
                    </div>
                    <div>
                        <span className="text-gray-500">Headcount needed:</span>
                        <span className="ml-2 font-medium text-navy">{shift.headcount_needed}</span>
                    </div>
                    <div>
                        <span className="text-gray-500">Current assigned:</span>
                        <span className="ml-2 font-medium text-navy">{assignedUserIds.size}</span>
                    </div>
                </div>
            </div>

            {/* Search */}
            <div className="mb-4">
                <label className="text-sm font-semibold text-navy mb-2 block">Select a staff member</label>
                <div className="relative">
                    <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Search by name…"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-9 pr-4 py-2.5 rounded-lg border border-border-gray bg-gray-50 text-sm text-navy placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-teal/40 transition-base"
                        disabled={isLoadingUsers || createAssignmentMutation.isPending}
                    />
                </div>
            </div>

            {/* Staff List */}
            {isLoadingUsers ? (
                <div className="py-10 flex justify-center text-gray-400">
                    <Loader2 size={24} className="animate-spin" />
                </div>
            ) : eligibleStaff.length === 0 ? (
                <div className="py-10 text-center text-sm text-gray-500">
                    No eligible staff found for this location.
                </div>
            ) : (
                <div className="space-y-1 max-h-72 overflow-y-auto pr-1">
                    {searchFilteredStaff.map((c, index) => {
                        const previewResponse = previewQueries[index].data;
                        const isLoadingPreview = previewQueries[index].isLoading;

                        const isSelected = selectedStaff === c.id;
                        const isExpanded = expandedViolation === c.id;
                        const showingOverride = showOverrideInput === c.id;

                        let constraintStatus: 'pass' | 'warning' | 'violation' | 'loading' = 'loading';
                        if (!isLoadingPreview && previewResponse) {
                            if (!previewResponse.valid && !previewResponse.requires_override) {
                                constraintStatus = 'violation';
                            } else if (previewResponse.requires_override || previewResponse.warnings.length > 0) {
                                constraintStatus = 'warning';
                            } else {
                                constraintStatus = 'pass';
                            }
                        }

                        const violation = previewResponse?.violations?.[0];
                        const warning = previewResponse?.warnings?.[0];
                        const primaryMessage = violation?.description || warning?.description || 'All constraints passed';

                        const hours = previewResponse?.projected_weekly_hours ?? 0;
                        const maxHours = c.desired_hours_per_week || 40;

                        return (
                            <div key={c.id}>
                                <button
                                    onClick={() => {
                                        if (constraintStatus === 'violation') {
                                            setExpandedViolation(isExpanded ? null : c.id);
                                            return;
                                        }
                                        if (constraintStatus === 'warning' && previewResponse?.requires_override) {
                                            setShowOverrideInput(showingOverride ? null : c.id);
                                            // Select staff only if they enter an override reason (handled in the textarea UI)
                                            if (!showingOverride) setSelectedStaff(null);
                                            return;
                                        }
                                        // Pass or soft warning
                                        setSelectedStaff(c.id);
                                        setShowOverrideInput(null);
                                    }}
                                    disabled={createAssignmentMutation.isPending || constraintStatus === 'loading'}
                                    className={`w-full flex items-center gap-3 px-4 py-3.5 rounded-lg text-left transition-base ${isSelected
                                        ? 'bg-teal-50 border-2 border-teal'
                                        : constraintStatus === 'violation'
                                            ? 'bg-gray-50 opacity-75 hover:opacity-100'
                                            : 'bg-white border border-border-gray hover:border-teal/30 hover:shadow-sm mt-1 mb-1'
                                        } ${createAssignmentMutation.isPending ? 'pointer-events-none opacity-50' : ''}`}
                                >
                                    <Avatar name={c.name} size="md" />
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-semibold text-navy">{c.name}</p>
                                        <div className="flex items-center gap-2 mt-1">
                                            <div className="w-24 bg-gray-200 rounded-full h-1.5">
                                                <div
                                                    className={`h-1.5 rounded-full ${hours >= maxHours && maxHours > 0 ? 'bg-danger' : hours >= maxHours - 5 ? 'bg-amber-warn' : 'bg-teal'}`}
                                                    style={{ width: `${Math.min((hours / (maxHours || 40)) * 100, 100)}%` }}
                                                />
                                            </div>
                                            <span className="text-xs text-gray-500">{hours.toFixed(1)}h / {maxHours}h</span>
                                        </div>
                                    </div>

                                    {constraintStatus === 'loading' && (
                                        <Loader2 size={16} className="text-gray-400 animate-spin" />
                                    )}
                                    {constraintStatus === 'pass' && (
                                        <Check size={18} className="text-success flex-shrink-0" />
                                    )}
                                    {constraintStatus === 'warning' && (
                                        <div className="flex-shrink-0" title={primaryMessage}>
                                            <AlertTriangle size={18} className="text-amber-warn" />
                                        </div>
                                    )}
                                    {constraintStatus === 'violation' && (
                                        <div className="flex-shrink-0" title={primaryMessage}>
                                            <X size={18} className="text-danger" />
                                        </div>
                                    )}
                                </button>

                                {/* Violation Detail */}
                                {isExpanded && violation && (
                                    <div className="ml-4 mt-1 p-3 bg-danger-50 border border-danger/20 rounded-lg text-sm text-danger animate-fade-in">
                                        <p className="font-semibold mb-1">{violation.rule}</p>
                                        <p className="font-medium text-xs">{violation.description}</p>

                                        {previewResponse?.suggestions && previewResponse.suggestions.length > 0 && (
                                            <div className="mt-3 bg-white p-2 rounded border border-danger/10">
                                                <p className="text-[10px] uppercase font-bold text-gray-500 mb-1">Suggested Alternatives</p>
                                                {previewResponse.suggestions.map((sug, i) => (
                                                    <p key={i} className="text-xs text-navy font-medium">• {sug.name} — <span className="text-gray-500 font-normal">{sug.reason}</span></p>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* Override Input */}
                                {showingOverride && (
                                    <div className="ml-4 mt-1 p-3 bg-amber-warn-50 border border-amber-warn/20 rounded-lg animate-fade-in">
                                        <p className="text-xs text-amber-warn font-medium mb-2">{primaryMessage}</p>
                                        <textarea
                                            placeholder="Override reason (min 10 characters)…"
                                            value={overrideReason}
                                            onChange={(e) => setOverrideReason(e.target.value)}
                                            className="w-full px-3 py-2 border border-border-gray rounded-lg text-sm text-navy placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-amber-warn/40 resize-none"
                                            rows={2}
                                        />
                                        <button
                                            disabled={overrideReason.length < 10}
                                            onClick={() => {
                                                setSelectedStaff(c.id);
                                            }}
                                            className={`mt-2 px-4 py-1.5 text-xs font-semibold rounded-lg transition-base ${overrideReason.length >= 10 && selectedStaff === c.id ? 'bg-success text-white' : 'bg-amber-warn text-white disabled:opacity-50 hover:bg-amber-warn/90'}`}
                                        >
                                            {selectedStaff === c.id ? 'Override Saved. Click Assign.' : 'Save Override'}
                                        </button>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}
        </Modal>
    );
}
