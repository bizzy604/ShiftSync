import React, { useState } from 'react';
import {
    ChevronLeft,
    ChevronRight,
    ChevronDown,
    Plus,
    AlertTriangle,
    Check,
    X,
    Clock,
    MapPin,
} from 'lucide-react';
import { AppLayout } from '../../components/NavBar';
import { Avatar } from '../../components/Avatar';
import { Badge } from '../../components/Badge';

/* ========== Mock Data ========== */
interface StaffMember {
    id: string;
    name: string;
    initials: string;
    status: 'available' | 'near-overtime' | 'unavailable';
    hours: number;
    maxHours: number;
    skills: string[];
}

const mockStaff: StaffMember[] = [
    { id: '1', name: 'Carlos M.', initials: 'CM', status: 'near-overtime', hours: 38, maxHours: 40, skills: ['Bartender'] },
    { id: '2', name: 'Maria L.', initials: 'ML', status: 'available', hours: 22, maxHours: 40, skills: ['Bartender', 'Server'] },
    { id: '3', name: 'Jordan T.', initials: 'JT', status: 'available', hours: 24, maxHours: 40, skills: ['Server'] },
    { id: '4', name: 'Sam K.', initials: 'SK', status: 'available', hours: 28, maxHours: 40, skills: ['Server'] },
    { id: '5', name: 'Priya N.', initials: 'PN', status: 'near-overtime', hours: 35, maxHours: 40, skills: ['Server'] },
    { id: '6', name: 'Alex R.', initials: 'AR', status: 'unavailable', hours: 16, maxHours: 40, skills: ['Bartender'] },
];

interface ShiftTile {
    id: string;
    day: number;
    period: number;
    skill: string;
    staffName?: string;
    time: string;
    assigned: boolean;
}

const mockShifts: ShiftTile[] = [
    { id: 's1', day: 0, period: 1, skill: 'Bartender', staffName: 'Carlos M.', time: '2pm-10pm', assigned: true },
    { id: 's2', day: 2, period: 0, skill: 'Bartender', time: '6am-2pm', assigned: false },
    { id: 's3', day: 4, period: 2, skill: 'Server', staffName: 'Maria L.', time: '10pm-6am', assigned: true },
    { id: 's4', day: 1, period: 0, skill: 'Server', staffName: 'Jordan T.', time: '6am-2pm', assigned: true },
    { id: 's5', day: 3, period: 1, skill: 'Server', staffName: 'Sam K.', time: '2pm-10pm', assigned: true },
];

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const DAY_DATES = ['Aug 11', 'Aug 12', 'Aug 13', 'Aug 14', 'Aug 15', 'Aug 16', 'Aug 17'];
const PERIODS = ['Morning (6am-2pm)', 'Afternoon (2pm-10pm)', 'Night (10pm-6am)'];

/* ========== Sub-Components ========== */

function StaffSidebar() {
    const [hoveredStaff, setHoveredStaff] = useState<string | null>(null);

    return (
        <div className="p-4">
            <h3 className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-3">Staff</h3>
            <div className="space-y-1.5">
                {mockStaff.map((s) => (
                    <div
                        key={s.id}
                        className="relative flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-white cursor-pointer transition-base group"
                        onMouseEnter={() => setHoveredStaff(s.id)}
                        onMouseLeave={() => setHoveredStaff(null)}
                    >
                        <Avatar name={s.name} size="sm" color={s.status === 'unavailable' ? 'bg-gray-400' : 'bg-navy'} />
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-navy truncate">{s.name}</p>
                        </div>
                        <span
                            className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${s.status === 'available'
                                    ? 'bg-success-light'
                                    : s.status === 'near-overtime'
                                        ? 'bg-amber-warn'
                                        : 'bg-danger'
                                }`}
                        />

                        {/* What-If Preview Tooltip */}
                        {hoveredStaff === s.id && (
                            <div className="absolute left-full ml-2 top-0 bg-navy text-white text-xs rounded-lg p-3 w-52 shadow-xl z-30 animate-fade-in">
                                <p className="font-semibold mb-1">{s.name}</p>
                                <p className="text-white/70">Current: {s.hours}h / {s.maxHours}h</p>
                                <div className="w-full bg-white/20 rounded-full h-1.5 mt-1.5 mb-2">
                                    <div
                                        className={`h-1.5 rounded-full ${s.hours >= 40 ? 'bg-danger' : s.hours >= 35 ? 'bg-amber-warn' : 'bg-success-light'}`}
                                        style={{ width: `${(s.hours / s.maxHours) * 100}%` }}
                                    />
                                </div>
                                {s.hours >= 35 && (
                                    <p className="text-amber-warn-light flex items-center gap-1">
                                        <AlertTriangle size={12} /> {s.hours >= 40 ? 'Over 40h limit' : 'Near 40h limit'}
                                    </p>
                                )}
                            </div>
                        )}
                    </div>
                ))}
            </div>

            {/* Weekly Hours */}
            <div className="mt-6">
                <h3 className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-3">Weekly Hours</h3>
                <div className="space-y-2">
                    {mockStaff.map((s) => (
                        <div key={s.id} className="flex items-center gap-2">
                            <span className="text-[11px] text-gray-600 w-16 truncate">{s.name}</span>
                            <div className="flex-1 bg-gray-200 rounded-full h-2">
                                <div
                                    className={`h-2 rounded-full transition-all ${s.hours >= 40 ? 'bg-danger' : s.hours >= 35 ? 'bg-amber-warn' : 'bg-teal'
                                        }`}
                                    style={{ width: `${Math.min((s.hours / s.maxHours) * 100, 100)}%` }}
                                />
                            </div>
                            <span className="text-[11px] text-gray-500 w-12 text-right">{s.hours}h</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

function ShiftTileComponent({ shift, onClick }: { shift: ShiftTile; onClick?: () => void }) {
    if (!shift.assigned) {
        return (
            <button
                onClick={onClick}
                className="w-full px-2 py-1.5 rounded-lg border-2 border-dashed border-amber-warn/50 bg-amber-warn-50 text-amber-warn text-xs font-medium flex items-center gap-1.5 hover:border-amber-warn hover:shadow-md transition-base"
            >
                <AlertTriangle size={12} />
                <span className="truncate">⚠ Unassigned · {shift.skill}</span>
            </button>
        );
    }

    return (
        <div className="w-full px-2.5 py-1.5 rounded-lg bg-teal text-white text-xs font-medium flex items-center gap-1.5 shadow-sm hover:shadow-md hover:bg-teal-dark transition-base cursor-pointer">
            <Clock size={11} className="flex-shrink-0" />
            <span className="truncate">{shift.skill} · {shift.time} · {shift.staffName}</span>
        </div>
    );
}

/* ========== Assign Popover ========== */

function AssignPopover({ onClose }: { onClose: () => void }) {
    const qualifiedStaff = mockStaff.filter((s) => s.skills.includes('Bartender') && s.status !== 'unavailable');

    return (
        <div className="absolute top-full left-0 mt-2 w-72 bg-white rounded-xl shadow-2xl border border-border-gray z-40 animate-fade-in">
            <div className="p-4 border-b border-border-gray">
                <h4 className="text-sm font-bold text-navy">Assign Staff</h4>
                <p className="text-xs text-gray-500 mt-0.5">Wednesday Morning · Bartender · 6am-2pm</p>
            </div>
            <div className="p-2">
                {qualifiedStaff.map((s) => (
                    <div
                        key={s.id}
                        className="flex items-center justify-between px-3 py-2.5 rounded-lg hover:bg-gray-50 transition-base"
                    >
                        <div className="flex items-center gap-2.5">
                            <Avatar name={s.name} size="sm" />
                            <div>
                                <p className="text-sm font-medium text-navy">{s.name}</p>
                                <p className="text-xs text-gray-500">{s.hours}h / {s.maxHours}h</p>
                            </div>
                        </div>
                        <button className="px-3 py-1 text-xs font-semibold bg-teal text-white rounded-lg hover:bg-teal-dark transition-base">
                            Assign
                        </button>
                    </div>
                ))}
            </div>
            <div className="px-4 py-3 border-t border-border-gray">
                <button onClick={onClose} className="text-xs text-gray-500 hover:text-navy transition-base">
                    Cancel
                </button>
            </div>
        </div>
    );
}

/* ========== Main Component ========== */

export function ScheduleBuilder() {
    const [isPublished, setIsPublished] = useState(false);
    const [showPopover, setShowPopover] = useState(false);
    const [showConstraintError, setShowConstraintError] = useState(false);

    const getShiftsForCell = (day: number, period: number) =>
        mockShifts.filter((s) => s.day === day && s.period === period);

    const assignedCount = mockShifts.filter((s) => s.assigned).length;
    const unassignedCount = mockShifts.filter((s) => !s.assigned).length;

    const locationSelector = (
        <div className="flex items-center gap-4">
            <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-sm font-medium transition-base">
                <MapPin size={14} />
                Ocean Ave Location
                <ChevronDown size={14} />
            </button>
            <div className="flex items-center gap-2 text-sm">
                <button className="p-1 rounded hover:bg-white/10 transition-base">
                    <ChevronLeft size={18} />
                </button>
                <span className="font-medium">Mon Aug 11 – Sun Aug 17, 2025</span>
                <button className="p-1 rounded hover:bg-white/10 transition-base">
                    <ChevronRight size={18} />
                </button>
            </div>
        </div>
    );

    return (
        <AppLayout
            title="Schedule Builder"
            role="manager"
            centerContent={locationSelector}
            notificationCount={3}
            sidebar={<StaffSidebar />}
        >
            <div className="flex flex-col h-full">
                {/* Schedule Grid */}
                <div className="flex-1 overflow-auto p-4">
                    <div className="min-w-[900px]">
                        {/* Day headers */}
                        <div className="grid grid-cols-7 gap-2 mb-2">
                            {DAYS.map((day, i) => (
                                <div key={day} className="text-center">
                                    <p className="text-xs font-bold text-navy uppercase">{day.slice(0, 3)}</p>
                                    <p className="text-[11px] text-gray-500">{DAY_DATES[i]}</p>
                                </div>
                            ))}
                        </div>

                        {/* Grid rows */}
                        {PERIODS.map((period, pi) => (
                            <div key={period} className="mb-3">
                                <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-1.5 pl-1">
                                    {period}
                                </p>
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
                                                            <div key={shift.id} className="relative">
                                                                <ShiftTileComponent
                                                                    shift={shift}
                                                                    onClick={
                                                                        !shift.assigned
                                                                            ? () => setShowPopover(!showPopover)
                                                                            : undefined
                                                                    }
                                                                />
                                                                {!shift.assigned && showPopover && (
                                                                    <AssignPopover onClose={() => setShowPopover(false)} />
                                                                )}
                                                            </div>
                                                        ))}
                                                    </div>
                                                ) : (
                                                    <div className="w-full h-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-base">
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

                {/* Constraint Error Panel */}
                {showConstraintError && (
                    <div className="mx-4 mb-2 px-4 py-3 bg-danger-50 border border-danger/20 rounded-lg flex items-start gap-3 animate-fade-in">
                        <AlertTriangle size={18} className="text-danger mt-0.5 flex-shrink-0" />
                        <div className="flex-1">
                            <p className="text-sm font-semibold text-danger">
                                Rest period violation: Only 8h gap. Carlos M.'s previous shift ends at 11pm. Minimum required: 10h.
                            </p>
                            <div className="mt-2 space-y-1">
                                <p className="text-xs text-gray-600">Suggested alternatives:</p>
                                <p className="text-xs text-gray-600">• Maria L. — available, 22h this week</p>
                                <p className="text-xs text-gray-600">• Jordan T. — available, 24h this week</p>
                            </div>
                        </div>
                        <button
                            onClick={() => setShowConstraintError(false)}
                            className="text-gray-400 hover:text-gray-600 transition-base"
                        >
                            <X size={16} />
                        </button>
                    </div>
                )}

                {/* Bottom Action Bar */}
                <div className="px-6 py-3 bg-white border-t border-border-gray flex items-center justify-between flex-shrink-0">
                    <Badge variant={isPublished ? 'green' : 'gray'}>
                        {isPublished ? 'Published' : 'Draft'}
                    </Badge>
                    <p className="text-sm text-gray-600">
                        <span className="font-semibold">{assignedCount} shifts assigned</span> · {unassignedCount} unassigned · Est. labor cost: <span className="font-semibold">$1,240</span>
                    </p>
                    <div className="flex items-center gap-3">
                        <button className="px-4 py-2 text-sm font-medium border border-border-gray rounded-lg text-gray-700 hover:bg-gray-50 transition-base">
                            Save Draft
                        </button>
                        <button
                            onClick={() => {
                                setIsPublished(!isPublished);
                                setShowConstraintError(!isPublished ? false : true);
                            }}
                            className={`px-5 py-2 text-sm font-bold rounded-lg transition-base ${isPublished
                                    ? 'bg-teal/10 text-teal border border-teal/20'
                                    : 'bg-teal text-white hover:bg-teal-dark shadow-md'
                                }`}
                        >
                            {isPublished ? 'Edit Schedule' : 'Publish Schedule'}
                        </button>
                    </div>
                </div>
            </div>
        </AppLayout>
    );
}
