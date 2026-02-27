import React, { useEffect, useState } from 'react';
import {
    ArrowLeftRight,
    Clock,
    Check,
    X,
    AlertTriangle,
    CheckCircle,
    MessageSquare,
    Loader2,
} from 'lucide-react';
import { format, parseISO, isBefore, addHours } from 'date-fns';
import { useSearchParams } from 'react-router-dom';

import { AppLayout } from '../../components/NavBar';
import { Avatar } from '../../components/Avatar';
import { Badge } from '../../components/Badge';
import { Modal } from '../../components/Modal';
import { NotificationCentre } from '../staff/NotificationCentre';
import { EmergencyCoverage } from './EmergencyCoverage';

import { useNotifications, useSwapRequests, useSwapAction } from '../../lib/api/hooks';
import { SwapRequestResponse, SwapStatus } from '../../lib/api/types';

/* ========== Sub-Components ========== */

interface RequestCardProps {
    request: SwapRequestResponse;
    onAction: (id: string, action: 'approve' | 'decline' | 'reject', note?: string, isDrop?: boolean) => void;
    onEmergencyCoverage: (requestId: string) => void;
    isPending: boolean;
    highlighted?: boolean;
}

function RequestCard({ request, onAction, onEmergencyCoverage, isPending, highlighted = false }: RequestCardProps) {
    const [showRejectModal, setShowRejectModal] = useState(false);
    const [showApproveModal, setShowApproveModal] = useState(false);
    const [note, setNote] = useState('');

    const isDrop = request.type === 'drop';
    const expiresAt = request.expires_at ? parseISO(request.expires_at) : null;
    const isUrgent = expiresAt && isBefore(expiresAt, addHours(new Date(), 4)) && request.status !== 'APPROVED';

    const getStatusConfig = (status: SwapStatus) => {
        switch (status) {
            case 'PENDING_ACCEPTEE': return { label: 'AWAITING STAFF ACCEPTANCE', variant: 'gray' as const };
            case 'PENDING_MANAGER': return { label: 'AWAITING YOUR APPROVAL', variant: 'amber' as const };
            case 'OPEN': return { label: 'OPEN FOR PICKUP', variant: 'green' as const };
            case 'APPROVED': return { label: 'APPROVED', variant: 'green' as const };
            case 'REJECTED': return { label: 'REJECTED', variant: 'red' as const };
            case 'EXPIRED': return { label: 'EXPIRED', variant: 'gray' as const };
            case 'CANCELLED': return { label: 'CANCELLED', variant: 'gray' as const };
            default: return { label: status, variant: 'gray' as const };
        }
    };

    const statusInfo = getStatusConfig(request.status);
    const dateFormatted = request.shift_date ? format(parseISO(request.shift_date), 'eeee, MMM d') : 'Unknown Date';

    const handleConfirmAction = (action: 'approve' | 'decline' | 'reject') => {
        onAction(request.id, action, note, isDrop);
        setShowRejectModal(false);
        setShowApproveModal(false);
        setNote('');
    };

    return (
        <div
            id={`request-${request.id}`}
            className={`bg-white rounded-xl border ${isUrgent ? 'border-danger/30 shadow-lg' : 'border-border-gray shadow-sm'
                } p-5 transition-base hover:shadow-md ${isUrgent ? 'border-l-4 border-l-danger' : ''} ${highlighted ? 'ring-2 ring-teal/40' : ''}`}
        >
            {/* Urgent banner */}
            {isUrgent && (
                <div className="flex items-center gap-2 mb-3 px-3 py-2 bg-danger-50 rounded-lg">
                    <AlertTriangle size={14} className="text-danger" />
                    <span className="text-xs font-bold text-danger uppercase">Urgent — Expires soon</span>
                </div>
            )}

            {/* Header badges */}
            <div className="flex items-center gap-2 mb-3 flex-wrap">
                <Badge variant={request.type === 'swap' ? 'teal' : 'purple'}>
                    {request.type === 'swap' ? 'SWAP REQUEST' : 'DROP REQUEST'}
                </Badge>
                <Badge variant={statusInfo.variant}>{statusInfo.label}</Badge>
            </div>

            {/* Content */}
            <div className="mb-3">
                {request.type === 'swap' ? (
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                        <Avatar name={request.requester_name || 'Staff'} size="sm" />
                        <span className="font-semibold text-navy">{request.requester_name}</span>
                        <ArrowLeftRight size={14} className="text-gray-400" />
                        {request.target_name ? (
                            <>
                                <Avatar name={request.target_name} size="sm" />
                                <span className="font-semibold text-navy">{request.target_name}</span>
                            </>
                        ) : (
                            <span className="text-sm text-gray-400">Open Swap</span>
                        )}
                    </div>
                ) : (
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                        <Avatar name={request.requester_name || 'Staff'} size="sm" />
                        <span className="font-semibold text-navy">{request.requester_name} dropped</span>
                    </div>
                )}
                <div className="flex items-center gap-3 text-sm text-gray-600 flex-wrap">
                    <span className="flex items-center gap-1">
                        <Clock size={13} /> {dateFormatted} · {request.shift_label} · {request.shift_time}
                    </span>
                </div>
            </div>

            {/* Note */}
            {request.resolution_note && (
                <div className="flex items-start gap-2 mb-3 px-3 py-2 bg-gray-50 rounded-lg">
                    <MessageSquare size={13} className="text-gray-400 mt-0.5" />
                    <p className="text-sm text-gray-600 italic">"{request.resolution_note}"</p>
                </div>
            )}

            {/* Pickup/Acceptee Badge */}
            {(request.pickup_name || (request.status === 'PENDING_MANAGER' && request.target_name)) && (
                <div className="flex items-center gap-2 mb-3">
                    <Badge variant="green">
                        <Check size={12} className="mr-1" /> {request.pickup_name || request.target_name} accepted
                    </Badge>
                </div>
            )}

            {/* Requested time */}
            <p className="text-xs text-gray-400 mb-4">Requested: {format(parseISO(request.created_at), 'MMM d, h:mm a')}</p>

            {/* Actions */}
            <div className="flex items-center justify-end gap-2 pt-3 border-t border-border-gray flex-wrap">
                {isPending && <Loader2 size={16} className="animate-spin text-teal mr-auto sm:mr-0" />}

                {request.status === 'PENDING_ACCEPTEE' && (
                    <span className="text-xs text-gray-500 w-full sm:w-auto sm:mr-auto">Awaiting {request.target_name}'s acceptance</span>
                )}

                {request.status === 'PENDING_MANAGER' && (
                    <>
                        {isDrop && (
                            <button
                                onClick={() => onEmergencyCoverage(request.id)}
                                className="px-3 py-1.5 text-xs font-semibold border border-amber-warn/30 text-amber-warn rounded-lg hover:bg-amber-warn-50 transition-base flex-1 sm:flex-none"
                            >
                                Emergency Coverage
                            </button>
                        )}
                        <button
                            onClick={() => setShowRejectModal(true)}
                            className="px-3 py-1.5 text-xs font-semibold border border-danger/30 text-danger rounded-lg hover:bg-danger-50 transition-base flex-1 sm:flex-none"
                        >
                            Decline
                        </button>
                        <button
                            onClick={() => setShowApproveModal(true)}
                            className="px-4 py-1.5 text-xs font-bold bg-teal text-white rounded-lg hover:bg-teal-dark transition-base flex-1 sm:flex-none"
                        >
                            Approve {isDrop ? 'Drop' : 'Swap'}
                        </button>
                    </>
                )}

                {request.status === 'OPEN' && (
                    <>
                        <button
                            onClick={() => onEmergencyCoverage(request.id)}
                            className="px-3 py-1.5 text-xs font-semibold border border-amber-warn/30 text-amber-warn rounded-lg hover:bg-amber-warn-50 transition-base"
                        >
                            Emergency Coverage
                        </button>
                        <span className="text-xs text-teal font-medium">Available for pickup by other staff</span>
                    </>
                )}
            </div>

            {/* Approve Modal */}
            <Modal open={showApproveModal} onClose={() => setShowApproveModal(false)} title={`Approve ${isDrop ? 'Drop' : 'Swap'}`} width="max-w-md">
                <div className="p-4">
                    <p className="text-sm text-gray-600 mb-4">
                        Are you sure you want to approve this {request.type}? This will update the schedule immediately.
                    </p>
                    <textarea
                        placeholder="Resolution note (optional)…"
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                        className="w-full px-3 py-2 border border-border-gray rounded-lg text-sm text-navy focus:outline-none focus:ring-2 focus:ring-teal/40 resize-none"
                        rows={2}
                    />
                    <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 mt-6">
                        <button onClick={() => setShowApproveModal(false)} className="w-full sm:w-auto text-sm text-gray-500">Cancel</button>
                        <button
                            onClick={() => handleConfirmAction('approve')}
                            className="w-full sm:w-auto px-6 py-2 bg-teal text-white font-bold rounded-lg hover:bg-teal-dark transition-base"
                        >
                            Confirm Approval
                        </button>
                    </div>
                </div>
            </Modal>

            {/* Decline Modal */}
            <Modal open={showRejectModal} onClose={() => setShowRejectModal(false)} title="Decline Request" width="max-w-md">
                <div className="p-4">
                    <p className="text-sm text-gray-600 mb-4">
                        Provide a reason why this {request.type} request is being declined. This will be visible to the staff.
                    </p>
                    <textarea
                        placeholder="Decline reason…"
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                        className="w-full px-3 py-2 border border-border-gray rounded-lg text-sm text-navy focus:outline-none focus:ring-2 focus:ring-danger/40 resize-none"
                        rows={2}
                    />
                    <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 mt-6">
                        <button onClick={() => setShowRejectModal(false)} className="w-full sm:w-auto text-sm text-gray-500">Cancel</button>
                        <button
                            onClick={() => handleConfirmAction('decline')}
                            disabled={!note}
                            className="w-full sm:w-auto px-6 py-2 bg-danger text-white font-bold rounded-lg hover:bg-danger/90 disabled:opacity-50 transition-base"
                        >
                            Confirm Decline
                        </button>
                    </div>
                </div>
            </Modal>
        </div>
    );
}

function EmptyState() {
    return (
        <div className="flex flex-col items-center justify-center py-20 text-center animate-fade-in">
            <div className="w-20 h-20 bg-success-50 rounded-full flex items-center justify-center mb-4">
                <CheckCircle size={40} className="text-success" />
            </div>
            <h3 className="text-lg font-bold text-navy mb-1">All caught up!</h3>
            <p className="text-sm text-gray-500">No requests in this category.</p>
        </div>
    );
}

/* ========== Main Component ========== */

type Tab = 'pending' | 'approved' | 'resolved' | 'expired';

export function SwapApprovalQueue() {
    const [activeTab, setActiveTab] = useState<Tab>('pending');
    const [isNotificationOpen, setIsNotificationOpen] = useState(false);
    const [isCoverageOpen, setIsCoverageOpen] = useState(false);
    const [coverageRequestId, setCoverageRequestId] = useState<string | null>(null);
    const [searchParams] = useSearchParams();
    const highlightedRequestId = searchParams.get('requestId');

    const { data, isLoading } = useSwapRequests();
    const { data: notificationsData } = useNotifications();
    const approveMutation = useSwapAction('approve');
    const declineMutation = useSwapAction('decline');
    const rejectMutation = useSwapAction('reject');
    const unreadCount = notificationsData?.unread_count || 0;

    const handleAction = (id: string, action: 'approve' | 'decline' | 'reject', note?: string, isDrop?: boolean) => {
        const mutation = action === 'approve' ? approveMutation : action === 'decline' ? declineMutation : rejectMutation;
        mutation.mutate({ id, data: { note }, isDrop });
    };

    const requests = data?.requests || [];

    // Filter requests for tabs
    const pendingRequests = requests.filter(r => ['PENDING_ACCEPTEE', 'PENDING_MANAGER', 'OPEN'].includes(r.status));
    const approvedRequests = requests.filter(r => r.status === 'APPROVED');
    const resolvedRequests = requests.filter(r => ['REJECTED', 'CANCELLED'].includes(r.status));
    const expiredRequests = requests.filter(r => r.status === 'EXPIRED');

    const getTabContent = () => {
        switch (activeTab) {
            case 'pending': return pendingRequests;
            case 'approved': return approvedRequests;
            case 'resolved': return resolvedRequests;
            case 'expired': return expiredRequests;
            default: return [];
        }
    };

    const currentRequests = getTabContent();

    useEffect(() => {
        if (!highlightedRequestId) return;
        const target = requests.find((r) => r.id === highlightedRequestId);
        if (!target) return;
        if (target.status === 'APPROVED') setActiveTab('approved');
        else if (target.status === 'EXPIRED') setActiveTab('expired');
        else if (['REJECTED', 'CANCELLED'].includes(target.status)) setActiveTab('resolved');
        else setActiveTab('pending');
    }, [highlightedRequestId, requests]);

    useEffect(() => {
        if (!highlightedRequestId) return;
        const el = document.getElementById(`request-${highlightedRequestId}`);
        if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }, [highlightedRequestId, currentRequests.length, activeTab]);

    const tabs: { key: Tab; label: string; count?: number }[] = [
        { key: 'pending', label: 'Pending', count: pendingRequests.length },
        { key: 'approved', label: 'Approved', count: approvedRequests.length > 0 ? approvedRequests.length : undefined },
        { key: 'resolved', label: 'Resolved' },
        { key: 'expired', label: 'Expired' },
    ];

    return (
        <AppLayout
            title="Swap & Drop Requests"
            role="manager"
            notificationCount={unreadCount}
            onBellClick={() => setIsNotificationOpen(true)}
        >
            <div className="p-4 md:p-6 max-w-4xl mx-auto">
                <div className="mb-6 flex items-center justify-between gap-3 flex-wrap">
                    <h1 className="text-xl sm:text-2xl font-bold text-navy">Swap & Drop Requests</h1>
                    {isLoading && <Loader2 size={24} className="animate-spin text-teal" />}
                </div>

                {/* Tabs */}
                <div className="flex gap-0 border-b border-border-gray mb-6 overflow-x-auto">
                    {tabs.map((tab) => (
                        <button
                            key={tab.key}
                            onClick={() => setActiveTab(tab.key)}
                            className={`px-5 py-3 text-sm font-medium border-b-2 transition-base ${activeTab === tab.key
                                ? 'border-teal text-teal'
                                : 'border-transparent text-gray-500 hover:text-navy'
                                }`}
                        >
                            {tab.label}
                            {tab.count !== undefined && (
                                <span className="ml-1.5 px-1.5 py-0.5 text-[10px] font-bold bg-teal/10 text-teal rounded-full">
                                    {tab.count}
                                </span>
                            )}
                        </button>
                    ))}
                </div>

                {/* Content */}
                {isLoading ? (
                    <div className="py-20 flex justify-center">
                        <Loader2 size={32} className="animate-spin text-teal/40" />
                    </div>
                ) : currentRequests.length === 0 ? (
                    <EmptyState />
                ) : (
                    <div className="space-y-4">
                        {currentRequests.map((r) => (
                            <RequestCard
                                key={r.id}
                                request={r}
                                onAction={handleAction}
                                onEmergencyCoverage={(requestId) => {
                                    setCoverageRequestId(requestId);
                                    setIsCoverageOpen(true);
                                }}
                                isPending={approveMutation.isPending || declineMutation.isPending || rejectMutation.isPending}
                                highlighted={highlightedRequestId === r.id}
                            />
                        ))}
                    </div>
                )}
            </div>

            <NotificationCentre
                open={isNotificationOpen}
                onClose={() => setIsNotificationOpen(false)}
            />

            <EmergencyCoverage
                open={isCoverageOpen}
                onClose={() => setIsCoverageOpen(false)}
                requestId={coverageRequestId || ""}
            />
        </AppLayout>
    );
}
