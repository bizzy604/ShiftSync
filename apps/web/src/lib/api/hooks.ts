import { useMutation, useQuery, useQueryClient, keepPreviousData } from "@tanstack/react-query";
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
    deleteAssignment,
    deleteShift,
    deleteUser,
    getAssignments,
    getAssignmentSuggestions,
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
    pickupDrop,
    previewAssignment,
    publishWeek,
    rejectSwap,
    removeCertification,
    removeSkill,
    updateShift,
    updateUser,
    updateUserAvailability,
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
    onDuty: (locationId?: string) => ["analytics", "onDuty", locationId] as const,
    overtime: (locationId: string, weekStart: string) => ["analytics", "overtime", locationId, weekStart] as const,
    fairness: (locationId: string, startDate: string, endDate: string) => ["analytics", "fairness", locationId, startDate, endDate] as const,
    audit: (page: number) => ["audit", page] as const,
    notifications: (unreadOnly: boolean) => ["notifications", { unreadOnly }] as const,
};

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
    return useMutation({
        mutationFn: ({ id, data }: { id: string; data: UserUpdateRequest }) => updateUser(id, data),
        onSuccess: (_, { id }) => {
            queryClient.invalidateQueries({ queryKey: keys.user(id) });
            queryClient.invalidateQueries({ queryKey: keys.users() });
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

export function useUpdateAvailability() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ id, data }: { id: string; data: AvailabilityReplaceRequest }) => updateUserAvailability(id, data),
        onSuccess: (_, { id }) => {
            queryClient.invalidateQueries({ queryKey: keys.availability(id) });
        },
    });
}

export function useCreateUser() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (data: UserCreateRequest) => createUser(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: keys.users() });
        },
    });
}

export function useDeleteUser() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (id: string) => deleteUser(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: keys.users() });
        },
    });
}

export function useAddSkill() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ userId, data }: { userId: string; data: SkillAttachRequest }) => addSkill(userId, data),
        onSuccess: (_, { userId }) => {
            queryClient.invalidateQueries({ queryKey: keys.user(userId) });
        },
    });
}

export function useRemoveSkill() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ userId, skillId }: { userId: string; skillId: string }) => removeSkill(userId, skillId),
        onSuccess: (_, { userId }) => {
            queryClient.invalidateQueries({ queryKey: keys.user(userId) });
        },
    });
}

export function useAddCertification() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ userId, data }: { userId: string; data: CertificationAttachRequest }) => addCertification(userId, data),
        onSuccess: (_, { userId }) => {
            queryClient.invalidateQueries({ queryKey: keys.user(userId) });
        },
    });
}

export function useRemoveCertification() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ userId, locationId }: { userId: string; locationId: string }) => removeCertification(userId, locationId),
        onSuccess: (_, { userId }) => {
            queryClient.invalidateQueries({ queryKey: keys.user(userId) });
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
    return useMutation({
        mutationFn: ({ locationId, data }: { locationId: string; data: ShiftCreateRequest }) => createShift(locationId, data),
        onSuccess: (_, { locationId, data }) => {
            queryClient.invalidateQueries({ queryKey: ["shifts", locationId] });
        },
    });
}

export function useUpdateShift() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ locationId, shiftId, data }: { locationId: string; shiftId: string; data: ShiftUpdateRequest }) =>
            updateShift(locationId, shiftId, data),
        onSuccess: (_, { locationId }) => {
            queryClient.invalidateQueries({ queryKey: ["shifts", locationId] });
        },
    });
}

export function useDeleteShift() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ locationId, shiftId }: { locationId: string; shiftId: string }) => deleteShift(locationId, shiftId),
        onSuccess: (_, { locationId }) => {
            queryClient.invalidateQueries({ queryKey: ["shifts", locationId] });
        },
    });
}

export function usePublishWeek() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ locationId, data }: { locationId: string; data: PublishWeekRequest }) => publishWeek(locationId, data),
        onSuccess: (_, { locationId, data }) => {
            queryClient.invalidateQueries({ queryKey: keys.shifts(locationId, data.week_start as unknown as string) });
            queryClient.invalidateQueries({ queryKey: ["shifts", locationId] });
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

export function useAssignmentSuggestions(shiftId: string) {
    return useQuery({
        queryKey: keys.assignmentSuggestions(shiftId),
        queryFn: () => getAssignmentSuggestions(shiftId),
        enabled: !!shiftId,
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
    return useMutation({
        mutationFn: ({ shiftId, data }: { shiftId: string; data: AssignmentCreateRequest }) => createAssignment(shiftId, data),
        onSuccess: (_, { shiftId }) => {
            queryClient.invalidateQueries({ queryKey: keys.assignments(shiftId) });
            queryClient.invalidateQueries({ queryKey: ["shifts"] });
        },
    });
}

export function useDeleteAssignment() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ shiftId, assignmentId }: { shiftId: string; assignmentId: string }) => deleteAssignment(shiftId, assignmentId),
        onSuccess: (_, { shiftId }) => {
            queryClient.invalidateQueries({ queryKey: keys.assignments(shiftId) });
            queryClient.invalidateQueries({ queryKey: ["shifts"] });
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
    return useMutation({
        mutationFn: (data: SwapCreateRequest) => createSwapRequest(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: keys.swaps });
            queryClient.invalidateQueries({ queryKey: ["shifts"] });
            queryClient.invalidateQueries({ queryKey: ["assignments"] });
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
    return useMutation({
        mutationFn: (data: DropCreateRequest) => createDrop(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: keys.drops });
            queryClient.invalidateQueries({ queryKey: keys.myAssignments });
            queryClient.invalidateQueries({ queryKey: ["shifts"] });
            queryClient.invalidateQueries({ queryKey: ["assignments"] });
        },
    });
}

export function usePickupDrop() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ id, data }: { id: string; data: DropPickupRequest }) => pickupDrop(id, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: keys.drops });
            queryClient.invalidateQueries({ queryKey: keys.swaps });
        },
    });
}

export function useSwapAction(action: "accept" | "reject" | "approve" | "decline") {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({ id, data, isDrop = false }: { id: string; data: SwapActionRequest; isDrop?: boolean }) => {
            if (isDrop) {
                if (action === "approve") return approveDrop(id, data);
                if (action === "decline") return rejectSwap(id, data);
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
                    return rejectSwap(id, data);
                default:
                    throw new Error("Unknown action");
            }
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: keys.swaps });
            queryClient.invalidateQueries({ queryKey: keys.drops });
            queryClient.invalidateQueries({ queryKey: ["shifts"] });
            queryClient.invalidateQueries({ queryKey: ["assignments"] });
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
    return useMutation({
        mutationFn: () => markAllNotificationsRead(),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["notifications"] });
        },
    });
}
