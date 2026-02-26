import React, { useState } from 'react';
import {
    ArrowLeftRight,
    ArrowDown,
    Clock,
    Check,
    X,
    AlertTriangle,
    CheckCircle,
    MessageSquare,
    Users,
} from 'lucide-react';
import { AppLayout } from '../../components/NavBar';
import { Avatar } from '../../components/Avatar';
import { Badge } from '../../components/Badge';
import { Modal } from '../../components/Modal';

/* ========== Types & Mock Data ========== */

interface SwapRequest {
    id: string;
    type: 'swap' | 'drop';
    status: 'awaiting-staff' | 'awaiting-manager' | 'open-pickup' | 'urgent-no-claims';
    from: string;
    to?: string;
    shift: string;
    date: string;
    time: string;
    note?: string;
    timeAgo: string;
    constraintOk?: boolean;
    acceptedBy?: string;
    notifiedCount?: number;
    qualifiedCount?: number;
    expiresIn?: string;
}

const mockRequests: SwapRequest[] = [
    {
        id: '1',
        type: 'swap',
        status: 'awaiting-staff',
        from: 'Carlos M.',
        to: 'Maria L.',
        shift: 'Bartender',
        date: 'Friday, Aug 15',
        time: '6pm – 11pm',
        note: 'Family emergency, need coverage',
        timeAgo: '2 hours ago',
    },
    {
        id: '2',
        type: 'swap',
        status: 'awaiting-manager',
        from: 'Jordan T.',
        to: 'Sam K.',
        shift: 'Server',
        date: 'Saturday, Aug 16',
        time: '2pm – 10pm',
        note: 'Jordan and Sam mutually agreed to swap',
        timeAgo: '4 hours ago',
        constraintOk: true,
        acceptedBy: 'Sam',
    },
    {
        id: '3',
        type: 'drop',
        status: 'open-pickup',
        from: 'Alex R.',
        shift: 'Bartender',
        date: 'Sunday, Aug 17',
        time: '4pm – 11pm',
        notifiedCount: 2,
        qualifiedCount: 3,
        expiresIn: 'in 6 hours (before 6pm Sunday)',
        timeAgo: '5 hours ago',
    },
    {
        id: '4',
        type: 'drop',
        status: 'urgent-no-claims',
        from: 'Priya N.',
        shift: 'Bartender',
        date: 'Sunday, Aug 17',
        time: '7pm – 11pm',
        expiresIn: 'in 1 hour',
        timeAgo: '8 hours ago',
    },
];

/* ========== Sub-Components ========== */

function RequestCard({ request }: { request: SwapRequest }) {
    const isUrgent = request.status === 'urgent-no-claims';

    const statusConfig = {
        'awaiting-staff': { label: 'AWAITING STAFF ACCEPTANCE', variant: 'gray' as const },
        'awaiting-manager': { label: 'AWAITING YOUR APPROVAL', variant: 'amber' as const },
        'open-pickup': { label: 'OPEN FOR PICKUP', variant: 'green' as const },
        'urgent-no-claims': { label: 'URGENT — NO CLAIMS', variant: 'red' as const },
    };

    const statusInfo = statusConfig[request.status];

    return (
        <div
            className={`bg-white rounded-xl border ${isUrgent ? 'border-danger/30 shadow-lg' : 'border-border-gray shadow-sm'
                } p-5 transition-base hover:shadow-md ${isUrgent ? 'border-l-4 border-l-danger' : ''}`}
        >
            {/* Urgent banner */}
            {isUrgent && (
                <div className="flex items-center gap-2 mb-3 px-3 py-2 bg-danger-50 rounded-lg">
                    <AlertTriangle size={14} className="text-danger" />
                    <span className="text-xs font-bold text-danger uppercase">Urgent — Expires {request.expiresIn}</span>
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
                    <div className="flex items-center gap-2 mb-2">
                        <Avatar name={request.from} size="sm" />
                        <span className="font-semibold text-navy">{request.from}</span>
                        <ArrowLeftRight size={14} className="text-gray-400" />
                        <Avatar name={request.to ?? ''} size="sm" />
                        <span className="font-semibold text-navy">{request.to}</span>
                    </div>
                ) : (
                    <div className="flex items-center gap-2 mb-2">
                        <Avatar name={request.from} size="sm" />
                        <span className="font-semibold text-navy">{request.from} dropped</span>
                    </div>
                )}
                <div className="flex items-center gap-4 text-sm text-gray-600">
                    <span className="flex items-center gap-1">
                        <Clock size={13} /> {request.date} · {request.shift} · {request.time}
                    </span>
                </div>
            </div>

            {/* Note */}
            {request.note && (
                <div className="flex items-start gap-2 mb-3 px-3 py-2 bg-gray-50 rounded-lg">
                    <MessageSquare size={13} className="text-gray-400 mt-0.5" />
                    <p className="text-sm text-gray-600 italic">"{request.note}"</p>
                </div>
            )}

            {/* Accepted badge */}
            {request.acceptedBy && (
                <div className="flex items-center gap-2 mb-3">
                    <Badge variant="green">
                        <Check size={12} className="mr-1" /> {request.acceptedBy} accepted
                    </Badge>
                    {request.constraintOk && (
                        <span className="flex items-center gap-1 text-xs text-success">
                            <CheckCircle size={13} /> All constraints pass
                        </span>
                    )}
                </div>
            )}

            {/* Notified count for drops */}
            {request.notifiedCount !== undefined && (
                <div className="flex items-center gap-2 mb-3 text-sm text-gray-600">
                    <Users size={14} />
                    <span>
                        {request.notifiedCount} of {request.qualifiedCount} qualified staff notified
                    </span>
                </div>
            )}

            {/* Expiry for non-urgent */}
            {request.expiresIn && !isUrgent && (
                <p className="text-xs text-gray-500 mb-3">Expires: {request.expiresIn}</p>
            )}

            {/* Requested time */}
            <p className="text-xs text-gray-400 mb-4">Requested: {request.timeAgo}</p>

            {/* Actions */}
            <div className="flex items-center justify-end gap-2 pt-3 border-t border-border-gray">
                {request.status === 'awaiting-staff' && (
                    <>
                        <span className="text-xs text-gray-500 mr-auto">Awaiting {request.to}'s acceptance</span>
                        <button className="px-3 py-1.5 text-xs font-semibold border border-danger/30 text-danger rounded-lg hover:bg-danger-50 transition-base">
                            Reject
                        </button>
                    </>
                )}
                {request.status === 'awaiting-manager' && (
                    <>
                        <button className="px-3 py-1.5 text-xs font-semibold border border-danger/30 text-danger rounded-lg hover:bg-danger-50 transition-base">
                            Reject
                        </button>
                        <button className="px-4 py-1.5 text-xs font-bold bg-teal text-white rounded-lg hover:bg-teal-dark transition-base">
                            Approve Swap
                        </button>
                    </>
                )}
                {request.status === 'open-pickup' && (
                    <button className="px-4 py-1.5 text-xs font-semibold border border-teal text-teal rounded-lg hover:bg-teal-50 transition-base">
                        Force-Assign Staff
                    </button>
                )}
                {request.status === 'urgent-no-claims' && (
                    <>
                        <button className="px-3 py-1.5 text-xs font-semibold border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50 transition-base">
                            Reject Drop
                        </button>
                        <button className="px-4 py-1.5 text-xs font-bold bg-danger text-white rounded-lg hover:bg-danger/90 transition-base">
                            Emergency Coverage
                        </button>
                    </>
                )}
            </div>
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
            <p className="text-sm text-gray-500">No pending swap or drop requests right now.</p>
        </div>
    );
}

/* ========== Main Component ========== */

type Tab = 'pending' | 'approved' | 'rejected' | 'expired';

export function SwapApprovalQueue() {
    const [activeTab, setActiveTab] = useState<Tab>('pending');

    const tabs: { key: Tab; label: string; count?: number }[] = [
        { key: 'pending', label: 'Pending', count: mockRequests.length },
        { key: 'approved', label: 'Approved' },
        { key: 'rejected', label: 'Rejected' },
        { key: 'expired', label: 'Expired' },
    ];

    return (
        <AppLayout title="Swap & Drop Requests" role="manager" notificationCount={4}>
            <div className="p-6 max-w-4xl mx-auto">
                {/* Header */}
                <div className="mb-6">
                    <h1 className="text-2xl font-bold text-navy">Swap & Drop Requests</h1>
                </div>

                {/* Tabs */}
                <div className="flex gap-0 border-b border-border-gray mb-6">
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
                {activeTab === 'pending' ? (
                    <div className="space-y-4">
                        {mockRequests.map((r) => (
                            <RequestCard key={r.id} request={r} />
                        ))}
                    </div>
                ) : (
                    <EmptyState />
                )}
            </div>
        </AppLayout>
    );
}
