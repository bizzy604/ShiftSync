import React, { useState } from 'react';
import {
    ChevronLeft,
    ChevronRight,
    MapPin,
    Users,
    AlertTriangle,
    DollarSign,
    ArrowRight,
    ChevronDown,
    ExternalLink,
    AlertCircle,
} from 'lucide-react';
import { AppLayout } from '../../components/NavBar';
import { Badge } from '../../components/Badge';

/* ========== Mock Data ========== */

interface LocationCard {
    id: string;
    name: string;
    city: string;
    timezone: string;
    manager: string;
    status: 'published' | 'draft';
    assignedStaff: number;
    requiredStaff: number;
    unassignedShifts: number;
    overtimeRisk: string | null;
    laborEstimate: string;
}

const mockLocations: LocationCard[] = [
    {
        id: '1',
        name: 'Ocean Ave',
        city: 'Los Angeles, PT',
        timezone: 'America/Los_Angeles',
        manager: 'Jordan K.',
        status: 'published',
        assignedStaff: 8,
        requiredStaff: 8,
        unassignedShifts: 0,
        overtimeRisk: '1 staff near limit',
        laborEstimate: '$4,820',
    },
    {
        id: '2',
        name: 'Beach Blvd',
        city: 'Los Angeles, PT',
        timezone: 'America/Los_Angeles',
        manager: 'Sam R.',
        status: 'draft',
        assignedStaff: 5,
        requiredStaff: 7,
        unassignedShifts: 2,
        overtimeRisk: null,
        laborEstimate: '$3,100 (draft)',
    },
    {
        id: '3',
        name: 'Miami Beach',
        city: 'Florida, ET',
        timezone: 'America/New_York',
        manager: 'Alex P.',
        status: 'published',
        assignedStaff: 9,
        requiredStaff: 9,
        unassignedShifts: 0,
        overtimeRisk: null,
        laborEstimate: '$5,200',
    },
    {
        id: '4',
        name: 'Downtown Miami',
        city: 'Florida, ET',
        timezone: 'America/New_York',
        manager: 'Dana W.',
        status: 'published',
        assignedStaff: 7,
        requiredStaff: 8,
        unassignedShifts: 1,
        overtimeRisk: '2 staff over 40h',
        laborEstimate: '$4,990',
    },
];

interface AlertItem {
    id: string;
    type: 'red' | 'amber' | 'blue';
    location: string;
    message: string;
}

const mockAlerts: AlertItem[] = [
    { id: '1', type: 'red', location: 'Downtown Miami', message: '2 staff members over 40h overtime' },
    { id: '2', type: 'amber', location: 'Beach Blvd', message: '2 unassigned shifts this week' },
    { id: '3', type: 'amber', location: 'Downtown Miami', message: '1 unassigned shift — Bartender' },
    { id: '4', type: 'blue', location: 'Ocean Ave', message: '1 pending swap approval' },
];

/* ========== Sub-Components ========== */

function LocationCardComponent({ loc }: { loc: LocationCard }) {
    const fillPercent = (loc.assignedStaff / loc.requiredStaff) * 100;
    const barColor = fillPercent >= 100 ? 'bg-success-light' : fillPercent >= 80 ? 'bg-amber-warn' : 'bg-danger';
    const borderColor = loc.status === 'published' ? 'border-l-success' : loc.unassignedShifts > 0 ? 'border-l-amber-warn' : 'border-l-gray-300';

    return (
        <div className={`bg-white rounded-xl border border-border-gray shadow-sm p-5 border-l-4 ${borderColor} card-hover`}>
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
                <div>
                    <h3 className="text-base font-bold text-navy">{loc.name}</h3>
                    <p className="text-xs text-gray-500">{loc.city}</p>
                </div>
                <Badge variant={loc.status === 'published' ? 'green' : 'gray'}>
                    {loc.status === 'published' ? 'Published' : 'Draft'}
                </Badge>
            </div>

            {/* Details */}
            <div className="space-y-2.5 mb-4">
                <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Manager:</span>
                    <span className="font-medium text-navy">{loc.manager}</span>
                </div>

                <div>
                    <div className="flex items-center justify-between text-sm mb-1">
                        <span className="text-gray-600">Staff:</span>
                        <span className="font-medium text-navy">
                            {loc.assignedStaff} / {loc.requiredStaff}
                        </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                        <div className={`h-2 rounded-full ${barColor} transition-all`} style={{ width: `${Math.min(fillPercent, 100)}%` }} />
                    </div>
                </div>

                <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Unassigned:</span>
                    {loc.unassignedShifts > 0 ? (
                        <Badge variant="red">{loc.unassignedShifts}</Badge>
                    ) : (
                        <span className="text-success font-medium">0</span>
                    )}
                </div>

                <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Overtime risk:</span>
                    {loc.overtimeRisk ? (
                        <span className="flex items-center gap-1 text-xs font-medium text-amber-warn">
                            <AlertTriangle size={12} /> {loc.overtimeRisk}
                        </span>
                    ) : (
                        <span className="text-success text-xs font-medium">None</span>
                    )}
                </div>

                <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Labor est.:</span>
                    <span className="font-bold text-navy">{loc.laborEstimate}</span>
                </div>
            </div>

            {/* Quick link */}
            <button className="w-full flex items-center justify-center gap-1.5 py-2 text-sm font-semibold text-admin-slate hover:text-navy border border-border-gray rounded-lg hover:bg-gray-50 transition-base">
                View Schedule <ArrowRight size={14} />
            </button>
        </div>
    );
}

function AlertsSidebar({ alerts }: { alerts: AlertItem[] }) {
    const iconMap = {
        red: <AlertCircle size={14} className="text-danger" />,
        amber: <AlertTriangle size={14} className="text-amber-warn" />,
        blue: <ExternalLink size={14} className="text-blue-600" />,
    };

    return (
        <div className="bg-white rounded-xl border border-border-gray shadow-sm p-5">
            <h3 className="text-sm font-bold text-navy mb-4">Alerts & Issues</h3>
            <div className="space-y-3">
                {alerts.map((a) => (
                    <div key={a.id} className="flex items-start gap-2.5">
                        <div className="mt-0.5 flex-shrink-0">{iconMap[a.type]}</div>
                        <div className="flex-1 min-w-0">
                            <p className="text-xs font-semibold text-gray-700">{a.location}</p>
                            <p className="text-xs text-gray-500">{a.message}</p>
                        </div>
                        <button className="text-[10px] text-admin-slate font-semibold hover:underline flex-shrink-0">
                            View
                        </button>
                    </div>
                ))}
            </div>
        </div>
    );
}

/* ========== Main Component ========== */

export function AdminOverview() {
    const centerContent = (
        <div className="flex items-center gap-2 text-sm">
            <button className="p-1 rounded hover:bg-white/10 transition-base">
                <ChevronLeft size={18} />
            </button>
            <span className="font-medium">Week of Aug 11, 2025</span>
            <button className="p-1 rounded hover:bg-white/10 transition-base">
                <ChevronRight size={18} />
            </button>
        </div>
    );

    const totalLabor = '$18,110';
    const issueCount = 3;
    const totalStaff = 32;

    return (
        <AppLayout title="Admin Portal" role="admin" centerContent={centerContent} notificationCount={2}>
            <div className="p-6">
                {/* Page title */}
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h1 className="text-2xl font-bold text-navy">All Locations — Week Overview</h1>
                    </div>
                    <div className="flex items-center gap-3">
                        <select className="px-3 py-2 rounded-lg border border-border-gray text-sm text-navy bg-white focus:outline-none focus:ring-2 focus:ring-admin-slate/40">
                            <option>All Locations</option>
                        </select>
                        <select className="px-3 py-2 rounded-lg border border-border-gray text-sm text-navy bg-white focus:outline-none focus:ring-2 focus:ring-admin-slate/40">
                            <option>This Week</option>
                        </select>
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                    {/* Location Cards - 2x2 grid */}
                    <div className="lg:col-span-3 grid grid-cols-1 md:grid-cols-2 gap-4">
                        {mockLocations.map((loc) => (
                            <LocationCardComponent key={loc.id} loc={loc} />
                        ))}
                    </div>

                    {/* Alerts Sidebar */}
                    <div className="lg:col-span-1">
                        <AlertsSidebar alerts={mockAlerts} />
                    </div>
                </div>

                {/* Bottom Summary */}
                <div className="mt-6 px-6 py-4 bg-gray-50 rounded-xl border border-border-gray flex items-center justify-between flex-wrap gap-4">
                    <div className="flex items-center gap-2">
                        <DollarSign size={16} className="text-admin-slate" />
                        <span className="text-sm text-gray-700">
                            Total weekly labor estimate: <strong className="text-navy">{totalLabor}</strong>
                        </span>
                    </div>
                    <div className="flex items-center gap-2">
                        <AlertTriangle size={16} className="text-amber-warn" />
                        <span className="text-sm text-gray-700">
                            Locations with unresolved issues: <strong className="text-navy">{issueCount}</strong>
                        </span>
                    </div>
                    <div className="flex items-center gap-2">
                        <Users size={16} className="text-admin-slate" />
                        <span className="text-sm text-gray-700">
                            Staff across all locations: <strong className="text-navy">{totalStaff}</strong>
                        </span>
                    </div>
                </div>
            </div>
        </AppLayout>
    );
}
