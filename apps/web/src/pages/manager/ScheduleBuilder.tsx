import React, { useState, useEffect } from "react";
import { format, startOfWeek, addDays, parseISO, differenceInDays, startOfDay } from "date-fns";
import { ChevronLeft, ChevronRight, ChevronDown, Plus, AlertTriangle, X, Clock, MapPin, Loader2 } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { AppLayout } from "../../components/NavBar";
import { Avatar } from "../../components/Avatar";
import { Badge } from "../../components/Badge";
import { NotificationCentre } from "../staff/NotificationCentre";

import { useLocations, useShifts, useUsers, useAssignments, usePublishWeek, useOvertimeDashboard, useNotifications } from "../../lib/api/hooks";
import { ShiftResponse } from "../../lib/api/types";
import { AssignmentModal } from "./AssignmentModal";
import { CreateShiftModal } from "./CreateShiftModal";

/* ========== Helpers ========== */
const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const PERIODS = ["Morning", "Afternoon", "Night"];

function extractClockParts(value: string): { hour: number; minute: number } | null {
    if (!value) return null;
    const clock = value.includes("T") ? value.slice(11, 16) : value.slice(0, 5);
    const match = /^([01]\d|2[0-3]):([0-5]\d)$/.exec(clock);
    if (!match) return null;
    return { hour: Number(match[1]), minute: Number(match[2]) };
}

function formatTime(value: string) {
    const parts = extractClockParts(value);
    if (!parts) return "";
    const { hour: h, minute: m } = parts;
    const period = h >= 12 ? "pm" : "am";
    const h12 = h % 12 || 12;
    return `${h12}${m > 0 ? `:${m.toString().padStart(2, "0")}` : ""}${period}`;
}

const getShiftPeriod = (timeStr: string) => {
    const parts = extractClockParts(timeStr);
    if (!parts) return 0;
    const h = parts.hour;
    if (h < 12) return 0;
    if (h < 18) return 1; // 12pm - 5:59pm is Afternoon
    return 2; // 6pm+ is Night
};

const getDefaultMobileDayIndex = (targetWeekStart: Date) => {
    const currentWeekStart = startOfWeek(new Date(), { weekStartsOn: 1 });
    const isCurrentWeek = differenceInDays(startOfDay(targetWeekStart), startOfDay(currentWeekStart)) === 0;
    if (!isCurrentWeek) return 0;
    const dayIndex = differenceInDays(startOfDay(new Date()), startOfDay(targetWeekStart));
    return Math.min(Math.max(dayIndex, 0), 6);
};

/* ========== Sub-Components ========== */
function StaffSidebar({ locationId, weekStart }: { locationId: string; weekStart: string }) {
    const { data: usersData, isLoading: isLoadingUsers } = useUsers(locationId);
    const { data: otData, isLoading: isLoadingOT } = useOvertimeDashboard(locationId, weekStart);
    const [hoveredStaff, setHoveredStaff] = useState<string | null>(null);

    const isLoading = isLoadingUsers || isLoadingOT;

    if (isLoading) {
        return (
            <div className="p-4 flex justify-center text-gray-400">
                <Loader2 size={24} className="animate-spin" />
            </div>
        );
    }

    const staff =
        usersData?.users.filter(
            (u) => u.role === "staff" && u.is_active
        ) || [];

    return (
        <div className="p-4">
            <h3 className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-3">Staff List</h3>
            <div className="space-y-1.5">
                {staff.map((s) => {
                    const otInfo = otData?.staff.find(row => row.user_id === s.id);
                    const hours = otInfo?.projected_weekly_hours || 0;
                    const maxHours = s.desired_hours_per_week || 40;
                    const isOvertime = hours > 40;

                    return (
                        <div
                            key={s.id}
                            className="relative flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-white cursor-pointer transition-base group"
                            onMouseEnter={() => setHoveredStaff(s.id)}
                            onMouseLeave={() => setHoveredStaff(null)}
                        >
                            <Avatar name={s.name} size="sm" color={isOvertime ? "bg-amber-warn" : "bg-navy"} />
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-navy truncate">{s.name}</p>
                                <p className={`text-[10px] truncate ${isOvertime ? "text-amber-warn font-bold" : "text-gray-500"}`}>
                                    {hours}h / {maxHours}h goal
                                </p>
                            </div>

                            {hoveredStaff === s.id && (
                                <div className="absolute left-full ml-2 top-0 bg-navy text-white text-xs rounded-lg p-3 w-52 shadow-xl z-30 animate-fade-in">
                                    <p className="font-semibold mb-1">{s.name}</p>
                                    <p className="text-white/70">
                                        Projected: {hours}h / {maxHours}h
                                    </p>
                                    <div className="w-full bg-white/20 rounded-full h-1.5 mt-1.5 mb-2">
                                        <div
                                            className={`h-1.5 rounded-full ${isOvertime ? "bg-amber-warn" : "bg-success-light"}`}
                                            style={{ width: `${Math.min((hours / maxHours) * 100, 100)}%` }}
                                        />
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

function ShiftTileComponent({ shift, onClick }: { shift: ShiftResponse; onClick: () => void }) {
    const { data: assignmentsData, isLoading } = useAssignments(shift.id);

    if (isLoading) {
        return (
            <div className="w-full px-2 py-1.5 rounded-lg border-2 border-dashed border-gray-200 bg-gray-50 flex items-center gap-1.5">
                <Loader2 size={12} className="animate-spin text-gray-400" />
                <span className="text-xs text-gray-400">Loading...</span>
            </div>
        );
    }

    const assignments = assignmentsData?.assignments.filter((a) => a.status === "assigned") || [];
    const assignedCount = assignments.length;
    const isFullyAssigned = assignedCount >= shift.headcount_needed;
    const label = `${formatTime(shift.start_local)}-${formatTime(shift.end_local)}`;

    if (!isFullyAssigned) {
        return (
            <button
                onClick={onClick}
                className="w-full text-left px-2 py-1.5 rounded-lg border-2 border-dashed border-amber-warn/50 bg-amber-warn-50 text-amber-warn text-xs font-medium flex items-center gap-1.5 hover:border-amber-warn hover:shadow-md transition-base"
            >
                <AlertTriangle size={12} className="flex-shrink-0" />
                <span className="truncate">
                    {shift.headcount_needed - assignedCount} needed · {shift.required_skill.name}
                </span>
            </button>
        );
    }

    const staffNames = assignments.map((a) => a.user_name.split(" ")[0]).join(", ");

    return (
        <div
            onClick={onClick}
            className={`w-full px-2.5 py-1.5 rounded-lg ${shift.status === "published" ? "bg-teal hover:bg-teal-dark" : "bg-admin-slate hover:opacity-90"
                } text-white text-xs font-medium flex items-center gap-1.5 shadow-sm hover:shadow-md transition-base cursor-pointer`}
        >
            <Clock size={11} className="flex-shrink-0" />
            <span className="truncate">
                {shift.required_skill.name} · {label} · {staffNames}
            </span>
        </div>
    );
}

/* ========== Main Component ========== */
export function ScheduleBuilder() {
    const [searchParams] = useSearchParams();
    const requestedLocationId = searchParams.get("location_id");
    const [weekStart, setWeekStart] = useState<Date>(() => startOfWeek(new Date(), { weekStartsOn: 1 }));
    const [locationId, setLocationId] = useState<string>("");
    const [activeMobileDayIndex, setActiveMobileDayIndex] = useState(() =>
        getDefaultMobileDayIndex(startOfWeek(new Date(), { weekStartsOn: 1 }))
    );
    const [selectedShiftId, setSelectedShiftId] = useState<string | null>(null);
    const [isNotificationOpen, setIsNotificationOpen] = useState(false);

    // Create Shift State
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [createDate, setCreateDate] = useState("");
    const [createPeriodIndex, setCreatePeriodIndex] = useState(0);

    const { data: locationsData } = useLocations();
    const { data: notificationsData } = useNotifications();
    const locations = locationsData?.locations || [];
    const unreadCount = notificationsData?.unread_count || 0;

    // Auto-select first location
    useEffect(() => {
        if (!locationId && locations.length > 0) {
            const requestedExists = requestedLocationId && locations.some((loc) => loc.id === requestedLocationId);
            setLocationId(requestedExists ? requestedLocationId! : locations[0].id);
        }
    }, [locations, locationId, requestedLocationId]);

    useEffect(() => {
        setActiveMobileDayIndex(getDefaultMobileDayIndex(weekStart));
    }, [weekStart]);

    const weekStartStr = format(weekStart, "yyyy-MM-dd");
    const { data: shiftsData, isLoading: isLoadingShifts } = useShifts(locationId, weekStartStr);
    const publishMutation = usePublishWeek();

    const shifts = shiftsData?.shifts || [];
    const isPublished = shifts.some((s) => s.status === "published");

    const handlePreviousWeek = () => setWeekStart((prev) => addDays(prev, -7));
    const handleNextWeek = () => setWeekStart((prev) => addDays(prev, 7));

    const handlePublish = () => {
        if (!locationId || shifts.length === 0) return;
        publishMutation.mutate({ locationId, data: { week_start: weekStartStr as any } });
    };

    const getShiftsForCell = (dayIndex: number, periodIndex: number) => {
        return shifts.filter((s) => {
            const shiftDay = differenceInDays(parseISO(s.date), weekStart);
            const shiftPeriod = getShiftPeriod(s.start_local);
            return shiftDay === dayIndex && shiftPeriod === periodIndex;
        });
    };

    const dayDates = Array.from({ length: 7 }).map((_, i) => format(addDays(weekStart, i), "MMM d"));
    const headerDateRange = `${format(weekStart, "eee MMM d")} – ${format(addDays(weekStart, 6), "eee MMM d, yyyy")}`;
    const shortHeaderDateRange = `${format(weekStart, "MMM d")} - ${format(addDays(weekStart, 6), "MMM d")}`;
    const currentLocation = locations.find((loc) => loc.id === locationId);

    const openCreateShiftForCell = (dayIndex: number, periodIndex: number) => {
        setCreateDate(format(addDays(weekStart, dayIndex), "yyyy-MM-dd"));
        setCreatePeriodIndex(periodIndex);
        setIsCreateModalOpen(true);
    };

    const locationSelector = (
        <div className="flex items-center justify-center flex-wrap gap-2 md:gap-4 text-xs md:text-sm">
            <div className="relative group">
                <select
                    value={locationId}
                    onChange={(e) => setLocationId(e.target.value)}
                    className="appearance-none bg-white/10 hover:bg-white/20 text-xs md:text-sm font-medium text-white px-2.5 md:px-3 py-1.5 pl-7 md:pl-8 pr-7 md:pr-8 rounded-lg outline-none transition-base cursor-pointer max-w-[155px] sm:max-w-none"
                >
                    {locations.map((loc) => (
                        <option key={loc.id} value={loc.id} className="text-navy">
                            {loc.name}
                        </option>
                    ))}
                </select>
                <MapPin size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-white/70 pointer-events-none" />
                <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-white/70 pointer-events-none" />
            </div>

            <div className="flex items-center gap-1 md:gap-2 text-xs md:text-sm">
                <button onClick={handlePreviousWeek} className="p-1 rounded hover:bg-white/10 transition-base">
                    <ChevronLeft size={18} />
                </button>
                <span className="font-medium whitespace-nowrap text-center md:hidden">{shortHeaderDateRange}</span>
                <span className="hidden md:inline font-medium whitespace-nowrap min-w-[180px] text-center">{headerDateRange}</span>
                <button onClick={handleNextWeek} className="p-1 rounded hover:bg-white/10 transition-base">
                    <ChevronRight size={18} />
                </button>
            </div>
        </div>
    );

    return (
        <AppLayout
            title="Schedule"
            role="manager"
            centerContent={locationSelector}
            sidebar={locationId ? <StaffSidebar locationId={locationId} weekStart={weekStartStr} /> : null}
            notificationCount={unreadCount}
            onBellClick={() => setIsNotificationOpen(true)}
            mainClassName="md:overflow-hidden"
        >
            <div className="flex h-full min-h-0 flex-col bg-gray-50/50">
                {/* Schedule Grid */}
                <div className="flex-1 min-h-0 overflow-auto p-2 md:p-2 lg:p-3">
                    {/* Mobile Day View */}
                    <div className="md:hidden space-y-4">
                        <div className="flex gap-2 overflow-x-auto pb-1">
                            {DAYS.map((day, dayIndex) => {
                                const isActive = activeMobileDayIndex === dayIndex;
                                return (
                                    <button
                                        key={day}
                                        type="button"
                                        onClick={() => setActiveMobileDayIndex(dayIndex)}
                                        className={`px-3 py-2 rounded-lg text-left min-w-[92px] border transition-base ${isActive
                                            ? "bg-teal/10 text-teal border-teal/30"
                                            : "bg-white text-gray-500 border-border-gray"
                                            }`}
                                    >
                                        <p className="text-[10px] font-bold uppercase">{day.slice(0, 3)}</p>
                                        <p className="text-xs font-medium">{dayDates[dayIndex]}</p>
                                    </button>
                                );
                            })}
                        </div>

                        {isLoadingShifts ? (
                            <div className="flex justify-center py-10">
                                <Loader2 className="animate-spin text-teal" size={28} />
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {PERIODS.map((period, periodIndex) => {
                                    const cellShifts = getShiftsForCell(activeMobileDayIndex, periodIndex);
                                    return (
                                        <div key={period} className="bg-white border border-border-gray rounded-xl p-3">
                                            <div className="flex items-center justify-between mb-2">
                                                <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400">{period}</p>
                                                <span className="text-[11px] text-gray-500">
                                                    {cellShifts.length} shift{cellShifts.length === 1 ? "" : "s"}
                                                </span>
                                            </div>
                                            {cellShifts.length > 0 ? (
                                                <div className="space-y-2">
                                                    {cellShifts.map((shift) => (
                                                        <ShiftTileComponent
                                                            key={shift.id}
                                                            shift={shift}
                                                            onClick={() => setSelectedShiftId(shift.id)}
                                                        />
                                                    ))}
                                                </div>
                                            ) : (
                                                <button
                                                    type="button"
                                                    onClick={() => openCreateShiftForCell(activeMobileDayIndex, periodIndex)}
                                                    className="w-full px-3 py-3 rounded-lg border-2 border-dashed border-border-gray text-gray-500 text-xs font-semibold hover:border-teal hover:text-teal transition-base flex items-center justify-center gap-1.5"
                                                >
                                                    <Plus size={14} />
                                                    Add Shift
                                                </button>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>

                    {/* Desktop Grid */}
                    <div className="hidden md:block w-full min-w-[860px]">
                        <div className="grid grid-cols-7 gap-1.5 mb-1.5">
                            {DAYS.map((day, i) => (
                                <div key={day} className="text-center">
                                    <p className="text-xs font-bold text-navy uppercase">{day.slice(0, 3)}</p>
                                    <p className="text-[10px] text-gray-500">{dayDates[i]}</p>
                                </div>
                            ))}
                        </div>

                        {isLoadingShifts && (
                            <div className="flex justify-center py-10">
                                <Loader2 className="animate-spin text-teal" size={32} />
                            </div>
                        )}

                        {!isLoadingShifts &&
                            PERIODS.map((period, pi) => (
                                <div key={period} className="mb-2.5 last:mb-0">
                                    <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-1 pl-1">{period}</p>
                                    <div className="grid grid-cols-7 gap-1.5">
                                        {DAYS.map((_, di) => {
                                            const cellShifts = getShiftsForCell(di, pi);
                                            return (
                                                <div
                                                    key={`${di}-${pi}`}
                                                    className="min-h-[62px] bg-white border border-border-gray rounded-lg p-1.5 relative group hover:border-teal/30 transition-base"
                                                >
                                                    {cellShifts.length > 0 ? (
                                                        <div className="space-y-1">
                                                            {cellShifts.map((shift) => (
                                                                <ShiftTileComponent
                                                                    key={shift.id}
                                                                    shift={shift}
                                                                    onClick={() => setSelectedShiftId(shift.id)}
                                                                />
                                                            ))}
                                                        </div>
                                                    ) : (
                                                        <div
                                                            onClick={() => openCreateShiftForCell(di, pi)}
                                                            className="w-full h-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-base cursor-pointer"
                                                        >
                                                            <button className="w-8 h-8 rounded-lg border-2 border-dashed border-gray-300 flex items-center justify-center text-gray-400 hover:border-teal hover:text-teal transition-base">
                                                                <Plus size={16} />
                                                            </button>
                                                        </div>
                                                    )}
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            ))}
                    </div>
                </div>

                {/* Bottom Action Bar */}
                <div className="px-3 md:px-4 py-2.5 bg-white border-t border-border-gray flex flex-wrap items-center justify-between gap-2.5 flex-shrink-0 shadow-sm z-10 relative">
                    <Badge variant={isPublished ? "green" : "gray"}>{isPublished ? "Published" : "Draft"}</Badge>
                    <p className="text-sm text-gray-600 w-full sm:w-auto order-3 sm:order-none">
                        {shifts.length} total shifts scheduled
                    </p>
                    <div className="flex items-center gap-3 w-full sm:w-auto">
                        <button
                            onClick={handlePublish}
                            disabled={publishMutation.isPending || shifts.length === 0}
                            className={`w-full sm:w-auto px-5 py-2 text-sm font-bold rounded-lg transition-base disabled:opacity-50 ${isPublished
                                ? "bg-teal/10 text-teal border border-teal/20"
                                : "bg-teal text-white hover:bg-teal-dark shadow-md"
                                }`}
                        >
                            {publishMutation.isPending ? "Publishing..." : isPublished ? "Update Publication" : "Publish Schedule"}
                        </button>
                    </div>
                </div>
            </div>

            {/* Assignment Modal (S-M-02) overlay */}
            {selectedShiftId && (
                <AssignmentModal
                    shift={shifts.find((s) => s.id === selectedShiftId)!}
                    open={!!selectedShiftId}
                    onClose={() => setSelectedShiftId(null)}
                />
            )}

            {/* Create Shift Modal */}
            <CreateShiftModal
                open={isCreateModalOpen}
                onClose={() => setIsCreateModalOpen(false)}
                locationId={locationId}
                defaultDateStr={createDate}
                defaultPeriodIndex={createPeriodIndex}
            />

            <NotificationCentre
                open={isNotificationOpen}
                onClose={() => setIsNotificationOpen(false)}
            />
        </AppLayout>
    );
}
