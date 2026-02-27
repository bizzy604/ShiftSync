import React, { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Loader2, Search } from "lucide-react";
import { useSearchParams } from "react-router-dom";

import { AppLayout } from "../../components/NavBar";
import { Badge } from "../../components/Badge";
import { NotificationCentre } from "../staff/NotificationCentre";
import { useAuditLogs, useLocations, useNotifications } from "../../lib/api/hooks";
import { AuditLogResponse } from "../../lib/api/types";

function referencesShift(entry: AuditLogResponse, shiftId: string): boolean {
    if (!shiftId) return true;
    if (entry.entity_id === shiftId) return true;
    const beforeShift = entry.before_state?.shift_id;
    const afterShift = entry.after_state?.shift_id;
    return beforeShift === shiftId || afterShift === shiftId;
}

export function ShiftHistory() {
    const [searchParams, setSearchParams] = useSearchParams();
    const [page, setPage] = useState(1);
    const [entityType, setEntityType] = useState(searchParams.get("entity_type") || "all");
    const [search, setSearch] = useState("");
    const [isNotificationOpen, setIsNotificationOpen] = useState(false);

    const shiftId = searchParams.get("shift_id") || "";
    const locationId = searchParams.get("location_id") || "all";

    const { data: locationsData } = useLocations();
    const { data: notificationsData } = useNotifications();
    const unreadCount = notificationsData?.unread_count || 0;

    const query = {
        page,
        limit: 50,
        location_id: locationId === "all" ? undefined : locationId,
        entity_type: entityType === "all" ? undefined : entityType,
    };

    const { data, isLoading } = useAuditLogs(query);
    const logs = data?.logs || [];
    const total = data?.total || 0;
    const totalPages = Math.max(1, Math.ceil(total / 50));

    const filteredLogs = useMemo(() => {
        const q = search.trim().toLowerCase();
        return logs.filter((entry) => {
            if (!referencesShift(entry, shiftId)) return false;
            if (!q) return true;
            return (
                entry.actor_name.toLowerCase().includes(q) ||
                entry.action_type.toLowerCase().includes(q) ||
                entry.entity_type.toLowerCase().includes(q) ||
                entry.entity_id.toLowerCase().includes(q) ||
                (entry.reason || "").toLowerCase().includes(q)
            );
        });
    }, [logs, search, shiftId]);

    return (
        <AppLayout
            title="Shift History"
            role="manager"
            notificationCount={unreadCount}
            onBellClick={() => setIsNotificationOpen(true)}
        >
            <div className="p-4 md:p-6">
                <div className="mb-5">
                    <p className="text-xs text-gray-500 mb-1">Manager {"->"} Shift History</p>
                    <h1 className="text-xl sm:text-2xl font-bold text-navy">Shift Change History</h1>
                    {shiftId && (
                        <p className="text-xs text-gray-500 mt-1">
                            Focused Shift: <span className="font-mono text-navy">{shiftId}</span>
                        </p>
                    )}
                </div>

                <div className="flex items-center gap-3 mb-4 flex-wrap">
                    <div className="relative flex-1 w-full sm:w-auto min-w-0 sm:min-w-[260px] max-w-full sm:max-w-md">
                        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                        <input
                            type="text"
                            value={search}
                            onChange={(event) => setSearch(event.target.value)}
                            placeholder="Search actor/action/entity/reason..."
                            className="w-full pl-9 pr-4 py-2.5 rounded-lg border border-border-gray text-sm text-navy placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-teal/30"
                        />
                    </div>

                    <select
                        value={locationId}
                        onChange={(event) => {
                            const params = new URLSearchParams(searchParams);
                            if (event.target.value === "all") params.delete("location_id");
                            else params.set("location_id", event.target.value);
                            setSearchParams(params, { replace: true });
                            setPage(1);
                        }}
                        className="w-full sm:w-auto px-3 py-2.5 rounded-lg border border-border-gray text-sm text-navy bg-white"
                    >
                        <option value="all">All Locations</option>
                        {(locationsData?.locations || []).map((location) => (
                            <option key={location.id} value={location.id}>
                                {location.name}
                            </option>
                        ))}
                    </select>

                    <select
                        value={entityType}
                        onChange={(event) => {
                            const next = event.target.value;
                            setEntityType(next);
                            const params = new URLSearchParams(searchParams);
                            if (next === "all") params.delete("entity_type");
                            else params.set("entity_type", next);
                            setSearchParams(params, { replace: true });
                            setPage(1);
                        }}
                        className="w-full sm:w-auto px-3 py-2.5 rounded-lg border border-border-gray text-sm text-navy bg-white"
                    >
                        <option value="all">All Entities</option>
                        <option value="shift">Shift</option>
                        <option value="assignment">Assignment</option>
                        <option value="swap_request">Swap Request</option>
                    </select>
                </div>

                <div className="bg-white rounded-xl border border-border-gray shadow-sm overflow-hidden">
                    {isLoading ? (
                        <div className="py-16 flex flex-col items-center text-gray-400">
                            <Loader2 size={28} className="animate-spin mb-3" />
                            <p>Loading shift history...</p>
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full min-w-[880px]">
                                <thead>
                                    <tr className="bg-gray-50 border-b border-border-gray">
                                        <th className="px-4 py-3 text-left text-xs font-bold text-gray-500 uppercase">Timestamp</th>
                                        <th className="px-4 py-3 text-left text-xs font-bold text-gray-500 uppercase">Actor</th>
                                        <th className="px-4 py-3 text-left text-xs font-bold text-gray-500 uppercase">Action</th>
                                        <th className="px-4 py-3 text-left text-xs font-bold text-gray-500 uppercase">Entity</th>
                                        <th className="px-4 py-3 text-left text-xs font-bold text-gray-500 uppercase">Reason</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredLogs.map((entry) => (
                                        <tr key={entry.id} className="border-b border-border-gray hover:bg-gray-50">
                                            <td className="px-4 py-3 text-xs text-gray-600 font-mono">
                                                {new Date(entry.created_at).toLocaleString()}
                                            </td>
                                            <td className="px-4 py-3 text-sm text-navy font-medium">{entry.actor_name}</td>
                                            <td className="px-4 py-3">
                                                <Badge variant="slate">{entry.action_type}</Badge>
                                            </td>
                                            <td className="px-4 py-3 text-xs text-gray-600">
                                                {entry.entity_type} / <span className="font-mono">{entry.entity_id}</span>
                                            </td>
                                            <td className="px-4 py-3 text-xs text-gray-600 max-w-[360px] truncate">
                                                {entry.reason || "-"}
                                            </td>
                                        </tr>
                                    ))}
                                    {filteredLogs.length === 0 && (
                                        <tr>
                                            <td colSpan={5} className="px-4 py-12 text-center text-sm text-gray-500">
                                                No audit entries found for this filter set.
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    )}

                    <div className="px-4 py-3 bg-gray-50 border-t border-border-gray flex items-center justify-between">
                        <button
                            onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                            disabled={page === 1}
                            className="flex items-center gap-1 text-sm text-gray-500 hover:text-navy disabled:opacity-30"
                        >
                            <ChevronLeft size={16} /> Prev
                        </button>
                        <span className="text-sm text-gray-600">Page {page} of {totalPages}</span>
                        <button
                            onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
                            disabled={page >= totalPages}
                            className="flex items-center gap-1 text-sm text-gray-500 hover:text-navy disabled:opacity-30"
                        >
                            Next <ChevronRight size={16} />
                        </button>
                    </div>
                </div>
            </div>

            <NotificationCentre open={isNotificationOpen} onClose={() => setIsNotificationOpen(false)} />
        </AppLayout>
    );
}

