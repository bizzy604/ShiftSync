import { useMutation, useQuery, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import axios from "axios";
import {
    acceptSwap,
    addCertification,
    addSkill,
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
    deleteUser,
    getAssignments,
    getShiftSuggestions,
    getAuditLogs,
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
    notifyQualifiedStaff,
    pickupDrop,
    previewAssignment,
    publishWeek,
    rejectSwap,
    removeCertification,
    removeSkill,
    updateShift,
    updateUser,
    updateUserAvailability,
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
    OnDutyResponse,
    OvertimeDashboardResponse,
    PublishWeekRequest,
    ShiftCreateRequest,
    ShiftUpdateRequest,
    SkillAttachRequest,
    SwapActionRequest,
    SwapCreateRequest,
    UserCreateRequest,
    UserUpdateRequest,
} from "./types";
import { useToast } from "../../components/ToastProvider";

// --- Keys ---
export const keys = {
    me: ["auth", "me"] as const,
    locations: ["locations"] as const,
    location: (id: string) => ["locations", id] as const,
    users: (locationId?: string) => ["users", locationId] as const,
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
    audit: (page: number) => ["audit", page] as const,
    notifications: (unreadOnly: boolean) => ["notifications", { unreadOnly }] as const,
    suggestions: (shiftId: string) => ["shifts", shiftId, "suggestions"] as const,
};

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
export function useLocations() {
    return useQuery({
        queryKey: keys.locations,
        queryFn: () => getLocations(),
    });
}

export function useLocation(id: string) {
    return useQuery({
        queryKey: keys.location(id),
        queryFn: () => getLocation(id),
        enabled: !!id,
    });
}

// --- Users ---
export function useUsers(locationId?: string) {
    return useQuery({
        queryKey: keys.users(locationId),
        queryFn: () => getUsers(locationId),
    });
}

export function useMe() {
    return useQuery({
        queryKey: keys.me,
        queryFn: getMe,
        staleTime: Infinity,
    });
}

export function useUser(id: string) {
    return useQuery({
        queryKey: keys.user(id),
        queryFn: () => getUser(id),
        enabled: !!id,
    });
}

export function useUpdateUser() {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useToast();
    return useMutation({
        mutationFn: ({ id, data }: { id: string; data: UserUpdateRequest }) => updateUser(id, data),
        onSuccess: (_, { id }) => {
            queryClient.invalidateQueries({ queryKey: keys.user(id) });
            queryClient.invalidateQueries({ queryKey: keys.users() });
            showSuccess("User updated");
        },
        onError: (error) => {
            showError("Failed to update user", getErrorMessage(error));
        },
    });
}

export function useUserAvailability(id: string) {
    return useQuery({
        queryKey: keys.availability(id),
        queryFn: () => getUserAvailability(id),
        enabled: !!id,
    });
}

// --- Skills ---
export function useSkills() {
    return useQuery({
        queryKey: keys.skills,
        queryFn: getSkills,
    });
}

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

export function useCreateUser() {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useToast();
    return useMutation({
        mutationFn: (data: UserCreateRequest) => createUser(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: keys.users() });
            showSuccess("User created");
        },
        onError: (error) => {
            showError("Failed to create user", getErrorMessage(error));
        },
    });
}

export function useDeleteUser() {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useToast();
    return useMutation({
        mutationFn: (id: string) => deleteUser(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: keys.users() });
            showSuccess("User deactivated");
        },
        onError: (error) => {
            showError("Failed to deactivate user", getErrorMessage(error));
        },
    });
}

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
export function useShifts(locationId: string, weekStart: string) {
    return useQuery({
        queryKey: keys.shifts(locationId, weekStart),
        queryFn: () => getShifts(locationId, weekStart),
        enabled: !!locationId && !!weekStart,
    });
}

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
export function useAssignments(shiftId: string) {
    return useQuery({
        queryKey: keys.assignments(shiftId),
        queryFn: () => getAssignments(shiftId),
        enabled: !!shiftId,
    });
}

export function useMyAssignments() {
    return useQuery({
        queryKey: keys.myAssignments,
        queryFn: () => getMyAssignments(),
    });
}

export function useShiftSuggestions(shiftId: string) {
    return useQuery({
        queryKey: keys.suggestions(shiftId),
        queryFn: () => getShiftSuggestions(shiftId),
        enabled: !!shiftId,
    });
}

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

export function useAssignmentPreview(shiftId: string, userId: string) {
    return useQuery({
        queryKey: keys.assignmentPreview(shiftId, userId),
        queryFn: () => previewAssignment(shiftId, userId),
        enabled: !!shiftId && !!userId,
    });
}

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
export function useSwapRequests() {
    return useQuery({
        queryKey: keys.swaps,
        queryFn: () => getSwapRequests(),
    });
}

export function useSwapRequest(id: string) {
    return useQuery({
        queryKey: keys.swap(id),
        queryFn: () => getSwapRequest(id),
        enabled: !!id,
    });
}

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

export function useAvailableDrops() {
    return useQuery({
        queryKey: keys.drops,
        queryFn: () => getAvailableDrops(),
    });
}

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

export function useSwapAction(action: "accept" | "reject" | "approve" | "decline") {
    const queryClient = useQueryClient();
    const { showSuccess, showError } = useToast();
    const successLabel = (() => {
        if (action === "accept") return "Swap accepted";
        if (action === "reject") return "Swap rejected";
        if (action === "approve") return "Request approved";
        return "Request declined";
    })();
    return useMutation({
        mutationFn: ({ id, data, isDrop = false }: { id: string; data: SwapActionRequest; isDrop?: boolean }) => {
            if (isDrop) {
                if (action === "approve") return approveDrop(id, data);
                if (action === "decline") return declineDrop(id, data);
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
export function useOvertimeDashboard(locationId: string, weekStart: string) {
    return useQuery({
        queryKey: keys.overtime(locationId, weekStart),
        queryFn: () => getOvertimeDashboard(locationId, weekStart),
        enabled: !!locationId && !!weekStart,
    });
}

export function useFairnessReport(locationId: string, startDate: string, endDate: string) {
    return useQuery({
        queryKey: keys.fairness(locationId, startDate, endDate),
        queryFn: () => getFairnessReport(locationId, startDate, endDate),
        enabled: !!locationId && !!startDate && !!endDate,
    });
}

export function useOnDuty(locationId?: string) {
    return useQuery({
        queryKey: keys.onDuty(locationId),
        queryFn: () => getOnDuty(locationId),
        refetchInterval: 60_000,
        refetchIntervalInBackground: false,
    });
}

// --- Audit ---
export function useAuditLogs(page: number) {
    return useQuery({
        queryKey: keys.audit(page),
        queryFn: () => getAuditLogs(page),
        placeholderData: keepPreviousData,
    });
}

// --- Notifications ---
export function useNotifications(unreadOnly = false) {
    return useQuery({
        queryKey: keys.notifications(unreadOnly),
        queryFn: () => getNotifications(unreadOnly),
    });
}

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

export function useMarkNotificationRead() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (notificationId: string) => markNotificationRead(notificationId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["notifications"] });
        },
    });
}
