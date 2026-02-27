import React, { useEffect, useMemo, useState } from "react";
import { ArrowLeftRight, Check, Clock, Loader2, MessageSquare, X } from "lucide-react";
import { format, parseISO } from "date-fns";
import { useSearchParams } from "react-router-dom";

import { AppLayout } from "../../components/NavBar";
import { Avatar } from "../../components/Avatar";
import { Badge } from "../../components/Badge";
import { Modal } from "../../components/Modal";
import { useAuth } from "../../auth/AuthContext";
import { useNotifications, useSwapAction, useSwapRequests } from "../../lib/api/hooks";
import { SwapRequestResponse, SwapStatus } from "../../lib/api/types";
import { NotificationCentre } from "./NotificationCentre";

function formatShiftDate(dateValue: string | null): string {
    if (!dateValue) return "Unknown date";
    try {
        return format(parseISO(dateValue), "EEE, MMM d");
    } catch {
        return dateValue;
    }
}

function statusBadge(status: SwapStatus): { label: string; variant: "gray" | "purple" | "amber" | "green" | "red" } {
    switch (status) {
        case "PENDING_ACCEPTEE":
            return { label: "Awaiting Your Response", variant: "purple" };
        case "PENDING_MANAGER":
            return { label: "Awaiting Manager", variant: "amber" };
        case "APPROVED":
            return { label: "Approved", variant: "green" };
        case "REJECTED":
            return { label: "Rejected", variant: "red" };
        case "CANCELLED":
            return { label: "Cancelled", variant: "gray" };
        case "EXPIRED":
            return { label: "Expired", variant: "gray" };
        default:
            return { label: status, variant: "gray" };
    }
}

function SwapCard({
    request,
    actionable,
    onAccept,
    onReject,
    busy,
    highlighted = false,
}: {
    request: SwapRequestResponse;
    actionable: boolean;
    onAccept: () => void;
    onReject: () => void;
    busy: boolean;
    highlighted?: boolean;
}) {
    const status = statusBadge(request.status);
    const requester = request.requester_name ?? "Staff member";
    const shiftDate = formatShiftDate(request.shift_date);
    const shiftTime = request.shift_time ?? "Time unavailable";
    const shiftLabel = request.shift_label ?? "Shift";

    return (
        <div
            id={`request-${request.id}`}
            className={`bg-white border border-border-gray rounded-xl p-5 shadow-sm ${highlighted ? "ring-2 ring-staff-purple/40" : ""}`}
        >
            <div className="flex items-center gap-2 mb-3 flex-wrap">
                <Badge variant="purple">Swap Request</Badge>
                <Badge variant={status.variant}>{status.label}</Badge>
            </div>

            <div className="flex items-center gap-2 mb-2 flex-wrap">
                <Avatar name={requester} size="sm" />
                <span className="text-sm font-semibold text-navy">{requester}</span>
                <ArrowLeftRight size={14} className="text-gray-400" />
                <span className="text-sm text-gray-500">wants to swap with you</span>
            </div>

            <div className="flex items-center gap-2 text-sm text-gray-600 flex-wrap">
                <Clock size={13} />
                <span>
                    {shiftDate} - {shiftLabel} - {shiftTime}
                </span>
            </div>

            {request.resolution_note && (
                <div className="mt-3 flex items-start gap-2 p-3 bg-gray-50 rounded-lg">
                    <MessageSquare size={14} className="text-gray-400 mt-0.5" />
                    <p className="text-xs text-gray-600">{request.resolution_note}</p>
                </div>
            )}

            <p className="mt-3 text-xs text-gray-400">
                Requested {format(parseISO(request.created_at), "MMM d, h:mm a")}
            </p>

            {actionable && (
                <div className="mt-4 pt-3 border-t border-border-gray flex items-center justify-end gap-2 flex-wrap">
                    {busy && <Loader2 size={16} className="animate-spin text-staff-purple mr-auto" />}
                    <button
                        onClick={onReject}
                        disabled={busy}
                        className="px-3 py-1.5 text-xs font-semibold border border-danger/30 text-danger rounded-lg hover:bg-danger-50 transition-base disabled:opacity-50 flex-1 sm:flex-none"
                    >
                        Reject
                    </button>
                    <button
                        onClick={onAccept}
                        disabled={busy}
                        className="px-4 py-1.5 text-xs font-bold bg-staff-purple text-white rounded-lg hover:bg-staff-purple-light transition-base disabled:opacity-50 flex-1 sm:flex-none"
                    >
                        Accept Swap
                    </button>
                </div>
            )}
        </div>
    );
}

export function SwapInbox() {
    const { user } = useAuth();
    const [searchParams] = useSearchParams();
    const highlightedRequestId = searchParams.get("requestId");
    const { data, isLoading } = useSwapRequests();
    const { data: notificationsData } = useNotifications();
    const acceptMutation = useSwapAction("accept");
    const rejectMutation = useSwapAction("reject");

    const [selected, setSelected] = useState<SwapRequestResponse | null>(null);
    const [action, setAction] = useState<"accept" | "reject" | null>(null);
    const [note, setNote] = useState("");
    const [isNotificationOpen, setIsNotificationOpen] = useState(false);

    const requests = data?.requests ?? [];
    const incoming = useMemo(
        () => requests.filter((r) => r.type === "swap" && r.target_user_id === user?.id),
        [requests, user?.id]
    );
    const actionable = incoming.filter((r) => r.status === "PENDING_ACCEPTEE");
    const history = incoming.filter((r) => r.status !== "PENDING_ACCEPTEE");

    useEffect(() => {
        if (!highlightedRequestId) return;
        const el = document.getElementById(`request-${highlightedRequestId}`);
        if (el) {
            el.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    }, [highlightedRequestId, actionable.length, history.length]);

    const closeModal = () => {
        setSelected(null);
        setAction(null);
        setNote("");
    };

    const submitAction = () => {
        if (!selected || !action) return;
        const payload = note.trim();
        const mutation = action === "accept" ? acceptMutation : rejectMutation;
        mutation.mutate(
            {
                id: selected.id,
                data: payload ? { note: payload } : {},
            },
            { onSuccess: closeModal }
        );
    };

    const busy = acceptMutation.isPending || rejectMutation.isPending;
    const unreadCount = notificationsData?.unread_count || 0;

    return (
        <AppLayout
            title="Swap Inbox"
            role="staff"
            notificationCount={unreadCount}
            onBellClick={() => setIsNotificationOpen(true)}
        >
            <div className="max-w-4xl mx-auto p-4 md:p-6 space-y-8">
                <section>
                    <div className="mb-4 flex items-center justify-between gap-3 flex-wrap">
                        <h1 className="text-xl sm:text-2xl font-bold text-navy">Swap Inbox</h1>
                        {isLoading && <Loader2 size={22} className="animate-spin text-staff-purple" />}
                    </div>

                    {isLoading ? (
                        <div className="py-16 flex justify-center">
                            <Loader2 size={30} className="animate-spin text-staff-purple/50" />
                        </div>
                    ) : actionable.length === 0 ? (
                        <div className="bg-white border border-border-gray rounded-xl p-6 text-center text-gray-500">
                            No swap requests are waiting for your response.
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {actionable.map((request) => (
                                <SwapCard
                                    key={request.id}
                                    request={request}
                                    actionable
                                    busy={busy}
                                    highlighted={highlightedRequestId === request.id}
                                    onAccept={() => {
                                        setSelected(request);
                                        setAction("accept");
                                    }}
                                    onReject={() => {
                                        setSelected(request);
                                        setAction("reject");
                                    }}
                                />
                            ))}
                        </div>
                    )}
                </section>

                <section>
                    <h2 className="text-lg font-bold text-navy mb-4">Recent Activity</h2>
                    {history.length === 0 ? (
                        <div className="bg-white border border-border-gray rounded-xl p-6 text-center text-gray-500">
                            No previous swap activity yet.
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {history.map((request) => (
                                <SwapCard
                                    key={request.id}
                                    request={request}
                                    actionable={false}
                                    busy={false}
                                    highlighted={highlightedRequestId === request.id}
                                    onAccept={() => {}}
                                    onReject={() => {}}
                                />
                            ))}
                        </div>
                    )}
                </section>
            </div>

            <Modal
                open={!!selected && !!action}
                onClose={closeModal}
                title={action === "accept" ? "Accept Swap Request" : "Reject Swap Request"}
                width="max-w-md"
                footer={
                    <div className="w-full flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-end gap-3">
                        <button onClick={closeModal} className="w-full sm:w-auto text-sm text-gray-500 hover:text-navy transition-base">
                            Cancel
                        </button>
                        <button
                            onClick={submitAction}
                            disabled={busy}
                            className={`w-full sm:w-auto px-5 py-2 text-sm font-bold text-white rounded-lg transition-base disabled:opacity-50 ${action === "accept" ? "bg-staff-purple hover:bg-staff-purple-light" : "bg-danger hover:bg-danger/90"
                                }`}
                        >
                            {busy ? (
                                <span className="inline-flex items-center gap-2">
                                    <Loader2 size={14} className="animate-spin" />
                                    Saving
                                </span>
                            ) : action === "accept" ? (
                                <span className="inline-flex items-center gap-1">
                                    <Check size={14} />
                                    Confirm Accept
                                </span>
                            ) : (
                                <span className="inline-flex items-center gap-1">
                                    <X size={14} />
                                    Confirm Reject
                                </span>
                            )}
                        </button>
                    </div>
                }
            >
                <p className="text-sm text-gray-600 mb-3">
                    {action === "accept"
                        ? "Accepting will send this request to a manager for final approval."
                        : "Rejecting will notify the requester that you declined the swap."}
                </p>
                <textarea
                    value={note}
                    onChange={(event) => setNote(event.target.value)}
                    placeholder="Optional note"
                    rows={3}
                    className="w-full px-3 py-2 border border-border-gray rounded-lg text-sm text-navy focus:outline-none focus:ring-2 focus:ring-staff-purple/30 resize-none"
                />
            </Modal>

            <NotificationCentre
                open={isNotificationOpen}
                onClose={() => setIsNotificationOpen(false)}
            />
        </AppLayout>
    );
}
