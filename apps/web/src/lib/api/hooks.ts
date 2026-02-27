/**
 * @file /apps/web/src/lib/api/hooks.ts
 *
 * @description
 * API-layer module for `hooks` covering communication contracts and data hooks.
 *
 * @dependencies
 * - (No in-repo dependents detected.)
 *
 * @importance
 * This module controls API consistency and cache behavior, which directly impacts UI
 * reliability.
 */

import { useMutation, useQuery, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import axios from "axios";
import {
    acceptSwap,
    addCertification,
    addSkill,
    cancelSwap,
    createSkill,
    approveDrop,
    approveSwap,
    createAssignment,
    createDrop,
    createShift,
    createSwapRequest,
    createUser,
    declineDrop,
    declineSwap,
    deleteAssignment,
    deleteShift,
    deleteSkill,
    deleteUser,
    getAssignments,
    getShiftSuggestions,
    getAuditLogs,
    exportAuditLogs,
    getAvailableDrops,
    getFairnessReport,
    getMyAssignments,
    getLocation,
    getLocations,
    getMe,
    getNotifications,
    getOnDuty,
    getOvertimeDashboard,
    getShifts,
    getSwapRequest,
    getSwapRequests,
    getUser,
    getUserAvailability,
    getUsers,
    markAllNotificationsRead,
    markNotificationRead,
    getNotificationPreferences,
    notifyQualifiedStaff,
    pickupDrop,
    previewAssignment,
    publishWeek,
    rejectSwap,
    removeCertification,
    removeSkill,
    unpublishShift,
    updateShift,
    updateUser,
    updateUserAvailability,
    updateNotificationPreferences,
    getSkills,
} from "./client";
import {
    AssignmentCreateRequest,
    AvailabilityReplaceRequest,
    CertificationAttachRequest,
    DropCreateRequest,
    DropPickupRequest,
    FairnessReportResponse,
    LocationListResponse,
    LocationResponse,
    NotificationListResponse,
    NotificationPreferencesUpdateRequest,
    OnDutyResponse,
    OvertimeDashboardResponse,
    PublishWeekRequest,
    ShiftCreateRequest,
    ShiftUpdateRequest,
    UnpublishShiftRequest,
    SkillAttachRequest,
    SkillCreateRequest,
    SwapActionRequest,
    SwapCreateRequest,
    AuditLogQuery,
    UserCreateRequest,
    UserUpdateRequest,
} from "./types";
import { useToast } from "../../components/ToastProvider";

/**
 * Centralized React Query hooks for all ShiftSync API domains.
 *
 * Keep query keys and invalidation logic here so cache behavior stays consistent
 * across pages and role-based workflows.
 */

// --- Keys ---
export const keys = {
    me: ["auth", "me"] as const,
    locations: ["locations"] as const,
    location: (id: string) => ["locations", id] as const,
    users: (locationId?: string, includeInactive?: boolean) => ["users", locationId, !!includeInactive] as const,
    user: (id: string) => ["users", id] as const,
    availability: (id: string) => ["users", id, "availability"] as const,
    shifts: (locationId: string, weekStart: string) => ["shifts", locationId, weekStart] as const,
    assignments: (shiftId: string) => ["assignments", shiftId] as const,
    assignmentSuggestions: (shiftId: string) => ["assignments", shiftId, "suggestions"] as const,
    myAssignments: ["assignments", "me"] as const,
    assignmentPreview: (shiftId: string, userId: string) => ["assignmentPreview", shiftId, userId] as const,
    swaps: ["swaps"] as const,
    swap: (id: string) => ["swaps", id] as const,
    drops: ["drops"] as const,
    skills: ["skills"] as const,
    onDuty: (locationId?: string) => ["analytics", "onDuty", locationId] as const,
    overtime: (locationId: string, weekStart: string) => ["analytics", "overtime", locationId, weekStart] as const,
    fairness: (locationId: string, startDate: string, endDate: string) => ["analytics", "fairness", locationId, startDate, endDate] as const,
    audit: (query: AuditLogQuery) => ["audit", query] as const,
    notifications: (unreadOnly: boolean) => ["notifications", { unreadOnly }] as const,
    notificationPreferences: ["notifications", "preferences"] as const,
    suggestions: (shiftId: string) => ["shifts", shiftId, "suggestions"] as const,
};

/**
 * Normalize backend and network failures into a user-facing message.
 */
function getErrorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        const detail = error.response?.data?.detail;
        if (typeof detail === "string") return detail;
        if (detail && typeof detail === "object" && typeof detail.message === "string") {
            return detail.message;
        }
        if (typeof error.response?.data?.message === "string") {
            return error.response.data.message;
        }
        if (typeof error.message === "string" && error.message.length > 0) {
            return error.message;
        }
    }
    if (error instanceof Error && error.message) {
        return error.message;
    }
    return "Something went wrong. Please try again.";
}

// --- Locations ---
/**
 * React Query hook for locations.
 */
export function useLocations() {
    return useQuery({
        queryKey: keys.locations,
        queryFn: () => getLocations(),
    });
}

/**
 * React Query hook for location.
 */
export function useLocation(id: string) {
    return useQuery({
        queryKey: keys.location(id),
        queryFn: () => getLocation(id),
        enabled: !!id,
    });
}

// --- Users ---
/**
 * React Query hook for users.
 */
export function useUsers(locationId?: string, includeInactive = false) {
    return useQuery({
        queryKey: keys.users(locationId, includeInactive),
        queryFn: () => getUsers(locationId, includeInactive),
    });
}

/**
 * React Query hook for me.
 */
export function useMe() {
    return useQuery({
        queryKey: keys.me,
        queryFn: getMe,
        staleTime: Infinity,
    });
}

/**
 * React Query hook for user.
 */
export function useUser(id: string) {
    return useQuery({
        queryKey: keys.user(id),
        queryFn: () => getUser(id),
        enabled: !!id,
    });
}

/**
 * React Query hook for update user.
 */
export function useUpdateUser() {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useToast();
    return useMutation({
        mutationFn: ({ id, data }: { id: string; data: UserUpdateRequest }) => updateUser(id, data),
        onSuccess: (_, { id }) => {
            queryClient.invalidateQueries({ queryKey: keys.user(id) });
            queryClient.invalidateQueries({ queryKey: ["users"] });
            showSuccess("User updated");
        },
        onError: (error) => {
            showError("Failed to update user", getErrorMessage(error));
        },
    });
}

/**
 * React Query hook for user availability.
 */
export function useUserAvailability(id: string) {
    return useQuery({
        queryKey: keys.availability(id),
        queryFn: () => getUserAvailability(id),
        enabled: !!id,
    });
}

// --- Skills ---
/**
 * React Query hook for skills.
 */
export function useSkills() {
    return useQuery({
        queryKey: keys.skills,
        queryFn: getSkills,
    });
}

/**
 * React Query hook for create skill.
 */
export function useCreateSkill() {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useToast();
    return useMutation({
        mutationFn: (data: SkillCreateRequest) => createSkill(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: keys.skills });
            showSuccess("Skill created");
        },
        onError: (error) => {
            showError("Failed to create skill", getErrorMessage(error));
        },
    });
}

/**
 * React Query hook for delete skill catalog.
 */
export function useDeleteSkillCatalog() {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useToast();
    return useMutation({
        mutationFn: (skillId: string) => deleteSkill(skillId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: keys.skills });
            queryClient.invalidateQueries({ queryKey: ["users"] });
            showSuccess("Skill deleted");
        },
        onError: (error) => {
            showError("Failed to delete skill", getErrorMessage(error));
        },
    });
}

/**
 * React Query hook for update availability.
 */
export function useUpdateAvailability() {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useToast();
    return useMutation({
        mutationFn: ({ id, data }: { id: string; data: AvailabilityReplaceRequest }) => updateUserAvailability(id, data),
        onSuccess: (_, { id }) => {
            queryClient.invalidateQueries({ queryKey: keys.availability(id) });
            showSuccess("Availability updated");
        },
        onError: (error) => {
            showError("Failed to update availability", getErrorMessage(error));
        },
    });
}

/**
 * React Query hook for create user.
 */
export function useCreateUser() {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useToast();
    return useMutation({
        mutationFn: (data: UserCreateRequest) => createUser(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["users"] });
            showSuccess("User created");
        },
        onError: (error) => {
            showError("Failed to create user", getErrorMessage(error));
        },
    });
}

/**
 * React Query hook for delete user.
 */
export function useDeleteUser() {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useToast();
    return useMutation({
        mutationFn: (id: string) => deleteUser(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["users"] });
            showSuccess("User deactivated");
        },
        onError: (error) => {
            showError("Failed to deactivate user", getErrorMessage(error));
        },
    });
}

/**
 * React Query hook for add skill.
 */
export function useAddSkill() {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useToast();
    return useMutation({
        mutationFn: ({ userId, data }: { userId: string; data: SkillAttachRequest }) => addSkill(userId, data),
        onSuccess: (_, { userId }) => {
            queryClient.invalidateQueries({ queryKey: keys.user(userId) });
            showSuccess("Skill added");
        },
        onError: (error) => {
            showError("Failed to add skill", getErrorMessage(error));
        },
    });
}

/**
 * React Query hook for remove skill.
 */
export function useRemoveSkill() {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useToast();
    return useMutation({
        mutationFn: ({ userId, skillId }: { userId: string; skillId: string }) => removeSkill(userId, skillId),
        onSuccess: (_, { userId }) => {
            queryClient.invalidateQueries({ queryKey: keys.user(userId) });
            showSuccess("Skill removed");
        },
        onError: (error) => {
            showError("Failed to remove skill", getErrorMessage(error));
        },
    });
}

/**
 * React Query hook for add certification.
 */
export function useAddCertification() {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useToast();
    return useMutation({
        mutationFn: ({ userId, data }: { userId: string; data: CertificationAttachRequest }) => addCertification(userId, data),
        onSuccess: (_, { userId }) => {
            queryClient.invalidateQueries({ queryKey: keys.user(userId) });
            showSuccess("Certification added");
        },
        onError: (error) => {
            showError("Failed to add certification", getErrorMessage(error));
        },
    });
}

/**
 * React Query hook for remove certification.
 */
export function useRemoveCertification() {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useToast();
    return useMutation({
        mutationFn: ({ userId, locationId }: { userId: string; locationId: string }) => removeCertification(userId, locationId),
        onSuccess: (_, { userId }) => {
            queryClient.invalidateQueries({ queryKey: keys.user(userId) });
            showSuccess("Certification removed");
        },
        onError: (error) => {
            showError("Failed to remove certification", getErrorMessage(error));
        },
    });
}

// --- Shifts ---
/**
 * React Query hook for shifts.
 */
export function useShifts(locationId: string, weekStart: string) {
    return useQuery({
        queryKey: keys.shifts(locationId, weekStart),
        queryFn: () => getShifts(locationId, weekStart),
        enabled: !!locationId && !!weekStart,
    });
}

/**
 * React Query hook for create shift.
 */
export function useCreateShift() {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useToast();
    return useMutation({
        mutationFn: ({ locationId, data }: { locationId: string; data: ShiftCreateRequest }) => createShift(locationId, data),
        onSuccess: (_, { locationId, data }) => {
            queryClient.invalidateQueries({ queryKey: ["shifts", locationId] });
            showSuccess("Shift created");
        },
        onError: (error) => {
            showError("Failed to create shift", getErrorMessage(error));
        },
    });
}

/**
 * React Query hook for update shift.
 */
export function useUpdateShift() {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useToast();
    return useMutation({
        mutationFn: ({ locationId, shiftId, data }: { locationId: string; shiftId: string; data: ShiftUpdateRequest }) =>
            updateShift(locationId, shiftId, data),
        onSuccess: (_, { locationId }) => {
            queryClient.invalidateQueries({ queryKey: ["shifts", locationId] });
            showSuccess("Shift updated");
        },
        onError: (error) => {
            showError("Failed to update shift", getErrorMessage(error));
        },
    });
}

/**
 * React Query hook for delete shift.
 */
export function useDeleteShift() {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useToast();
    return useMutation({
        mutationFn: ({ locationId, shiftId }: { locationId: string; shiftId: string }) => deleteShift(locationId, shiftId),
        onSuccess: (_, { locationId }) => {
            queryClient.invalidateQueries({ queryKey: ["shifts", locationId] });
            showSuccess("Shift cancelled");
        },
        onError: (error) => {
            showError("Failed to cancel shift", getErrorMessage(error));
        },
    });
}

/**
 * React Query hook for unpublish shift.
 */
export function useUnpublishShift() {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useToast();
    return useMutation({
        mutationFn: ({ locationId, shiftId, data }: { locationId: string; shiftId: string; data: UnpublishShiftRequest }) =>
            unpublishShift(locationId, shiftId, data),
        onSuccess: (_, { locationId }) => {
            queryClient.invalidateQueries({ queryKey: ["shifts", locationId] });
            showSuccess("Shift unpublished");
        },
        onError: (error) => {
            showError("Failed to unpublish shift", getErrorMessage(error));
        },
    });
}

/**
 * React Query hook for publish week.
 */
export function usePublishWeek() {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useToast();
    return useMutation({
        mutationFn: ({ locationId, data }: { locationId: string; data: PublishWeekRequest }) => publishWeek(locationId, data),
        onSuccess: (_, { locationId, data }) => {
            queryClient.invalidateQueries({ queryKey: keys.shifts(locationId, data.week_start as unknown as string) });
            queryClient.invalidateQueries({ queryKey: ["shifts", locationId] });
            showSuccess("Schedule published");
        },
        onError: (error) => {
            showError("Failed to publish schedule", getErrorMessage(error));
        },
    });
}

// --- Assignments ---
/**
 * React Query hook for assignments.
 */
export function useAssignments(shiftId: string) {
    return useQuery({
        queryKey: keys.assignments(shiftId),
        queryFn: () => getAssignments(shiftId),
        enabled: !!shiftId,
    });
}

/**
 * React Query hook for my assignments.
 */
export function useMyAssignments() {
    return useQuery({
        queryKey: keys.myAssignments,
        queryFn: () => getMyAssignments(),
    });
}

/**
 * React Query hook for shift suggestions.
 */
export function useShiftSuggestions(shiftId: string) {
    return useQuery({
        queryKey: keys.suggestions(shiftId),
        queryFn: () => getShiftSuggestions(shiftId),
        enabled: !!shiftId,
    });
}

/**
 * React Query hook for notify qualified staff.
 */
export function useNotifyQualifiedStaff() {
    const { showSuccess, showError } = useToast();
    return useMutation({
        mutationFn: (requestId: string) => notifyQualifiedStaff(requestId),
        onSuccess: (data) => {
            showSuccess("Notifications sent", `Notified ${data.notified} qualified staff member(s).`);
        },
        onError: (error) => {
            showError("Failed to notify staff", getErrorMessage(error));
        },
    });
}

/**
 * React Query hook for assignment preview.
 */
export function useAssignmentPreview(shiftId: string, userId: string) {
    return useQuery({
        queryKey: keys.assignmentPreview(shiftId, userId),
        queryFn: () => previewAssignment(shiftId, userId),
        enabled: !!shiftId && !!userId,
    });
}

/**
 * React Query hook for create assignment.
 */
export function useCreateAssignment() {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useToast();
    return useMutation({
        mutationFn: ({ shiftId, data }: { shiftId: string; data: AssignmentCreateRequest }) => createAssignment(shiftId, data),
        onSuccess: (_, { shiftId }) => {
            queryClient.invalidateQueries({ queryKey: keys.assignments(shiftId) });
            queryClient.invalidateQueries({ queryKey: ["shifts"] });
            showSuccess("Staff assigned");
        },
        onError: (error) => {
            showError("Failed to assign staff", getErrorMessage(error));
        },
    });
}

/**
 * React Query hook for delete assignment.
 */
export function useDeleteAssignment() {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useToast();
    return useMutation({
        mutationFn: ({ shiftId, assignmentId }: { shiftId: string; assignmentId: string }) => deleteAssignment(shiftId, assignmentId),
        onSuccess: (_, { shiftId }) => {
            queryClient.invalidateQueries({ queryKey: keys.assignments(shiftId) });
            queryClient.invalidateQueries({ queryKey: ["shifts"] });
            showSuccess("Assignment removed");
        },
        onError: (error) => {
            showError("Failed to remove assignment", getErrorMessage(error));
        },
    });
}

// --- Swaps & Drops ---
/**
 * React Query hook for swap requests.
 */
export function useSwapRequests() {
    return useQuery({
        queryKey: keys.swaps,
        queryFn: () => getSwapRequests(),
    });
}

/**
 * React Query hook for swap request.
 */
export function useSwapRequest(id: string) {
    return useQuery({
        queryKey: keys.swap(id),
        queryFn: () => getSwapRequest(id),
        enabled: !!id,
    });
}

/**
 * React Query hook for create swap request.
 */
export function useCreateSwapRequest() {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useToast();
    return useMutation({
        mutationFn: (data: SwapCreateRequest) => createSwapRequest(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: keys.swaps });
            queryClient.invalidateQueries({ queryKey: ["shifts"] });
            queryClient.invalidateQueries({ queryKey: ["assignments"] });
            showSuccess("Swap request sent");
        },
        onError: (error) => {
            showError("Failed to create swap request", getErrorMessage(error));
        },
    });
}

/**
 * React Query hook for available drops.
 */
export function useAvailableDrops() {
    return useQuery({
        queryKey: keys.drops,
        queryFn: () => getAvailableDrops(),
    });
}

/**
 * React Query hook for create drop request.
 */
export function useCreateDropRequest() {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useToast();
    return useMutation({
        mutationFn: (data: DropCreateRequest) => createDrop(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: keys.drops });
            queryClient.invalidateQueries({ queryKey: keys.myAssignments });
            queryClient.invalidateQueries({ queryKey: ["shifts"] });
            queryClient.invalidateQueries({ queryKey: ["assignments"] });
            showSuccess("Drop request created");
        },
        onError: (error) => {
            showError("Failed to create drop request", getErrorMessage(error));
        },
    });
}

/**
 * React Query hook for pickup drop.
 */
export function usePickupDrop() {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useToast();
    return useMutation({
        mutationFn: ({ id, data }: { id: string; data: DropPickupRequest }) => pickupDrop(id, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: keys.drops });
            queryClient.invalidateQueries({ queryKey: keys.swaps });
            showSuccess("Drop picked up");
        },
        onError: (error) => {
            showError("Failed to pick up drop", getErrorMessage(error));
        },
    });
}

/**
 * React Query hook for swap action.
 */
export function useSwapAction(action: "accept" | "reject" | "approve" | "decline" | "cancel") {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useToast();
    const successLabel = (() => {
        if (action === "accept") return "Swap accepted";
        if (action === "reject") return "Swap rejected";
        if (action === "approve") return "Request approved";
        if (action === "cancel") return "Request cancelled";
        return "Request declined";
    })();
    return useMutation({
        mutationFn: ({ id, data, isDrop = false }: { id: string; data: SwapActionRequest; isDrop?: boolean }) => {
            if (isDrop) {
                if (action === "approve") return approveDrop(id, data);
                if (action === "decline") return declineDrop(id, data);
                if (action === "cancel") return cancelSwap(id, data);
                throw new Error("Invalid drop action");
            }

            switch (action) {
                case "accept":
                    return acceptSwap(id, data);
                case "reject":
                    return rejectSwap(id, data);
                case "approve":
                    return approveSwap(id, data);
                case "decline":
                    return declineSwap(id, data);
                case "cancel":
                    return cancelSwap(id, data);
                default:
                    throw new Error("Unknown action");
            }
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: keys.swaps });
            queryClient.invalidateQueries({ queryKey: keys.drops });
            queryClient.invalidateQueries({ queryKey: ["shifts"] });
            queryClient.invalidateQueries({ queryKey: ["assignments"] });
            showSuccess(successLabel);
        },
        onError: (error) => {
            showError("Action failed", getErrorMessage(error));
        },
    });
}

// --- Analytics ---
/**
 * React Query hook for overtime dashboard.
 */
export function useOvertimeDashboard(locationId: string, weekStart: string) {
    return useQuery({
        queryKey: keys.overtime(locationId, weekStart),
        queryFn: () => getOvertimeDashboard(locationId, weekStart),
        enabled: !!locationId && !!weekStart,
    });
}

/**
 * React Query hook for fairness report.
 */
export function useFairnessReport(locationId: string, startDate: string, endDate: string) {
    return useQuery({
        queryKey: keys.fairness(locationId, startDate, endDate),
        queryFn: () => getFairnessReport(locationId, startDate, endDate),
        enabled: !!locationId && !!startDate && !!endDate,
    });
}

/**
 * React Query hook for on duty.
 */
export function useOnDuty(locationId?: string) {
    return useQuery({
        queryKey: keys.onDuty(locationId),
        queryFn: () => getOnDuty(locationId),
        refetchInterval: 60_000,
        refetchIntervalInBackground: false,
    });
}

// --- Audit ---
/**
 * React Query hook for audit logs.
 */
export function useAuditLogs(query: AuditLogQuery) {
    return useQuery({
        queryKey: keys.audit(query),
        queryFn: () => getAuditLogs(query),
        placeholderData: keepPreviousData,
    });
}

/**
 * React Query hook for export audit logs.
 */
export function useExportAuditLogs() {
    const { showSuccess, showError } = useToast();
    return useMutation({
        mutationFn: (query: AuditLogQuery) => exportAuditLogs(query),
        onSuccess: () => {
            showSuccess("Audit export ready");
        },
        onError: (error) => {
            showError("Failed to export audit logs", getErrorMessage(error));
        },
    });
}

// --- Notifications ---
/**
 * React Query hook for notifications.
 */
export function useNotifications(unreadOnly = false) {
    return useQuery({
        queryKey: keys.notifications(unreadOnly),
        queryFn: () => getNotifications(unreadOnly),
    });
}

/**
 * React Query hook for mark all notifications read.
 */
export function useMarkAllNotificationsRead() {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useToast();
    return useMutation({
        mutationFn: () => markAllNotificationsRead(),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["notifications"] });
            showSuccess("Notifications marked as read");
        },
        onError: (error) => {
            showError("Failed to mark notifications", getErrorMessage(error));
        },
    });
}

/**
 * React Query hook for mark notification read.
 */
export function useMarkNotificationRead() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (notificationId: string) => markNotificationRead(notificationId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["notifications"] });
        },
    });
}

/**
 * React Query hook for notification preferences.
 */
export function useNotificationPreferences() {
    return useQuery({
        queryKey: keys.notificationPreferences,
        queryFn: getNotificationPreferences,
    });
}

/**
 * React Query hook for update notification preferences.
 */
export function useUpdateNotificationPreferences() {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useToast();
    return useMutation({
        mutationFn: (data: NotificationPreferencesUpdateRequest) => updateNotificationPreferences(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: keys.notificationPreferences });
            queryClient.invalidateQueries({ queryKey: ["users"] });
            showSuccess("Notification preferences updated");
        },
        onError: (error) => {
            showError("Failed to update notification preferences", getErrorMessage(error));
        },
    });
}
