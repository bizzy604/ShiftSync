import React, { useState } from 'react';
import { Search, Download, ChevronLeft, ChevronRight, Calendar } from 'lucide-react';
import { AppLayout } from '../../components/NavBar';
import { Badge } from '../../components/Badge';
import { SidePanel } from '../../components/SidePanel';
import { Modal } from '../../components/Modal';
import { useAuditLogs } from '../../lib/api/hooks';
import { Loader2 } from 'lucide-react';
import { AuditLogResponse } from '../../lib/api/types';

/* ========== Mock Data ========== */

/* ========== Detail Panel ========== */

function DetailPanel({ entry, open, onClose }: { entry: AuditLogResponse | null; open: boolean; onClose: () => void }) {
    if (!entry) return null;

    return (
        <SidePanel
            open={open}
            onClose={onClose}
            title="Audit Entry Detail"
            subtitle={`${entry.action_type} - ${entry.entity_type}`}
            width="w-[480px]"
            headerColor="bg-admin-slate"
        >
            <div className="p-6 space-y-5">
                <div className="grid grid-cols-2 gap-3">
                    <div>
                        <span className="text-xs text-gray-500 block mb-0.5">Timestamp</span>
                        <span className="text-sm font-medium text-navy font-mono">
                            {new Date(entry.created_at).toLocaleString()}
                        </span>
                    </div>
                    <div>
                        <span className="text-xs text-gray-500 block mb-0.5">Actor</span>
                        <span className="text-sm font-medium text-navy">{entry.actor_name}</span>
                    </div>
                    <div>
                        <span className="text-xs text-gray-500 block mb-0.5">Action</span>
                        <Badge variant="slate">{entry.action_type}</Badge>
                    </div>
                    <div>
                        <span className="text-xs text-gray-500 block mb-0.5">Location</span>
                        <span className="text-sm font-medium text-navy">{entry.location_name || 'System'}</span>
                    </div>
                </div>

                <div>
                    <span className="text-xs text-gray-500 block mb-1">Details</span>
                    <p className="text-sm text-navy bg-gray-50 px-4 py-3 rounded-lg">
                        {entry.details || 'No additional details provided.'}
                    </p>
                </div>

                {/* State Diff */}
                {entry.before_state && entry.after_state && (
                    <div>
                        <span className="text-xs text-gray-500 block mb-2">State Change</span>
                        <div className="grid grid-cols-2 gap-3">
                            <div className="bg-danger-50 rounded-lg p-4 border border-danger/10">
                                <p className="text-[10px] font-bold uppercase text-danger mb-2">Before</p>
                                <pre className="text-[10px] font-mono text-danger whitespace-pre-wrap overflow-x-auto max-h-[200px]">
                                    {JSON.stringify(entry.before_state, null, 2)}
                                </pre>
                            </div>
                            <div className="bg-success-50 rounded-lg p-4 border border-success/10">
                                <p className="text-[10px] font-bold uppercase text-success mb-2">After</p>
                                <pre className="text-[10px] font-mono text-success whitespace-pre-wrap overflow-x-auto max-h-[200px]">
                                    {JSON.stringify(entry.after_state, null, 2)}
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
    const [page, setPage] = useState(1);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedEntry, setSelectedEntry] = useState<AuditLogResponse | null>(null);
    const [showExportModal, setShowExportModal] = useState(false);

    const { data: auditData, isLoading } = useAuditLogs(page);
    const logs = auditData?.logs || [];
    const totalCount = auditData?.total || 0;
    const totalPages = Math.ceil(totalCount / 50);

    const filteredEntries = logs.filter(
        (e) =>
            e.actor_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            e.action_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
            e.entity_type.toLowerCase().includes(searchQuery.toLowerCase())
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
                        Showing {filteredEntries.length} of {totalCount} entries
                    </span>
                </div>

                {isLoading && (
                    <div className="flex flex-col items-center justify-center py-20 text-gray-400">
                        <Loader2 size={32} className="animate-spin mb-4" />
                        <p>Accessing secure audit records...</p>
                    </div>
                )}

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
                                        className={`border-b border-border-gray cursor-pointer transition-base ${i % 2 === 0 ? 'bg-white hover:bg-gray-50' : 'bg-gray-50/50 hover:bg-gray-100'
                                            }`}
                                    >
                                        <td className="px-4 py-3 text-xs font-mono text-gray-600 whitespace-nowrap">
                                            {new Date(entry.created_at).toLocaleString()}
                                        </td>
                                        <td className="px-4 py-3 text-sm font-medium text-navy whitespace-nowrap">{entry.actor_name}</td>
                                        <td className="px-4 py-3">
                                            <span className="text-xs font-semibold text-admin-slate">System</span>
                                        </td>
                                        <td className="px-4 py-3">
                                            <code className="text-[10px] bg-gray-100 px-2 py-0.5 rounded font-mono text-navy font-bold uppercase">{entry.action_type}</code>
                                        </td>
                                        <td className="px-4 py-3 text-xs text-gray-400 font-mono whitespace-nowrap">{entry.entity_type}</td>
                                        <td className="px-4 py-3 text-xs text-navy max-w-xs truncate">{entry.details}</td>
                                        <td className="px-4 py-3">
                                            <Badge variant="gray">{entry.location_name || 'Global'}</Badge>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {/* Footer */}
                    <div className="px-5 py-3 bg-gray-50 border-t border-border-gray flex items-center justify-between">
                        <p className="text-[11px] text-gray-400 italic">
                            Audit logs are immutable and permanent.
                        </p>
                        <div className="flex items-center gap-4">
                            <button
                                onClick={() => setPage(p => Math.max(1, p - 1))}
                                disabled={page === 1}
                                className="flex items-center gap-1 text-sm text-gray-500 hover:text-navy transition-base disabled:opacity-30"
                            >
                                <ChevronLeft size={16} /> Prev
                            </button>
                            <span className="text-sm text-gray-600">Page {page} of {totalPages || 1}</span>
                            <button
                                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                                disabled={page >= totalPages}
                                className="flex items-center gap-1 text-sm text-gray-500 hover:text-navy transition-base disabled:opacity-30"
                            >
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
                            <span className="text-gray-600">Total records:</span>
                            <span className="font-medium text-navy">{totalCount} entries</span>
                        </div>
                        <div className="flex justify-between text-sm">
                            <span className="text-gray-600">Export format:</span>
                            <span className="font-medium text-navy">CSV (UTF-8)</span>
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
