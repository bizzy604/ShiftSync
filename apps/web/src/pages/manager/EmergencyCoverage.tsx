import React, { useState } from 'react';
import { AlertTriangle, Clock, Check, Bell, User, X } from 'lucide-react';
import { SidePanel } from '../../components/SidePanel';
import { Avatar } from '../../components/Avatar';
import { Badge } from '../../components/Badge';

/* ========== Mock Data ========== */

interface QualifiedStaff {
    id: string;
    name: string;
    hours: number;
    notified: boolean;
    notifiedAgo?: string;
    online: boolean;
    claimed: boolean;
    claimedAgo?: string;
}

const mockQualified: QualifiedStaff[] = [
    { id: '1', name: 'Jordan T.', hours: 24, notified: true, notifiedAgo: '2h ago', online: true, claimed: false },
    { id: '2', name: 'Sam K.', hours: 28, notified: true, notifiedAgo: '2h ago', online: false, claimed: false },
    { id: '3', name: 'Alex R.', hours: 16, notified: false, online: false, claimed: false },
];

/* ========== Main Component ========== */

interface EmergencyCoverageProps {
    open: boolean;
    onClose: () => void;
}

export function EmergencyCoverage({ open, onClose }: EmergencyCoverageProps) {
    const [staff, setStaff] = useState(mockQualified);
    const [showApproval, setShowApproval] = useState(false);

    const claimedCount = staff.filter((s) => s.claimed).length;
    const totalQualified = staff.length;

    const handleClaim = (staffId: string) => {
        setStaff((prev) =>
            prev.map((s) =>
                s.id === staffId ? { ...s, claimed: true, claimedAgo: '30 seconds ago' } : s
            )
        );
        setTimeout(() => setShowApproval(true), 500);
    };

    const claimedStaff = staff.find((s) => s.claimed);

    return (
        <SidePanel
            open={open}
            onClose={onClose}
            title="🚨 Emergency Coverage"
            subtitle="Sunday, Aug 17 · Bartender · 7pm – 11pm"
            width="w-[420px]"
            headerColor="bg-danger"
        >
            <div className="p-5 space-y-5">
                {/* Dropped by */}
                <div className="flex items-center gap-2 text-sm text-gray-600">
                    <User size={14} />
                    <span>Dropped by: <strong className="text-navy">Priya N.</strong> (2 hours ago)</span>
                </div>

                {/* Shift Status */}
                <div className="bg-gray-50 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-3">
                        <h4 className="text-sm font-bold text-navy">Shift Status</h4>
                        <Badge variant="red">No Takers Yet</Badge>
                    </div>
                    <div className="flex items-center gap-2 mb-2">
                        <Clock size={14} className="text-danger" />
                        <span className="text-sm font-bold text-danger">Closes in 47 minutes</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2 mb-1">
                        <div className="h-2 rounded-full bg-danger" style={{ width: `${(claimedCount / totalQualified) * 100}%` }} />
                    </div>
                    <p className="text-xs text-gray-500">
                        {claimedCount} of {totalQualified} qualified staff have claimed this shift
                    </p>
                </div>

                {/* Qualified Staff */}
                <div>
                    <h4 className="text-sm font-bold text-navy mb-3">Qualified & Available Staff</h4>
                    <p className="text-xs text-gray-500 mb-3">Staff who meet all constraints for this shift</p>

                    <div className="space-y-2">
                        {staff.map((s) => (
                            <div
                                key={s.id}
                                className={`p-3.5 rounded-xl border transition-base ${s.claimed ? 'bg-success-50 border-success/30' : 'bg-white border-border-gray hover:border-gray-400'
                                    }`}
                            >
                                <div className="flex items-center gap-3">
                                    <Avatar name={s.name} size="md" online={s.online} />
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-semibold text-navy">{s.name}</p>
                                        <p className="text-xs text-gray-500">{s.hours}h this week</p>
                                    </div>
                                    <div className="flex-shrink-0">
                                        {s.claimed ? (
                                            <Badge variant="green">
                                                <Check size={12} className="mr-1" /> Claimed!
                                            </Badge>
                                        ) : s.notified ? (
                                            <Badge variant="green">Notified</Badge>
                                        ) : (
                                            <Badge variant="gray">Not yet notified</Badge>
                                        )}
                                    </div>
                                </div>
                                {s.notified && !s.claimed && (
                                    <div className="mt-2 flex items-center justify-between">
                                        <p className="text-[11px] text-gray-400">Notified {s.notifiedAgo}</p>
                                        <button
                                            onClick={() => handleClaim(s.id)}
                                            className="text-[11px] text-teal font-medium hover:underline"
                                        >
                                            Simulate Claim
                                        </button>
                                    </div>
                                )}
                                {s.claimed && (
                                    <p className="mt-2 text-[11px] text-success flex items-center gap-1">
                                        <Check size={11} /> Claimed {s.claimedAgo}
                                    </p>
                                )}
                            </div>
                        ))}
                    </div>
                </div>

                {/* Pending Approval Section */}
                {showApproval && claimedStaff && (
                    <div className="bg-teal-50 rounded-xl p-4 border border-teal/20 animate-fade-in">
                        <h4 className="text-sm font-bold text-navy mb-3">Pending Approval</h4>
                        <div className="flex items-center gap-3 mb-4">
                            <Avatar name={claimedStaff.name} size="md" />
                            <div>
                                <p className="text-sm font-semibold text-navy">{claimedStaff.name}</p>
                                <p className="text-xs text-gray-500">Sun Aug 17 · Bartender · 7pm–11pm</p>
                            </div>
                        </div>
                        <div className="flex gap-2">
                            <button className="flex-1 py-2 text-sm font-bold bg-teal text-white rounded-lg hover:bg-teal-dark transition-base">
                                Approve Assignment
                            </button>
                            <button className="px-4 py-2 text-sm font-semibold border border-danger/30 text-danger rounded-lg hover:bg-danger-50 transition-base">
                                Reject
                            </button>
                        </div>
                    </div>
                )}

                {/* Actions */}
                <div className="space-y-2 pt-2">
                    <button className="w-full py-2.5 bg-teal text-white text-sm font-semibold rounded-lg hover:bg-teal-dark transition-base flex items-center justify-center gap-2">
                        <Bell size={16} /> Notify All Remaining
                    </button>
                    <button className="w-full py-2.5 border border-teal text-teal text-sm font-semibold rounded-lg hover:bg-teal-50 transition-base">
                        Manually Assign
                    </button>
                    <button className="w-full py-2 text-xs text-gray-500 hover:text-navy transition-base">
                        Close Without Coverage
                    </button>
                </div>
            </div>
        </SidePanel>
    );
}
