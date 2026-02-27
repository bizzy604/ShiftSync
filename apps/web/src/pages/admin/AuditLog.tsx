import React, { useEffect, useMemo, useState } from 'react';
import { Calendar, ChevronLeft, ChevronRight, Download, Loader2, Search } from 'lucide-react';
import { format, subDays } from 'date-fns';

import { AppLayout } from '../../components/NavBar';
import { Badge } from '../../components/Badge';
import { SidePanel } from '../../components/SidePanel';
import { Modal } from '../../components/Modal';
import { useAuditLogs, useExportAuditLogs, useLocations } from '../../lib/api/hooks';
import { AuditLogResponse } from '../../lib/api/types';

function downloadBlob(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

function DetailPanel({ entry, open, onClose }: { entry: AuditLogResponse | null; open: boolean; onClose: () => void }) {
    if (!entry) return null;

    return (
        <SidePanel
            open={open}
            onClose={onClose}
            title="Audit Entry Detail"
            subtitle={`${entry.action_type} - ${entry.entity_type}`}
            width="sm:w-[520px]"
            headerColor="bg-admin-slate"
        >
            <div className="p-4 sm:p-6 space-y-5">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
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
                        <span className="text-sm font-medium text-navy">{entry.location_name || entry.location_id || 'System'}</span>
                    </div>
                </div>

                <div>
                    <span className="text-xs text-gray-500 block mb-1">Reason</span>
                    <p className="text-sm text-navy bg-gray-50 px-4 py-3 rounded-lg">
                        {entry.reason || entry.details || 'No reason provided.'}
                    </p>
                </div>

                <div>
                    <span className="text-xs text-gray-500 block mb-2">State Change</span>
                    <div className="grid grid-cols-1 gap-3">
                        <div className="bg-danger-50 rounded-lg p-4 border border-danger/10">
                            <p className="text-[10px] font-bold uppercase text-danger mb-2">Before</p>
                            <pre className="text-[10px] font-mono text-danger whitespace-pre-wrap overflow-x-auto max-h-[200px]">
                                {JSON.stringify(entry.before_state, null, 2) || '{}'}
                            </pre>
                        </div>
                        <div className="bg-success-50 rounded-lg p-4 border border-success/10">
                            <p className="text-[10px] font-bold uppercase text-success mb-2">After</p>
                            <pre className="text-[10px] font-mono text-success whitespace-pre-wrap overflow-x-auto max-h-[200px]">
                                {JSON.stringify(entry.after_state, null, 2) || '{}'}
                            </pre>
                        </div>
                    </div>
                </div>
            </div>
        </SidePanel>
    );
}

export function AuditLog() {
    const defaultEnd = format(new Date(), 'yyyy-MM-dd');
    const defaultStart = format(subDays(new Date(), 14), 'yyyy-MM-dd');

    const [page, setPage] = useState(1);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedEntry, setSelectedEntry] = useState<AuditLogResponse | null>(null);
    const [showExportModal, setShowExportModal] = useState(false);

    const [startDate, setStartDate] = useState(defaultStart);
    const [endDate, setEndDate] = useState(defaultEnd);
    const [locationId, setLocationId] = useState('all');
    const [actionFilter, setActionFilter] = useState('all');
    const [actorFilter, setActorFilter] = useState('all');

    const { data: locationsData } = useLocations();
    const exportMutation = useExportAuditLogs();

    const auditQuery = {
        page,
        limit: 50,
        location_id: locationId === 'all' ? undefined : locationId,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
    };

    const { data: auditData, isLoading } = useAuditLogs(auditQuery);
    const logs = auditData?.logs || [];
    const totalCount = auditData?.total || 0;
    const totalPages = Math.max(1, Math.ceil(totalCount / 50));

    useEffect(() => {
        setPage(1);
    }, [startDate, endDate, locationId]);

    const actionOptions = useMemo(() => {
        return Array.from(new Set(logs.map((entry) => entry.action_type))).sort();
    }, [logs]);

    const actorOptions = useMemo(() => {
        return Array.from(new Set(logs.map((entry) => entry.actor_name))).sort();
    }, [logs]);

    const filteredEntries = useMemo(() => {
        const query = searchQuery.trim().toLowerCase();
        return logs.filter((entry) => {
            const matchesSearch =
                query.length === 0 ||
                entry.actor_name.toLowerCase().includes(query) ||
                entry.action_type.toLowerCase().includes(query) ||
                entry.entity_type.toLowerCase().includes(query) ||
                entry.entity_id.toLowerCase().includes(query);
            const matchesAction = actionFilter === 'all' || entry.action_type === actionFilter;
            const matchesActor = actorFilter === 'all' || entry.actor_name === actorFilter;
            return matchesSearch && matchesAction && matchesActor;
        });
    }, [logs, searchQuery, actionFilter, actorFilter]);

    const handleDownload = () => {
        exportMutation.mutate(auditQuery, {
            onSuccess: (blob) => {
                const suffix = `${startDate || 'all'}_${endDate || 'all'}`;
                downloadBlob(blob, `audit_log_${suffix}.csv`);
                setShowExportModal(false);
            },
        });
    };

    return (
        <AppLayout title="Audit Log" role="admin" notificationCount={0}>
            <div className="p-4 md:p-6">
                <div className="flex items-start justify-between mb-6 gap-3 flex-wrap">
                    <div>
                        <p className="text-xs text-gray-500 mb-1">Admin &gt; Audit Log</p>
                        <h1 className="text-xl sm:text-2xl font-bold text-navy">Audit Log</h1>
                        <p className="text-sm text-gray-500 mt-0.5">Immutable record of scheduling and staffing actions.</p>
                    </div>
                    <div className="flex items-center gap-3 flex-wrap w-full sm:w-auto">
                        <div className="w-full sm:w-auto flex items-center justify-center sm:justify-start gap-1.5 px-3 py-2 border border-border-gray rounded-lg text-xs sm:text-sm text-navy bg-white">
                            <Calendar size={14} className="text-gray-400" />
                            <span>{startDate} to {endDate}</span>
                        </div>
                        <button
                            onClick={() => setShowExportModal(true)}
                            className="w-full sm:w-auto justify-center px-4 py-2.5 bg-teal text-white text-sm font-semibold rounded-lg hover:bg-teal-dark transition-base flex items-center gap-2"
                        >
                            <Download size={14} /> Export CSV
                        </button>
                    </div>
                </div>

                <div className="flex items-center gap-3 mb-4 flex-wrap">
                    <div className="relative flex-1 w-full sm:w-auto min-w-0 sm:min-w-[220px] max-w-full sm:max-w-sm">
                        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                        <input
                            type="text"
                            placeholder="Search actor, action, entity..."
                            value={searchQuery}
                            onChange={(event) => setSearchQuery(event.target.value)}
                            className="w-full pl-9 pr-4 py-2.5 rounded-lg border border-border-gray text-sm text-navy placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-admin-slate/30"
                        />
                    </div>

                    <input
                        type="date"
                        value={startDate}
                        onChange={(event) => setStartDate(event.target.value)}
                        className="w-full sm:w-auto px-3 py-2.5 rounded-lg border border-border-gray text-sm text-navy bg-white"
                    />
                    <input
                        type="date"
                        value={endDate}
                        onChange={(event) => setEndDate(event.target.value)}
                        className="w-full sm:w-auto px-3 py-2.5 rounded-lg border border-border-gray text-sm text-navy bg-white"
                    />

                    <select
                        value={actionFilter}
                        onChange={(event) => setActionFilter(event.target.value)}
                        className="w-full sm:w-auto px-3 py-2.5 rounded-lg border border-border-gray text-sm text-navy bg-white"
                    >
                        <option value="all">All Action Types</option>
                        {actionOptions.map((action) => (
                            <option key={action} value={action}>
                                {action}
                            </option>
                        ))}
                    </select>

                    <select
                        value={actorFilter}
                        onChange={(event) => setActorFilter(event.target.value)}
                        className="w-full sm:w-auto px-3 py-2.5 rounded-lg border border-border-gray text-sm text-navy bg-white"
                    >
                        <option value="all">All Actors</option>
                        {actorOptions.map((actor) => (
                            <option key={actor} value={actor}>
                                {actor}
                            </option>
                        ))}
                    </select>

                    <select
                        value={locationId}
                        onChange={(event) => setLocationId(event.target.value)}
                        className="w-full sm:w-auto px-3 py-2.5 rounded-lg border border-border-gray text-sm text-navy bg-white"
                    >
                        <option value="all">All Locations</option>
                        {locationsData?.locations.map((location) => (
                            <option key={location.id} value={location.id}>
                                {location.name}
                            </option>
                        ))}
                    </select>
                </div>

                {isLoading && (
                    <div className="flex flex-col items-center justify-center py-20 text-gray-400">
                        <Loader2 size={32} className="animate-spin mb-4" />
                        <p>Loading audit records...</p>
                    </div>
                )}

                <div className="bg-white rounded-xl border border-border-gray shadow-sm overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full min-w-[980px]">
                            <thead>
                                <tr className="bg-gray-50 border-b border-border-gray">
                                    <th className="px-4 py-3 text-left text-[11px] font-bold text-gray-500 uppercase">Timestamp</th>
                                    <th className="px-4 py-3 text-left text-[11px] font-bold text-gray-500 uppercase">Actor</th>
                                    <th className="px-4 py-3 text-left text-[11px] font-bold text-gray-500 uppercase">Action</th>
                                    <th className="px-4 py-3 text-left text-[11px] font-bold text-gray-500 uppercase">Entity</th>
                                    <th className="px-4 py-3 text-left text-[11px] font-bold text-gray-500 uppercase">Entity ID</th>
                                    <th className="px-4 py-3 text-left text-[11px] font-bold text-gray-500 uppercase">Location</th>
                                    <th className="px-4 py-3 text-left text-[11px] font-bold text-gray-500 uppercase">Reason</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredEntries.map((entry, idx) => (
                                    <tr
                                        key={entry.id}
                                        onClick={() => setSelectedEntry(entry)}
                                        className={`border-b border-border-gray cursor-pointer transition-base ${idx % 2 === 0 ? 'bg-white hover:bg-gray-50' : 'bg-gray-50/50 hover:bg-gray-100'
                                            }`}
                                    >
                                        <td className="px-4 py-3 text-xs font-mono text-gray-600 whitespace-nowrap">
                                            {new Date(entry.created_at).toLocaleString()}
                                        </td>
                                        <td className="px-4 py-3 text-sm font-medium text-navy whitespace-nowrap">{entry.actor_name}</td>
                                        <td className="px-4 py-3">
                                            <code className="text-[10px] bg-gray-100 px-2 py-0.5 rounded font-mono text-navy font-bold uppercase">
                                                {entry.action_type}
                                            </code>
                                        </td>
                                        <td className="px-4 py-3 text-xs text-gray-500">{entry.entity_type}</td>
                                        <td className="px-4 py-3 text-xs font-mono text-gray-500">{entry.entity_id}</td>
                                        <td className="px-4 py-3">
                                            <Badge variant="gray">{entry.location_name || entry.location_id || 'Global'}</Badge>
                                        </td>
                                        <td className="px-4 py-3 text-xs text-navy max-w-xs truncate">{entry.reason || '-'}</td>
                                    </tr>
                                ))}
                                {!isLoading && filteredEntries.length === 0 && (
                                    <tr>
                                        <td colSpan={7} className="px-4 py-10 text-center text-sm text-gray-500">
                                            No audit entries match these filters.
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>

                    <div className="px-4 sm:px-5 py-3 bg-gray-50 border-t border-border-gray flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <p className="text-[11px] text-gray-400 italic">Audit logs are immutable and append-only.</p>
                        <div className="flex items-center gap-4 w-full sm:w-auto justify-between sm:justify-start">
                            <button
                                onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                                disabled={page === 1}
                                className="flex items-center gap-1 text-sm text-gray-500 hover:text-navy transition-base disabled:opacity-30"
                            >
                                <ChevronLeft size={16} /> Prev
                            </button>
                            <span className="text-sm text-gray-600">Page {page} of {totalPages}</span>
                            <button
                                onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
                                disabled={page >= totalPages}
                                className="flex items-center gap-1 text-sm text-gray-500 hover:text-navy transition-base disabled:opacity-30"
                            >
                                Next <ChevronRight size={16} />
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <DetailPanel
                entry={selectedEntry}
                open={selectedEntry !== null}
                onClose={() => setSelectedEntry(null)}
            />

            <Modal
                open={showExportModal}
                onClose={() => setShowExportModal(false)}
                title="Export Audit Log"
                width="max-w-md"
                footer={
                    <div className="flex flex-col-reverse sm:flex-row justify-end gap-3">
                        <button
                            onClick={() => setShowExportModal(false)}
                            className="w-full sm:w-auto px-4 py-2 text-sm text-gray-600 hover:text-navy transition-base"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleDownload}
                            disabled={exportMutation.isPending}
                            className="w-full sm:w-auto justify-center px-5 py-2.5 bg-teal text-white text-sm font-semibold rounded-lg hover:bg-teal-dark transition-base flex items-center gap-2 disabled:opacity-50"
                        >
                            <Download size={14} />
                            {exportMutation.isPending ? 'Preparing...' : 'Download'}
                        </button>
                    </div>
                }
            >
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-navy mb-1.5">Start Date</label>
                        <input
                            type="date"
                            value={startDate}
                            onChange={(event) => setStartDate(event.target.value)}
                            className="w-full px-3 py-2.5 rounded-lg border border-border-gray text-sm text-navy bg-white"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-navy mb-1.5">End Date</label>
                        <input
                            type="date"
                            value={endDate}
                            onChange={(event) => setEndDate(event.target.value)}
                            className="w-full px-3 py-2.5 rounded-lg border border-border-gray text-sm text-navy bg-white"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-navy mb-1.5">Location</label>
                        <select
                            value={locationId}
                            onChange={(event) => setLocationId(event.target.value)}
                            className="w-full px-3 py-2.5 rounded-lg border border-border-gray text-sm text-navy bg-white"
                        >
                            <option value="all">All Locations</option>
                            {locationsData?.locations.map((location) => (
                                <option key={location.id} value={location.id}>
                                    {location.name}
                                </option>
                            ))}
                        </select>
                    </div>
                    <div className="p-4 bg-gray-50 rounded-lg space-y-2">
                        <div className="flex justify-between text-sm">
                            <span className="text-gray-600">Total records (current page):</span>
                            <span className="font-medium text-navy">{filteredEntries.length}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                            <span className="text-gray-600">Export format:</span>
                            <span className="font-medium text-navy">CSV (UTF-8)</span>
                        </div>
                    </div>
                </div>
            </Modal>
        </AppLayout>
    );
}
