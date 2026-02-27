// Auth / Users
export type Role = "admin" | "manager" | "staff";
export type NotificationPref = "in_app" | "in_app_email";

export interface AuthUser {
    id: string;
    name: string;
    email: string;
    role: Role;
    location_ids: string[];
    home_timezone?: string;
}

export interface UserCreateRequest {
    name: string;
    email: string;
    password?: string;
    role: Role;
    home_timezone?: string;
    desired_hours_per_week?: number;
    hourly_rate?: number | null;
    notification_pref?: NotificationPref;
}

export interface SkillAttachRequest {
    skill_id: string;
}

export interface CertificationAttachRequest {
    location_id: string;
}

export interface SkillResponse {
    id: string;
    name: string;
}

export interface SkillCreateRequest {
    name: string;
}

export interface UserUpdateRequest {
    name?: string;
    role?: Role;
    home_timezone?: string;
    desired_hours_per_week?: number;
    hourly_rate?: number | null;
    notification_pref?: NotificationPref;
    is_active?: boolean;
}

export interface UserResponse {
    id: string;
    name: string;
    email: string;
    role: Role;
    home_timezone: string;
    desired_hours_per_week: number;
    hourly_rate: number | null;
    notification_pref: NotificationPref;
    is_active: boolean;
    created_at: string;
    updated_at: string;
    user_skills?: UserSkillResponse[];
    user_location_certifications?: UserCertificationResponse[];
}

export interface UserListResponse {
    users: UserResponse[];
    total: number;
    page: number;
    limit: number;
}

export interface UserSkillResponse {
    skill_id: string;
    skill_name: string;
}

export interface UserCertificationResponse {
    location_id: string;
    location_name: string;
    certified_at: string;
    revoked_at: string | null;
}

export interface RecurringAvailabilityIn {
    day_of_week: number;
    start_clock_time: string;
    end_clock_time: string;
}

export interface ExceptionAvailabilityIn {
    date: string;
    is_available: boolean;
    start_clock_time?: string;
    end_clock_time?: string;
}

export interface AvailabilityReplaceRequest {
    recurring: RecurringAvailabilityIn[];
    exceptions: ExceptionAvailabilityIn[];
}

export interface AvailabilityEntryResponse {
    id: string;
    avail_type: "recurring" | "exception";
    day_of_week: number | null;
    specific_date: string | null;
    start_clock: string | null;
    end_clock: string | null;
    is_available: boolean;
}

export interface AvailabilityResponse {
    user_id: string;
    recurring: AvailabilityEntryResponse[];
    exceptions: AvailabilityEntryResponse[];
}

// Locations
export interface LocationCreateRequest {
    name: string;
    address?: string;
    iana_timezone: string;
}

export interface LocationUpdateRequest {
    name?: string;
    address?: string;
    iana_timezone?: string;
    is_active?: boolean;
}

export interface LocationResponse {
    id: string;
    name: string;
    address: string | null;
    iana_timezone: string;
    is_active: boolean;
    created_at: string;
}

export interface LocationListResponse {
    locations: LocationResponse[];
}

// Shifts
export type ShiftStatus = "draft" | "published" | "cancelled";

export interface ShiftCreateRequest {
    date: string;
    start_time: string;
    end_time: string;
    required_skill_id: string;
    headcount_needed?: number;
}

export interface ShiftUpdateRequest {
    date?: string;
    start_time?: string;
    end_time?: string;
    required_skill_id?: string;
    headcount_needed?: number;
    override_reason?: string;
}

export interface PublishWeekRequest {
    week_start: string;
}

export interface PublishWeekResponse {
    published_shifts: number;
    edit_cutoff_utc: string | null;
    notified_staff_count: number;
}

export interface ShiftRequiredSkill {
    id: string;
    name: string;
}

export interface ShiftResponse {
    id: string;
    location_id: string;
    date: string;
    start_utc: string;
    end_utc: string;
    start_local: string;
    end_local: string;
    required_skill: ShiftRequiredSkill;
    headcount_needed: number;
    status: ShiftStatus;
    week_start: string;
    edit_cutoff_utc: string | null;
    created_at: string;
}

export interface ShiftListResponse {
    shifts: ShiftResponse[];
}

// Assignments
export type AssignmentStatus = "assigned" | "swap_pending" | "dropped" | "removed";
export type ConstraintSeverity = "HARD_BLOCK" | "WARNING" | "OVERRIDE_REQUIRED";

export interface AssignmentCreateRequest {
    user_id: string;
    override_reason?: string;
}

export interface AssignmentResponse {
    id: string;
    shift_id: string;
    user_id: string;
    user_name: string;
    status: AssignmentStatus;
    version: number;
    assigned_by: string;
    assigned_at: string;
}

export interface AssignmentListResponse {
    assignments: AssignmentResponse[];
}

export interface AssignmentShiftInfo {
    id: string;
    location_id: string;
    location_name: string;
    shift_date: string;
    start_utc: string;
    end_utc: string;
    start_local: string;
    end_local: string;
    required_skill: string;
}

export interface MyAssignmentResponse {
    id: string;
    status: AssignmentStatus;
    shift: AssignmentShiftInfo;
}

export interface MyAssignmentListResponse {
    assignments: MyAssignmentResponse[];
}

export interface ConstraintDetail {
    rule: string;
    description: string;
    severity: ConstraintSeverity;
}

export interface ConstraintSuggestion {
    user_id: string;
    name: string;
    reason: string;
}

export interface AssignmentPreviewResponse {
    user_id: string;
    user_name: string;
    valid: boolean;
    violations: ConstraintDetail[];
    warnings: ConstraintDetail[];
    requires_override: boolean;
    projected_weekly_hours: number;
    projected_daily_hours: number;
    projected_overtime_cost: number;
    suggestions: ConstraintSuggestion[];
}

// Swaps & Drops
export type SwapType = "swap" | "drop";
export type SwapStatus = "OPEN" | "PENDING_ACCEPTEE" | "PENDING_MANAGER" | "APPROVED" | "REJECTED" | "CANCELLED" | "EXPIRED";

export interface SwapCreateRequest {
    my_assignment_id: string;
    target_user_id: string;
    target_assignment_id?: string;
}

export interface SwapActionRequest {
    note?: string;
}

export interface DropCreateRequest {
    assignment_id: string;
}

export interface DropPickupRequest {
    note?: string;
}

export interface SwapRequestResponse {
    id: string;
    type: SwapType;
    status: SwapStatus;
    requester_assignment_id: string;
    requester_name: string | null;
    target_user_id: string | null;
    target_name: string | null;
    candidate_assignment_id: string | null;
    pickup_user_id: string | null;
    pickup_name: string | null;
    initiated_by: string;
    expires_at: string | null;
    created_at: string;
    resolved_at: string | null;
    resolution_note: string | null;
    shift_date: string | null;
    shift_time: string | null;
    shift_label: string | null;
}

export interface SwapRequestListResponse {
    requests: SwapRequestResponse[];
}

export interface AvailableDropShift {
    id: string;
    date: string;
    start_local: string;
    end_local: string;
    location: any;
    required_skill: string;
}

export interface AvailableDropRequest {
    drop_request_id: string;
    shift: AvailableDropShift;
    original_staff: any;
    expires_at: string | null;
}

export interface AvailableDropListResponse {
    available: AvailableDropRequest[];
}

// Analytics
export interface OvertimeStaffRow {
    user_id: string;
    name: string;
    projected_weekly_hours: number;
    overtime_hours: number;
    projected_overtime_cost: number;
    offending_assignment_ids: string[];
}

export interface OvertimeDashboardResponse {
    week_start: string;
    location_id: string;
    total_projected_overtime_cost: number;
    staff: OvertimeStaffRow[];
}

export interface FairnessStaffRow {
    user_id: string;
    name: string;
    total_hours: number;
    desired_hours_per_week: number;
    scheduling_variance_pct: number;
    premium_shift_count: number;
    premium_shift_pct: number;
}

export interface FairnessPeriod {
    start_date: string;
    end_date: string;
}

export interface FairnessReportResponse {
    period: FairnessPeriod;
    location_id: string;
    fairness_score: number;
    fairness_grade: string;
    staff: FairnessStaffRow[];
}

export interface HoursDistributionRow {
    user_id: string;
    name: string;
    total_hours: number;
    assigned_shift_count: number;
}

export interface HoursDistributionResponse {
    period: FairnessPeriod;
    location_id: string;
    total_hours: number;
    staff: HoursDistributionRow[];
}

export interface OnDutyStaffRow {
    user_id: string;
    name: string;
    skill: string;
}

export interface OnDutyCurrentShift {
    id: string;
    start_local: string;
    end_local: string;
}

export interface OnDutyLocationRow {
    location_id: string;
    location_name: string;
    iana_timezone: string;
    local_time: string;
    current_shift: OnDutyCurrentShift | null;
    on_duty_staff: OnDutyStaffRow[];
}

export interface OnDutyResponse {
    as_of: string;
    locations: OnDutyLocationRow[];
}

// Audit
export interface AuditLogResponse {
    id: string;
    actor_id: string;
    actor_name: string;
    action_type: string;
    entity_type: string;
    entity_id: string;
    before_state: any;
    after_state: any;
    reason: string | null;
    location_id: string | null;
    location_name: string | null;
    details: string | null;
    created_at: string;
}

export interface AuditLogListResponse {
    logs: AuditLogResponse[];
    total: number;
    page: number;
    limit: number;
}

export interface AuditLogQuery {
    page?: number;
    limit?: number;
    entity_type?: string;
    entity_id?: string;
    location_id?: string;
    start_date?: string;
    end_date?: string;
}

// Notifications
export interface NotificationPreferencesUpdateRequest {
    notification_pref: NotificationPref;
}

export interface NotificationResponse {
    id: string;
    type: string;
    message: string;
    payload: any;
    created_at: string;
    read_at: string | null;
}

export interface NotificationListResponse {
    unread_count: number;
    notifications: NotificationResponse[];
    pagination: Record<string, number>;
}
