import React, { useState, useEffect } from "react";
import { format, startOfWeek, addDays, parseISO, differenceInDays } from "date-fns";
import { ChevronLeft, ChevronRight, ChevronDown, Plus, AlertTriangle, X, Clock, MapPin, Loader2 } from "lucide-react";
import { AppLayout } from "../../components/NavBar";
import { Avatar } from "../../components/Avatar";
import { Badge } from "../../components/Badge";

import { useLocations, useShifts, useUsers, useAssignments, usePublishWeek, useOvertimeDashboard } from "../../lib/api/hooks";
import { ShiftResponse } from "../../lib/api/types";
import { AssignmentModal } from "./AssignmentModal";

/* ========== Helpers ========== */
const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const PERIODS = ["Morning", "Afternoon", "Night"];

function formatTime(t24: string) {
    if (!t24) return "";
    const [h, m] = t24.split(":").map(Number);
    const period = h >= 12 ? "pm" : "am";
    const h12 = h % 12 || 12;
    return `${h12}${m > 0 ? `:${m.toString().padStart(2, "0")}` : ""}${period}`;
}

const getShiftPeriod = (timeStr: string) => {
    const h = parseInt(timeStr.split(":")[0], 10);
    if (h < 12) return 0;
    if (h < 18) return 1; // 12pm - 5:59pm is Afternoon
    return 2; // 6pm+ is Night
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
    const [weekStart, setWeekStart] = useState<Date>(() => startOfWeek(new Date(), { weekStartsOn: 1 }));
    const [locationId, setLocationId] = useState<string>("");
    const [selectedShiftId, setSelectedShiftId] = useState<string | null>(null);

    const { data: locationsData } = useLocations();
    const locations = locationsData?.locations || [];

    // Auto-select first location
    useEffect(() => {
        if (!locationId && locations.length > 0) {
            setLocationId(locations[0].id);
        }
    }, [locations, locationId]);

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
    const currentLocation = locations.find((loc) => loc.id === locationId);

    const locationSelector = (
        <div className="flex items-center gap-4">
            <div className="relative group">
                <select
                    value={locationId}
                    onChange={(e) => setLocationId(e.target.value)}
                    className="appearance-none bg-white/10 hover:bg-white/20 text-sm font-medium text-white px-3 py-1.5 pl-8 pr-8 rounded-lg outline-none transition-base cursor-pointer"
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

            <div className="flex items-center gap-2 text-sm">
                <button onClick={handlePreviousWeek} className="p-1 rounded hover:bg-white/10 transition-base">
                    <ChevronLeft size={18} />
                </button>
                <span className="font-medium whitespace-nowrap min-w-[180px] text-center">{headerDateRange}</span>
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
        >
            <div className="flex flex-col h-full bg-gray-50/50">
                {/* Schedule Grid */}
                <div className="flex-1 overflow-auto p-4">
                    <div className="min-w-[900px]">
                        {/* Day headers */}
                        <div className="grid grid-cols-7 gap-2 mb-2">
                            {DAYS.map((day, i) => (
                                <div key={day} className="text-center">
                                    <p className="text-xs font-bold text-navy uppercase">{day.slice(0, 3)}</p>
                                    <p className="text-[11px] text-gray-500">{dayDates[i]}</p>
                                </div>
                            ))}
                        </div>

                        {/* Loading Overlay */}
                        {isLoadingShifts && (
                            <div className="flex justify-center py-10">
                                <Loader2 className="animate-spin text-teal" size={32} />
                            </div>
                        )}

                        {/* Grid rows */}
                        {!isLoadingShifts &&
                            PERIODS.map((period, pi) => (
                                <div key={period} className="mb-3">
                                    <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-1.5 pl-1">{period}</p>
                                    <div className="grid grid-cols-7 gap-2">
                                        {DAYS.map((_, di) => {
                                            const cellShifts = getShiftsForCell(di, pi);
                                            return (
                                                <div
                                                    key={`${di}-${pi}`}
                                                    className="min-h-[72px] bg-white border border-border-gray rounded-lg p-1.5 relative group hover:border-teal/30 transition-base"
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
                                                        <div className="w-full h-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-base cursor-pointer">
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
                <div className="px-6 py-3 bg-white border-t border-border-gray flex items-center justify-between flex-shrink-0 shadow-sm z-10 relative">
                    <Badge variant={isPublished ? "green" : "gray"}>{isPublished ? "Published" : "Draft"}</Badge>
                    <p className="text-sm text-gray-600">
                        {shifts.length} total shifts scheduled
                    </p>
                    <div className="flex items-center gap-3">
                        <button
                            onClick={handlePublish}
                            disabled={publishMutation.isPending || shifts.length === 0}
                            className={`px-5 py-2 text-sm font-bold rounded-lg transition-base disabled:opacity-50 ${isPublished
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
        </AppLayout>
    );
}
