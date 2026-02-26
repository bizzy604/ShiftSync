import React, { useState } from 'react';
import { Search, Download, ChevronLeft, ChevronRight, Calendar } from 'lucide-react';
import { AppLayout } from '../../components/NavBar';
import { Badge } from '../../components/Badge';
import { SidePanel } from '../../components/SidePanel';
import { Modal } from '../../components/Modal';

/* ========== Mock Data ========== */

interface AuditEntry {
    id: string;
    timestamp: string;
    actor: string;
    role: 'Manager' | 'Staff' | 'Admin';
    action: string;
    entity: string;
    details: string;
    location: string;
    isOverride?: boolean;
    beforeState?: Record<string, string>;
    afterState?: Record<string, string>;
}

const mockEntries: AuditEntry[] = [
    {
        id: '1',
        timestamp: 'Aug 17 2025 11:42:03 UTC',
        actor: 'Jordan K.',
        role: 'Manager',
        action: 'shift.assign',
        entity: 'Assignment #A-991',
        details: 'Assigned Carlos M. to Fri Aug 15 · Bartender 6pm–11pm',
        location: 'Ocean Ave',
        beforeState: { assignee: 'Unassigned', status: 'Open' },
        afterState: { assignee: 'Carlos M.', status: 'Assigned' },
    },
    {
        id: '2',
        timestamp: 'Aug 17 2025 11:40:17 UTC',
        actor: 'Carlos M.',
        role: 'Staff',
        action: 'swap.request',
        entity: 'SwapRequest #SR-142',
        details: 'Carlos requested swap with Maria L. for Wed Aug 13',
        location: 'Ocean Ave',
    },
    {
        id: '3',
        timestamp: 'Aug 17 2025 10:15:00 UTC',
        actor: 'Jordan K.',
        role: 'Manager',
        action: 'schedule.publish',
        entity: 'Schedule #S-88',
        details: 'Published week Aug 11–17 for Ocean Ave',
        location: 'Ocean Ave',
    },
    {
        id: '4',
        timestamp: 'Aug 16 2025 18:30:44 UTC',
        actor: 'Admin',
        role: 'Admin',
        action: 'cert.revoke',
        entity: 'UserCert #UC-55',
        details: "Revoked Alex R.'s Beach Blvd certification",
        location: 'System',
    },
    {
        id: '5',
        timestamp: 'Aug 16 2025 14:22:11 UTC',
        actor: 'Sam R.',
        role: 'Manager',
        action: 'shift.assign.override',
        entity: 'Assignment #A-987',
        details: 'Override: Jordan T. assigned to 7th consecutive day. Reason: Emergency staffing.',
        location: 'Beach Blvd',
        isOverride: true,
        beforeState: { assignee: 'Unassigned', consecutiveDays: '6', overrideApplied: 'false' },
        afterState: { assignee: 'Jordan T.', consecutiveDays: '7', overrideApplied: 'true' },
    },
    {
        id: '6',
        timestamp: 'Aug 15 2025 09:10:05 UTC',
        actor: 'Admin',
        role: 'Admin',
        action: 'user.create',
        entity: 'User #U-33',
        details: 'Created staff account for Priya N.',
        location: 'System',
    },
    {
        id: '7',
        timestamp: 'Aug 14 2025 22:01:33 UTC',
        actor: 'Jordan K.',
        role: 'Manager',
        action: 'swap.approve',
        entity: 'SwapRequest #SR-138',
        details: 'Approved swap: Jordan T. ↔ Sam K. for Sat Aug 16',
        location: 'Ocean Ave',
    },
    {
        id: '8',
        timestamp: 'Aug 14 2025 16:44:20 UTC',
        actor: 'Maria L.',
        role: 'Staff',
        action: 'swap.accept',
        entity: 'SwapRequest #SR-142',
        details: 'Maria L. accepted swap request from Carlos M.',
        location: 'Ocean Ave',
    },
];

/* ========== Detail Panel ========== */

function DetailPanel({ entry, open, onClose }: { entry: AuditEntry | null; open: boolean; onClose: () => void }) {
    if (!entry) return null;

    return (
        <SidePanel
            open={open}
            onClose={onClose}
            title="Audit Entry Detail"
            subtitle={entry.entity}
            width="w-[480px]"
            headerColor="bg-admin-slate"
        >
            <div className="p-6 space-y-5">
                <div className="grid grid-cols-2 gap-3">
                    <div>
                        <span className="text-xs text-gray-500 block mb-0.5">Timestamp</span>
                        <span className="text-sm font-medium text-navy font-mono">{entry.timestamp}</span>
                    </div>
                    <div>
                        <span className="text-xs text-gray-500 block mb-0.5">Actor</span>
                        <span className="text-sm font-medium text-navy">{entry.actor} ({entry.role})</span>
                    </div>
                    <div>
                        <span className="text-xs text-gray-500 block mb-0.5">Action</span>
                        <Badge variant={entry.isOverride ? 'amber' : 'slate'}>{entry.action}</Badge>
                    </div>
                    <div>
                        <span className="text-xs text-gray-500 block mb-0.5">Location</span>
                        <span className="text-sm font-medium text-navy">{entry.location}</span>
                    </div>
                </div>

                <div>
                    <span className="text-xs text-gray-500 block mb-1">Details</span>
                    <p className="text-sm text-navy bg-gray-50 px-4 py-3 rounded-lg">{entry.details}</p>
                </div>

                {/* Before/After Diff */}
                {entry.beforeState && entry.afterState && (
                    <div>
                        <span className="text-xs text-gray-500 block mb-2">State Change</span>
                        <div className="grid grid-cols-2 gap-3">
                            <div className="bg-danger-50 rounded-lg p-4 border border-danger/10">
                                <p className="text-[10px] font-bold uppercase text-danger mb-2">Before</p>
                                <pre className="text-xs font-mono text-danger whitespace-pre-wrap">
                                    {JSON.stringify(entry.beforeState, null, 2)}
                                </pre>
                            </div>
                            <div className="bg-success-50 rounded-lg p-4 border border-success/10">
                                <p className="text-[10px] font-bold uppercase text-success mb-2">After</p>
                                <pre className="text-xs font-mono text-success whitespace-pre-wrap">
                                    {JSON.stringify(entry.afterState, null, 2)}
                                </pre>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </SidePanel>
    );
}

/* ========== Main Component ========== */

export function AuditLog() {
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedEntry, setSelectedEntry] = useState<AuditEntry | null>(null);
    const [showExportModal, setShowExportModal] = useState(false);

    const filteredEntries = mockEntries.filter(
        (e) =>
            e.actor.toLowerCase().includes(searchQuery.toLowerCase()) ||
            e.action.toLowerCase().includes(searchQuery.toLowerCase()) ||
            e.entity.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const roleColor = (role: string) => {
        switch (role) {
            case 'Manager': return 'text-teal';
            case 'Staff': return 'text-staff-purple';
            case 'Admin': return 'text-admin-slate';
            default: return 'text-gray-600';
        }
    };

    return (
        <AppLayout title="Audit Log" role="admin" notificationCount={0}>
            <div className="p-6">
                {/* Header */}
                <div className="flex items-start justify-between mb-6">
                    <div>
                        <p className="text-xs text-gray-500 mb-1">Admin › Audit Log</p>
                        <h1 className="text-2xl font-bold text-navy">Audit Log</h1>
                        <p className="text-sm text-gray-500 mt-0.5">Complete, immutable record of all actions taken in ShiftSync.</p>
                    </div>
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-1.5 px-3 py-2 border border-border-gray rounded-lg text-sm text-navy bg-white">
                            <Calendar size={14} className="text-gray-400" />
                            <span>Aug 1, 2025 – Aug 17, 2025</span>
                        </div>
                        <button
                            onClick={() => setShowExportModal(true)}
                            className="px-4 py-2.5 bg-teal text-white text-sm font-semibold rounded-lg hover:bg-teal-dark transition-base flex items-center gap-2"
                        >
                            <Download size={14} /> Export CSV
                        </button>
                    </div>
                </div>

                {/* Filters */}
                <div className="flex items-center gap-3 mb-4 flex-wrap">
                    <div className="relative flex-1 max-w-sm">
                        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                        <input
                            type="text"
                            placeholder="Search by actor, action, or entity ID…"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pl-9 pr-4 py-2.5 rounded-lg border border-border-gray text-sm text-navy placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-admin-slate/30"
                        />
                    </div>
                    <select className="px-3 py-2.5 rounded-lg border border-border-gray text-sm text-navy bg-white">
                        <option>All Action Types</option>
                    </select>
                    <select className="px-3 py-2.5 rounded-lg border border-border-gray text-sm text-navy bg-white">
                        <option>All Actors</option>
                    </select>
                    <select className="px-3 py-2.5 rounded-lg border border-border-gray text-sm text-navy bg-white">
                        <option>All Locations</option>
                    </select>
                    <span className="text-xs text-gray-500">
                        Showing {filteredEntries.length} of 1,247 entries
                    </span>
                </div>

                {/* Table */}
                <div className="bg-white rounded-xl border border-border-gray shadow-sm overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="bg-gray-50 border-b border-border-gray">
                                    <th className="px-4 py-3 text-left text-[11px] font-bold text-gray-500 uppercase">Timestamp</th>
                                    <th className="px-4 py-3 text-left text-[11px] font-bold text-gray-500 uppercase">Actor</th>
                                    <th className="px-4 py-3 text-left text-[11px] font-bold text-gray-500 uppercase">Role</th>
                                    <th className="px-4 py-3 text-left text-[11px] font-bold text-gray-500 uppercase">Action</th>
                                    <th className="px-4 py-3 text-left text-[11px] font-bold text-gray-500 uppercase">Entity</th>
                                    <th className="px-4 py-3 text-left text-[11px] font-bold text-gray-500 uppercase">Details</th>
                                    <th className="px-4 py-3 text-left text-[11px] font-bold text-gray-500 uppercase">Location</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredEntries.map((entry, i) => (
                                    <tr
                                        key={entry.id}
                                        onClick={() => setSelectedEntry(entry)}
                                        className={`border-b border-border-gray cursor-pointer transition-base ${entry.isOverride
                                                ? 'bg-amber-warn-50 border-l-4 border-l-amber-warn hover:bg-amber-warn-50/80'
                                                : i % 2 === 0
                                                    ? 'bg-white hover:bg-gray-50'
                                                    : 'bg-gray-50/50 hover:bg-gray-100'
                                            }`}
                                    >
                                        <td className="px-4 py-3 text-xs font-mono text-gray-600 whitespace-nowrap">{entry.timestamp}</td>
                                        <td className="px-4 py-3 text-sm font-medium text-navy whitespace-nowrap">{entry.actor}</td>
                                        <td className="px-4 py-3">
                                            <span className={`text-xs font-semibold ${roleColor(entry.role)}`}>{entry.role}</span>
                                        </td>
                                        <td className="px-4 py-3">
                                            <code className="text-xs bg-gray-100 px-2 py-0.5 rounded font-mono text-navy">{entry.action}</code>
                                        </td>
                                        <td className="px-4 py-3 text-xs text-gray-600 font-mono whitespace-nowrap">{entry.entity}</td>
                                        <td className="px-4 py-3 text-xs text-gray-600 max-w-xs truncate">{entry.details}</td>
                                        <td className="px-4 py-3">
                                            <Badge variant="gray">{entry.location}</Badge>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {/* Footer */}
                    <div className="px-5 py-3 bg-gray-50 border-t border-border-gray flex items-center justify-between">
                        <p className="text-[11px] text-gray-400 italic">
                            Exported logs are immutable. No entries can be edited or deleted.
                        </p>
                        <div className="flex items-center gap-4">
                            <button className="flex items-center gap-1 text-sm text-gray-500 hover:text-navy transition-base">
                                <ChevronLeft size={16} /> Prev
                            </button>
                            <span className="text-sm text-gray-600">Page 1 of 25</span>
                            <button className="flex items-center gap-1 text-sm text-gray-500 hover:text-navy transition-base">
                                Next <ChevronRight size={16} />
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Detail Panel */}
            <DetailPanel
                entry={selectedEntry}
                open={selectedEntry !== null}
                onClose={() => setSelectedEntry(null)}
            />

            {/* Export Modal */}
            <Modal
                open={showExportModal}
                onClose={() => setShowExportModal(false)}
                title="Export Audit Log"
                width="max-w-md"
                footer={
                    <div className="flex justify-end gap-3">
                        <button
                            onClick={() => setShowExportModal(false)}
                            className="px-4 py-2 text-sm text-gray-600 hover:text-navy transition-base"
                        >
                            Cancel
                        </button>
                        <button className="px-5 py-2.5 bg-teal text-white text-sm font-semibold rounded-lg hover:bg-teal-dark transition-base flex items-center gap-2">
                            <Download size={14} /> Download
                        </button>
                    </div>
                }
            >
                <div className="space-y-4">
                    <div className="p-4 bg-gray-50 rounded-lg space-y-2">
                        <div className="flex justify-between text-sm">
                            <span className="text-gray-600">Date range:</span>
                            <span className="font-medium text-navy">Aug 1 – Aug 17, 2025</span>
                        </div>
                        <div className="flex justify-between text-sm">
                            <span className="text-gray-600">Records:</span>
                            <span className="font-medium text-navy">1,247 entries</span>
                        </div>
                        <div className="flex justify-between text-sm">
                            <span className="text-gray-600">Columns:</span>
                            <span className="font-medium text-navy">Timestamp, Actor, Role, Action, Entity, Details, Location</span>
                        </div>
                    </div>
                    <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                        <p className="text-xs text-blue-700">
                            Exports are watermarked with the requesting admin's name and timestamp.
                        </p>
                    </div>
                </div>
            </Modal>
        </AppLayout>
    );
}
