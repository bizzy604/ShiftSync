import React, { useState } from 'react';
import { ChevronLeft, ChevronRight, AlertTriangle, TrendingUp, DollarSign, BarChart3 } from 'lucide-react';
import { AppLayout } from '../../components/NavBar';
import { Avatar } from '../../components/Avatar';
import { Badge } from '../../components/Badge';

/* ========== Mock Data ========== */

interface StaffHours {
    name: string;
    hours: number;
    maxHours: number;
    status: 'green' | 'amber' | 'red';
    regularShifts?: number;
    premiumShifts?: number;
    fairnessScore?: number;
}

const mockStaffHours: StaffHours[] = [
    { name: 'Carlos M.', hours: 38, maxHours: 40, status: 'amber', regularShifts: 3, premiumShifts: 2, fairnessScore: 85 },
    { name: 'Maria L.', hours: 42, maxHours: 40, status: 'red', regularShifts: 4, premiumShifts: 1, fairnessScore: 62 },
    { name: 'Jordan T.', hours: 24, maxHours: 40, status: 'green', regularShifts: 2, premiumShifts: 1, fairnessScore: 78 },
    { name: 'Sam K.', hours: 28, maxHours: 40, status: 'green', regularShifts: 3, premiumShifts: 0, fairnessScore: 45 },
    { name: 'Priya N.', hours: 35, maxHours: 40, status: 'amber', regularShifts: 3, premiumShifts: 2, fairnessScore: 90 },
    { name: 'Alex R.', hours: 16, maxHours: 40, status: 'green', regularShifts: 1, premiumShifts: 1, fairnessScore: 70 },
];

/* ========== Sub-Components ========== */

function HoursBarChart({ staff }: { staff: StaffHours[] }) {
    const maxDisplayHours = 45;

    return (
        <div className="bg-white rounded-xl border border-border-gray p-5">
            <h3 className="text-sm font-bold text-navy mb-1">Weekly Hours Projection</h3>
            <p className="text-xs text-gray-500 mb-5">Projected hours for current schedule draft</p>

            <div className="relative">
                {/* Threshold lines */}
                <div className="absolute top-0 bottom-8 flex flex-col justify-between pointer-events-none" style={{ left: `${(35 / maxDisplayHours) * 100}%` }}>
                    <div className="border-l-2 border-dashed border-amber-warn/50 h-full" />
                </div>
                <div className="absolute top-0 bottom-8 flex flex-col justify-between pointer-events-none" style={{ left: `${(40 / maxDisplayHours) * 100}%` }}>
                    <div className="border-l-2 border-danger/50 h-full" />
                </div>

                {/* Bars */}
                <div className="space-y-3">
                    {staff.map((s) => {
                        const barColor =
                            s.status === 'red' ? 'bg-danger' : s.status === 'amber' ? 'bg-amber-warn' : 'bg-teal';
                        const width = Math.min((s.hours / maxDisplayHours) * 100, 100);

                        return (
                            <div key={s.name} className="flex items-center gap-3">
                                <span className="text-sm text-gray-700 w-20 truncate font-medium">{s.name}</span>
                                <div className="flex-1 bg-gray-100 rounded-full h-6 relative overflow-hidden">
                                    <div
                                        className={`h-6 rounded-full ${barColor} transition-all duration-500 flex items-center justify-end pr-2`}
                                        style={{ width: `${width}%` }}
                                    >
                                        <span className="text-[10px] font-bold text-white">{s.hours}h</span>
                                    </div>
                                </div>
                                <div className="w-28 flex-shrink-0">
                                    {s.status === 'red' && <Badge variant="red">Over 40h</Badge>}
                                    {s.status === 'amber' && <Badge variant="amber">⚠ Near limit</Badge>}
                                </div>
                            </div>
                        );
                    })}
                </div>

                {/* Legend */}
                <div className="flex items-center gap-4 mt-4 pt-3 border-t border-border-gray text-[10px] text-gray-500">
                    <span className="flex items-center gap-1">
                        <span className="w-4 border-t-2 border-dashed border-amber-warn" /> 35h warning
                    </span>
                    <span className="flex items-center gap-1">
                        <span className="w-4 border-t-2 border-danger" /> 40h limit
                    </span>
                </div>
            </div>
        </div>
    );
}

function OvertimeAlertCard() {
    return (
        <div className="bg-danger rounded-xl p-5 text-white">
            <div className="flex items-center gap-2 mb-3">
                <AlertTriangle size={18} />
                <h3 className="font-bold">Overtime Alert</h3>
            </div>
            <p className="text-sm text-white/90 mb-2">
                1 staff member projected over 40 hours this week
            </p>
            <div className="flex items-center gap-2 mb-4">
                <Avatar name="Maria L." size="sm" color="bg-white/20" />
                <div>
                    <p className="text-sm font-semibold">Maria L.</p>
                    <p className="text-xs text-white/70">42h projected · 2h overtime</p>
                </div>
            </div>
            <button className="px-4 py-2 bg-white text-danger font-semibold text-sm rounded-lg hover:bg-white/90 transition-base">
                View & Fix
            </button>
        </div>
    );
}

function CostEstimateCard() {
    return (
        <div className="bg-white rounded-xl border border-border-gray p-5 border-t-4 border-t-teal">
            <div className="flex items-center gap-2 mb-3">
                <DollarSign size={18} className="text-teal" />
                <h3 className="font-bold text-navy">Cost Estimate</h3>
            </div>
            <div className="space-y-2">
                <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Estimated weekly labor:</span>
                    <span className="text-lg font-bold text-navy">$4,820</span>
                </div>
                <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Overtime premium:</span>
                    <span className="text-sm font-semibold text-danger">+$186 (Maria L.)</span>
                </div>
            </div>
            <p className="text-xs text-gray-400 mt-3">Based on hourly rates × scheduled hours</p>
        </div>
    );
}

function FairnessReport({ staff }: { staff: StaffHours[] }) {
    const maxPremium = Math.max(...staff.map((s) => s.premiumShifts ?? 0));
    const fairShareTarget = 1.5;

    return (
        <div className="space-y-6">
            {/* Premium Shift Distribution chart */}
            <div className="bg-white rounded-xl border border-border-gray p-5">
                <h3 className="text-sm font-bold text-navy mb-1">Premium Shift Distribution</h3>
                <p className="text-xs text-gray-500 mb-5">Fri/Sat 5pm+ shifts per staff member</p>

                <div className="space-y-3">
                    {staff.map((s) => {
                        const premiumCount = s.premiumShifts ?? 0;
                        const width = maxPremium > 0 ? (premiumCount / (maxPremium + 1)) * 100 : 0;

                        return (
                            <div key={s.name} className="flex items-center gap-3">
                                <span className="text-sm text-gray-700 w-20 truncate font-medium">{s.name}</span>
                                <div className="flex-1 bg-gray-100 rounded-full h-5 relative">
                                    <div
                                        className="h-5 rounded-full bg-staff-purple transition-all duration-500 flex items-center justify-end pr-2"
                                        style={{ width: `${width}%` }}
                                    >
                                        {premiumCount > 0 && (
                                            <span className="text-[10px] font-bold text-white">{premiumCount}</span>
                                        )}
                                    </div>
                                    {/* Fair share line */}
                                    <div
                                        className="absolute top-0 bottom-0 border-l-2 border-dashed border-teal/50"
                                        style={{ left: `${(fairShareTarget / (maxPremium + 1)) * 100}%` }}
                                    />
                                </div>
                            </div>
                        );
                    })}
                </div>

                <div className="flex items-center gap-2 mt-3 pt-2 border-t border-border-gray text-[10px] text-gray-500">
                    <span className="w-4 border-t-2 border-dashed border-teal" /> Fair share target
                </div>
            </div>

            {/* Fairness Table */}
            <div className="bg-white rounded-xl border border-border-gray overflow-hidden">
                <table className="w-full">
                    <thead>
                        <tr className="bg-gray-50 border-b border-border-gray">
                            <th className="px-5 py-3 text-left text-xs font-bold text-gray-500 uppercase">Staff Name</th>
                            <th className="px-5 py-3 text-center text-xs font-bold text-gray-500 uppercase">Regular Shifts</th>
                            <th className="px-5 py-3 text-center text-xs font-bold text-gray-500 uppercase">Premium Shifts</th>
                            <th className="px-5 py-3 text-center text-xs font-bold text-gray-500 uppercase">Fairness Score</th>
                        </tr>
                    </thead>
                    <tbody>
                        {staff.map((s) => (
                            <tr key={s.name} className="border-b border-border-gray hover:bg-gray-50 transition-base">
                                <td className="px-5 py-3">
                                    <div className="flex items-center gap-2">
                                        <Avatar name={s.name} size="sm" />
                                        <span className="text-sm font-medium text-navy">{s.name}</span>
                                    </div>
                                </td>
                                <td className="px-5 py-3 text-center text-sm text-gray-700">{s.regularShifts}</td>
                                <td className="px-5 py-3 text-center text-sm text-gray-700">{s.premiumShifts}</td>
                                <td className="px-5 py-3 text-center">
                                    <div className="flex items-center justify-center gap-2">
                                        <div className="w-16 bg-gray-200 rounded-full h-2">
                                            <div
                                                className={`h-2 rounded-full ${(s.fairnessScore ?? 0) >= 80
                                                        ? 'bg-success-light'
                                                        : (s.fairnessScore ?? 0) >= 60
                                                            ? 'bg-amber-warn'
                                                            : 'bg-danger'
                                                    }`}
                                                style={{ width: `${s.fairnessScore}%` }}
                                            />
                                        </div>
                                        <span className="text-xs font-semibold text-gray-600">{s.fairnessScore}%</span>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

/* ========== Main Component ========== */

type TabType = 'overtime' | 'fairness';

export function OvertimeFairness() {
    const [activeTab, setActiveTab] = useState<TabType>('overtime');

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

    return (
        <AppLayout title="Analytics" role="manager" centerContent={centerContent} notificationCount={1}>
            <div className="p-6 max-w-6xl mx-auto">
                {/* Header */}
                <div className="mb-6">
                    <h1 className="text-2xl font-bold text-navy">Overtime & Fairness — Ocean Ave Location</h1>
                </div>

                {/* Tabs */}
                <div className="flex gap-0 border-b border-border-gray mb-6">
                    <button
                        onClick={() => setActiveTab('overtime')}
                        className={`px-5 py-3 text-sm font-medium border-b-2 transition-base ${activeTab === 'overtime'
                                ? 'border-teal text-teal'
                                : 'border-transparent text-gray-500 hover:text-navy'
                            }`}
                    >
                        Overtime Watch
                    </button>
                    <button
                        onClick={() => setActiveTab('fairness')}
                        className={`px-5 py-3 text-sm font-medium border-b-2 transition-base ${activeTab === 'fairness'
                                ? 'border-teal text-teal'
                                : 'border-transparent text-gray-500 hover:text-navy'
                            }`}
                    >
                        Fairness Report
                    </button>
                </div>

                {/* Content */}
                {activeTab === 'overtime' ? (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        <div className="lg:col-span-2">
                            <HoursBarChart staff={mockStaffHours} />
                        </div>
                        <div className="space-y-4">
                            <OvertimeAlertCard />
                            <CostEstimateCard />
                        </div>
                    </div>
                ) : (
                    <FairnessReport staff={mockStaffHours} />
                )}
            </div>
        </AppLayout>
    );
}
