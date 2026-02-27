import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueries } from '@tanstack/react-query';
import {
    ChevronLeft,
    ChevronRight,
    MapPin,
    Users,
    AlertTriangle,
    ArrowRight,
    AlertCircle,
} from 'lucide-react';
import { AppLayout } from '../../components/NavBar';
import { Badge } from '../../components/Badge';
import { useLocations, useOnDuty, useUsers } from '../../lib/api/hooks';
import { getUsers } from '../../lib/api/client';
import { Loader2 } from 'lucide-react';
import { format, startOfWeek, addDays } from 'date-fns';
import { Avatar } from '../../components/Avatar';

/* ========== Sub-Components ========== */

function OnDutySidebar() {
    const { data: onDutyData, isLoading } = useOnDuty();

    if (isLoading) {
        return (
            <div className="bg-white rounded-xl border border-border-gray shadow-sm p-8 flex flex-col items-center justify-center text-gray-400">
                <Loader2 size={24} className="animate-spin mb-2" />
                <p className="text-xs">Loading on-duty status...</p>
            </div>
        );
    }

    const locations = onDutyData?.locations || [];

    return (
        <div className="bg-white rounded-xl border border-border-gray shadow-sm overflow-hidden">
            <div className="p-4 border-b border-border-gray bg-gray-50 flex items-center justify-between">
                <h3 className="text-sm font-bold text-navy">Live On-Duty Staff</h3>
                <Badge variant="green">Live</Badge>
            </div>
            <div className="divide-y divide-border-gray max-h-[500px] overflow-y-auto">
                {locations.length === 0 && (
                    <div className="p-6 text-center">
                        <p className="text-xs text-gray-500">No active shifts across any location.</p>
                    </div>
                )}
                {locations.map((loc) => (
                    <div key={loc.location_id} className="p-4">
                        <div className="flex items-center justify-between mb-2">
                            <h4 className="text-xs font-bold text-navy truncate flex-1 mr-2">{loc.location_name}</h4>
                            <span className="text-[10px] text-gray-400 tabular-nums">
                                {new Date(loc.local_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                        </div>

                        {loc.on_duty_staff.length === 0 ? (
                            <p className="text-[10px] text-gray-400 italic">No staff on clock</p>
                        ) : (
                            <div className="space-y-2">
                                {loc.on_duty_staff.map((staff) => (
                                    <div key={staff.user_id} className="flex items-center gap-2">
                                        <Avatar name={staff.name} size="sm" color="bg-teal" />
                                        <div className="flex-1 min-w-0">
                                            <p className="text-[11px] font-medium text-navy truncate">{staff.name}</p>
                                            <p className="text-[9px] text-gray-500 uppercase tracking-wider">{staff.skill}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}

interface LocationCardProps {
    id: string;
    name: string;
    iana_timezone: string;
    staff_count: number;
}

function LocationCardComponent({ loc, onManageLocation }: { loc: LocationCardProps; onManageLocation: (locationId: string) => void }) {
    // Note: To get real assigned staff/unassigned shifts per location, we'd need a specific dashboard endpoint.
    // For now, we'll keep the visual layout but fetch the real name/timezone.
    return (
        <div className={`bg-white rounded-xl border border-border-gray shadow-sm p-5 border-l-4 border-l-success card-hover`}>
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
                <div>
                    <h3 className="text-base font-bold text-navy">{loc.name}</h3>
                    <p className="text-[10px] text-gray-500 font-mono uppercase tracking-tighter">{loc.iana_timezone}</p>
                </div>
                <Badge variant="green">Active</Badge>
            </div>

            {/* Details */}
            <div className="space-y-3 mb-4">
                <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Total Staff:</span>
                    <span className="font-bold text-navy">{loc.staff_count}</span>
                </div>

                <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Overtime Risk:</span>
                    <span className="text-success text-xs font-medium">Synced</span>
                </div>

                <div className="p-3 bg-gray-50 rounded-lg border border-border-gray/50">
                    <div className="flex items-center gap-2 text-[10px] text-gray-500 uppercase font-bold mb-1">
                        <AlertCircle size={10} /> Live Snapshot
                    </div>
                    <p className="text-xs text-navy font-medium">Full Coverage</p>
                </div>
            </div>

            {/* Quick link */}
            <button
                onClick={() => onManageLocation(loc.id)}
                className="w-full flex items-center justify-center gap-1.5 py-2 text-sm font-semibold text-admin-slate hover:text-navy border border-border-gray rounded-lg hover:bg-gray-50 transition-base"
            >
                Manage Location <ArrowRight size={14} />
            </button>
        </div>
    );
}

/* ========== Main Component ========== */

export function AdminOverview() {
    const navigate = useNavigate();
    const [weekStart, setWeekStart] = useState<Date>(() => startOfWeek(new Date(), { weekStartsOn: 1 }));
    const { data: locationsData, isLoading: isLoadingLocs } = useLocations();
    const { data: usersData } = useUsers();

    const headerDateRange = `Week of ${format(weekStart, "MMM d, yyyy")}`;

    const centerContent = (
        <div className="flex items-center gap-2 text-sm">
            <button
                onClick={() => setWeekStart(prev => addDays(prev, -7))}
                className="p-1 rounded hover:bg-white/10 transition-base"
            >
                <ChevronLeft size={18} />
            </button>
            <span className="font-medium">{headerDateRange}</span>
            <button
                onClick={() => setWeekStart(prev => addDays(prev, 7))}
                className="p-1 rounded hover:bg-white/10 transition-base"
            >
                <ChevronRight size={18} />
            </button>
        </div>
    );

    const locations = locationsData?.locations || [];
    const totalStaff = usersData?.users.filter(u => u.role === 'staff').length || 0;

    const staffCountQueries = useQueries({
        queries: locations.map((location) => ({
            queryKey: ['admin', 'location-staff-count', location.id],
            queryFn: () => getUsers(location.id),
            staleTime: 60_000,
        })),
    });

    const locationCards: LocationCardProps[] = locations.map((location, index) => {
        const response = staffCountQueries[index]?.data;
        const staffCount = response?.users.filter((user) => user.role === 'staff').length || 0;
        return {
            id: location.id,
            name: location.name,
            iana_timezone: location.iana_timezone,
            staff_count: staffCount,
        };
    });

    return (
        <AppLayout title="Admin Portal" role="admin" centerContent={centerContent} notificationCount={0}>
            <div className="p-6">
                {/* Page title */}
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h1 className="text-2xl font-bold text-navy">Global Operations Overview</h1>
                        <p className="text-sm text-gray-500 mt-1">Monitoring {locations.length} locations across all timezones.</p>
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                    {/* Location Cards - 2x2 grid */}
                    <div className="lg:col-span-3 grid grid-cols-1 md:grid-cols-2 gap-4">
                        {isLoadingLocs ? (
                            <div className="col-span-full py-20 flex flex-col items-center justify-center text-gray-400">
                                <Loader2 size={32} className="animate-spin mb-4" />
                                <p>Loading location metrics...</p>
                            </div>
                        ) : (
                            locationCards.map((loc) => (
                                <LocationCardComponent
                                    key={loc.id}
                                    loc={loc}
                                    onManageLocation={(locationId) => navigate(`/manager?location_id=${encodeURIComponent(locationId)}`)}
                                />
                            ))
                        )}
                        {locations.length === 0 && !isLoadingLocs && (
                            <div className="col-span-full p-12 bg-white rounded-xl border border-border-gray text-center text-gray-500">
                                No active locations found.
                            </div>
                        )}
                    </div>

                    {/* On Duty Sidebar */}
                    <div className="lg:col-span-1">
                        <OnDutySidebar />
                    </div>
                </div>

                {/* Bottom Summary */}
                <div className="mt-6 px-6 py-5 bg-gray-50 rounded-xl border border-border-gray flex items-center justify-between flex-wrap gap-6">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-navy/5 rounded-lg flex items-center justify-center text-navy">
                            <MapPin size={20} />
                        </div>
                        <div>
                            <p className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Total Locations</p>
                            <p className="text-xl font-bold text-navy">{locations.length}</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-teal/5 rounded-lg flex items-center justify-center text-teal">
                            <Users size={20} />
                        </div>
                        <div>
                            <p className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Active Staff</p>
                            <p className="text-xl font-bold text-navy">{totalStaff}</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-amber-warn/5 rounded-lg flex items-center justify-center text-amber-warn">
                            <AlertTriangle size={20} />
                        </div>
                        <div>
                            <p className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">System Alerts</p>
                            <p className="text-xl font-bold text-navy">--</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-4 border-l border-border-gray pl-6">
                        <div className="text-right">
                            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Est. Weekly Budget</p>
                            <p className="text-lg font-bold text-navy truncate max-w-[120px]">Calculated in Reports</p>
                        </div>
                        <button
                            onClick={() => navigate('/admin/audit')}
                            className="p-2 bg-navy text-white rounded-lg hover:bg-navy-light transition-base shadow-sm"
                            title="Open audit log"
                        >
                            <ArrowRight size={18} />
                        </button>
                    </div>
                </div>
            </div>
        </AppLayout>
    );
}
