import axios from "axios";
import {
    AssignmentCreateRequest,
    AssignmentListResponse,
    AssignmentPreviewResponse,
    AuthUser,
    ConstraintSuggestion,
    AvailabilityReplaceRequest,
    AvailabilityResponse,
    AvailableDropListResponse,
    AvailableDropRequest,
    FairnessReportResponse,
    LocationListResponse,
    LocationResponse,
    MyAssignmentListResponse,
    NotificationListResponse,
    OnDutyResponse,
    OvertimeDashboardResponse,
    PublishWeekRequest,
    PublishWeekResponse,
    ShiftCreateRequest,
    ShiftListResponse,
    ShiftResponse,
    ShiftUpdateRequest,
    SwapActionRequest,
    SwapCreateRequest,
    SwapRequestListResponse,
    SwapRequestResponse,
    UserListResponse,
    UserResponse,
    UserUpdateRequest,
    DropCreateRequest,
    DropPickupRequest,
    AuditLogListResponse,
    AuditLogQuery,
    SkillAttachRequest,
    CertificationAttachRequest,
    UserCreateRequest,
} from "./types";

// Construct dynamic base URL to match current origin (handles localhost/127.0.0.1 consistency)
const getBaseUrl = () => {
    if (import.meta.env.VITE_API_BASE_URL) return import.meta.env.VITE_API_BASE_URL;
    const hostname = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
    return `http://${hostname}:8000/api/v1`;
};

const api = axios.create({
    baseURL: getBaseUrl(),
    withCredentials: true,
});

// --- Auth ---
export async function login(email: string, password: string): Promise<AuthUser> {
    const response = await api.post("/auth/login", { email, password });
    return response.data.user;
}

export async function logout(): Promise<void> {
    await api.post("/auth/logout");
}

export async function getMe(): Promise<AuthUser> {
    const response = await api.get("/auth/me");
    return response.data.user;
}

// --- Locations ---
export async function getLocations(): Promise<LocationListResponse> {
    const response = await api.get("/locations");
    return response.data;
}

export async function getLocation(id: string): Promise<LocationResponse> {
    const response = await api.get(`/locations/${id}`);
    return response.data;
}

// --- Users ---
export async function getUsers(locationId?: string, includeInactive = false): Promise<UserListResponse> {
    const params = new URLSearchParams();
    if (locationId) params.append("location_id", locationId);
    if (includeInactive) params.append("include_inactive", "true");
    params.append("limit", "100"); // Getting all users for UI lists
    const response = await api.get(`/users?${params.toString()}`);
    return response.data;
}

export async function getUser(id: string): Promise<UserResponse> {
    const response = await api.get(`/users/${id}`);
    return response.data;
}

export async function updateUser(id: string, data: UserUpdateRequest): Promise<UserResponse> {
    const response = await api.put(`/users/${id}`, data);
    return response.data;
}

export async function createUser(data: UserCreateRequest): Promise<UserResponse> {
    const response = await api.post(`/users`, data);
    return response.data;
}

export async function deleteUser(id: string): Promise<void> {
    await api.delete(`/users/${id}`);
}

export async function addSkill(userId: string, data: SkillAttachRequest): Promise<void> {
    await api.post(`/users/${userId}/skills`, data);
}

export async function removeSkill(userId: string, skillId: string): Promise<void> {
    await api.delete(`/users/${userId}/skills/${skillId}`);
}

export async function addCertification(userId: string, data: CertificationAttachRequest): Promise<void> {
    await api.post(`/users/${userId}/certifications`, data);
}

export async function removeCertification(userId: string, locationId: string): Promise<void> {
    await api.delete(`/users/${userId}/certifications/${locationId}`);
}

export async function getUserAvailability(userId: string): Promise<AvailabilityResponse> {
    const response = await api.get(`/users/${userId}/availability`);
    return response.data;
}

export async function updateUserAvailability(userId: string, data: AvailabilityReplaceRequest): Promise<AvailabilityResponse> {
    const response = await api.put(`/users/${userId}/availability`, data);
    return response.data;
}

// --- Skills ---
export async function getSkills(): Promise<{ id: string; name: string }[]> {
    const response = await api.get("/skills");
    return response.data;
}

// --- Shifts ---
export async function getShifts(locationId: string, weekStart: string): Promise<ShiftListResponse> {
    const response = await api.get(`/shifts`, {
        params: { location_id: locationId, week_start: weekStart },
    });
    return response.data;
}

export async function createShift(locationId: string, data: ShiftCreateRequest): Promise<ShiftResponse> {
    const response = await api.post(`/shifts`, data, {
        params: { location_id: locationId },
    });
    return response.data;
}

export async function updateShift(locationId: string, shiftId: string, data: ShiftUpdateRequest): Promise<ShiftResponse> {
    const response = await api.put(`/shifts/${shiftId}`, data, {
        params: { location_id: locationId },
    });
    return response.data;
}

export async function deleteShift(locationId: string, shiftId: string): Promise<void> {
    await api.delete(`/shifts/${shiftId}`, {
        params: { location_id: locationId },
    });
}

export async function publishWeek(locationId: string, data: PublishWeekRequest): Promise<PublishWeekResponse> {
    const response = await api.post(`/shifts/publish`, data, {
        params: { location_id: locationId },
    });
    return response.data;
}

// --- Assignments ---
export async function getAssignments(shiftId: string): Promise<AssignmentListResponse> {
    const response = await api.get(`/assignments`, {
        params: { shift_id: shiftId },
    });
    return response.data;
}

export async function previewAssignment(shiftId: string, userId: string): Promise<AssignmentPreviewResponse> {
    const response = await api.get(`/assignments/preview`, {
        params: { shift_id: shiftId, user_id: userId },
    });
    return response.data;
}

export async function createAssignment(shiftId: string, data: AssignmentCreateRequest): Promise<void> {
    await api.post(`/assignments`, data, {
        params: { shift_id: shiftId },
    });
}

export async function deleteAssignment(shiftId: string, assignmentId: string): Promise<void> {
    await api.delete(`/assignments/${assignmentId}`, {
        params: { shift_id: shiftId },
    });
}

export async function getMyAssignments(): Promise<MyAssignmentListResponse> {
    const response = await api.get("/assignments/me");
    return response.data;
}

export async function getShiftSuggestions(shiftId: string): Promise<ConstraintSuggestion[]> {
    const response = await api.get(`/assignments/shifts/${shiftId}/suggestions`);
    return response.data;
}

// --- Swaps & Drops ---
export async function getSwapRequests(): Promise<SwapRequestListResponse> {
    const response = await api.get(`/swaps`);
    return response.data;
}

export async function getSwapRequest(id: string): Promise<SwapRequestResponse> {
    const response = await api.get(`/swaps/${id}`);
    return response.data;
}

export async function createSwapRequest(data: SwapCreateRequest): Promise<void> {
    await api.post(`/swaps`, data);
}

export async function acceptSwap(requestId: string, data: SwapActionRequest): Promise<void> {
    await api.post(`/swaps/${requestId}/accept`, data);
}

export async function rejectSwap(requestId: string, data: SwapActionRequest): Promise<void> {
    await api.post(`/swaps/${requestId}/reject`, data);
}

export async function approveSwap(requestId: string, data: SwapActionRequest): Promise<void> {
    await api.post(`/swaps/${requestId}/approve`, data);
}

export async function declineSwap(requestId: string, data: SwapActionRequest): Promise<void> {
    await api.post(`/swaps/${requestId}/decline`, data);
}

export async function getAvailableDrops(): Promise<AvailableDropListResponse> {
    const response = await api.get(`/swaps/drops/available`);
    return response.data;
}

export async function createDrop(data: DropCreateRequest): Promise<void> {
    await api.post(`/swaps/drops`, data);
}

export async function pickupDrop(requestId: string, data: DropPickupRequest): Promise<void> {
    await api.post(`/swaps/drops/${requestId}/pickup`, data);
}

export async function approveDrop(requestId: string, data: SwapActionRequest): Promise<void> {
    await api.post(`/swaps/drops/${requestId}/approve`, data);
}

export async function declineDrop(requestId: string, data: SwapActionRequest): Promise<void> {
    await api.post(`/swaps/drops/${requestId}/decline`, data);
}

export async function notifyQualifiedStaff(requestId: string): Promise<{ notified: number }> {
    const response = await api.post(`/swaps/drops/${requestId}/notify-qualified`);
    return response.data;
}

// --- Analytics ---
export async function getOvertimeDashboard(locationId: string, weekStart: string): Promise<OvertimeDashboardResponse> {
    const response = await api.get(`/analytics/overtime-dashboard`, {
        params: { location_id: locationId, week_start: weekStart },
    });
    return response.data;
}

export async function getFairnessReport(locationId: string, startDate: string, endDate: string): Promise<FairnessReportResponse> {
    const response = await api.get(`/analytics/fairness-report`, {
        params: { location_id: locationId, start_date: startDate, end_date: endDate },
    });
    return response.data;
}

export async function getOnDuty(locationId?: string): Promise<OnDutyResponse> {
    const response = await api.get(`/analytics/on-duty`, {
        params: locationId ? { location_id: locationId } : {},
    });
    return response.data;
}

// --- Audit ---
function normalizeAuditLogResponse(raw: any): AuditLogListResponse {
    const pagination = raw?.pagination ?? {};
    const logs = Array.isArray(raw?.logs)
        ? raw.logs.map((entry: any) => ({
            ...entry,
            location_name: entry.location_name ?? entry.location_id ?? null,
            details: entry.details ?? entry.reason ?? null,
        }))
        : [];
    return {
        logs,
        total: Number(pagination.total ?? raw?.total ?? logs.length),
        page: Number(pagination.page ?? raw?.page ?? 1),
        limit: Number(pagination.limit ?? raw?.limit ?? 50),
    };
}

export async function getAuditLogs(query: AuditLogQuery = {}): Promise<AuditLogListResponse> {
    const response = await api.get(`/audit/audit-logs`, {
        params: {
            page: query.page ?? 1,
            limit: query.limit ?? 50,
            entity_type: query.entity_type,
            entity_id: query.entity_id,
            location_id: query.location_id,
            start_date: query.start_date,
            end_date: query.end_date,
        },
    });
    return normalizeAuditLogResponse(response.data);
}

export async function exportAuditLogs(query: AuditLogQuery = {}): Promise<Blob> {
    const response = await api.get(`/audit/audit-logs/export`, {
        params: {
            entity_type: query.entity_type,
            entity_id: query.entity_id,
            location_id: query.location_id,
            start_date: query.start_date,
            end_date: query.end_date,
        },
        responseType: "blob",
    });
    return response.data as Blob;
}

// --- Notifications ---
export async function getNotifications(unreadOnly = false): Promise<NotificationListResponse> {
    const response = await api.get(`/notifications`, {
        params: { unreadOnly },
    });
    return response.data;
}

export async function markAllNotificationsRead(): Promise<void> {
    await api.put(`/notifications/read-all`);
}

export async function markNotificationRead(notificationId: string): Promise<void> {
    await api.put(`/notifications/${notificationId}/read`);
}

export default api;
