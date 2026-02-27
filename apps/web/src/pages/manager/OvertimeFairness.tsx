import React, { useState } from 'react';
import { ChevronLeft, ChevronRight, AlertTriangle, TrendingUp, DollarSign, BarChart3, Loader2, CheckCircle } from 'lucide-react';
import { format, startOfWeek, addDays, subDays, parseISO } from 'date-fns';

import { AppLayout } from '../../components/NavBar';
import { Avatar } from '../../components/Avatar';
import { Badge } from '../../components/Badge';
import { NotificationCentre } from '../staff/NotificationCentre';

import { useNotifications, useOvertimeDashboard, useFairnessReport, useLocations } from '../../lib/api/hooks';
import { OvertimeStaffRow, FairnessStaffRow } from '../../lib/api/types';

/* ========== Sub-Components ========== */

function HoursBarChart({ staff }: { staff: OvertimeStaffRow[] }) {
    const maxDisplayHours = Math.max(45, ...staff.map(s => s.projected_weekly_hours + 5));

    return (
        <div className="bg-white rounded-xl border border-border-gray p-5 h-full">
            <h3 className="text-sm font-bold text-navy mb-1">Weekly Hours Projection</h3>
            <p className="text-xs text-gray-500 mb-5">Projected hours for current schedule draft</p>

            <div className="relative">
                {/* Threshold lines */}
                <div className="absolute top-0 bottom-8 flex flex-col justify-between pointer-events-none" style={{ left: `${(35 / maxDisplayHours) * 100}%` }}>
                    <div className="border-l-2 border-dashed border-amber-warn/50 h-full" />
                </div>
                <div className="absolute top-0 bottom-8 flex flex-col justify-between pointer-events-none" style={{ left: `${(40 / maxDisplayHours) * 100}%` }}>
                    <div className="border-l-2 border-dashed border-danger/50 h-full" />
                </div>

                {/* Bars */}
                <div className="space-y-4">
                    {staff.map((s) => {
                        const status = s.projected_weekly_hours > 40 ? 'red' : s.projected_weekly_hours > 35 ? 'amber' : 'green';
                        const barColor =
                            status === 'red' ? 'bg-danger' : status === 'amber' ? 'bg-amber-warn' : 'bg-teal';
                        const width = Math.min((s.projected_weekly_hours / maxDisplayHours) * 100, 100);

                        return (
                            <div key={s.user_id} className="flex items-center gap-2 sm:gap-3">
                                <span className="text-xs sm:text-sm text-gray-700 w-20 sm:w-24 truncate font-medium">{s.name}</span>
                                <div className="flex-1 bg-gray-100 rounded-full h-7 relative overflow-hidden">
                                    <div
                                        className={`h-7 rounded-full ${barColor} transition-all duration-500 flex items-center justify-end pr-2`}
                                        style={{ width: `${width}%` }}
                                    >
                                        <span className="text-[10px] font-bold text-white">{s.projected_weekly_hours.toFixed(1)}h</span>
                                    </div>
                                </div>
                                <div className="w-20 sm:w-28 flex-shrink-0">
                                    {status === 'red' && <Badge variant="red">Overtime</Badge>}
                                    {status === 'amber' && <Badge variant="amber">Near limit</Badge>}
                                </div>
                            </div>
                        );
                    })}
                </div>

                {/* Legend */}
                <div className="flex items-center flex-wrap gap-3 mt-6 pt-3 border-t border-border-gray text-[10px] text-gray-500">
                    <span className="flex items-center gap-1">
                        <span className="w-4 border-t-2 border-dashed border-amber-warn" /> 35h warning
                    </span>
                    <span className="flex items-center gap-1">
                        <span className="w-4 border-t-2 border-dashed border-danger" /> 40h limit
                    </span>
                </div>
            </div>
        </div>
    );
}

function OvertimeAlertCard({ staff }: { staff: OvertimeStaffRow[] }) {
    const offenders = staff.filter(s => s.overtime_hours > 0);

    if (offenders.length === 0) {
        return (
            <div className="bg-success rounded-xl p-5 text-white">
                <div className="flex items-center gap-2 mb-3">
                    <CheckCircle size={18} />
                    <h3 className="font-bold">No Overtime</h3>
                </div>
                <p className="text-sm text-white/90">
                    All staff members are currently projected under 40 hours this week.
                </p>
            </div>
        );
    }

    return (
        <div className="bg-danger rounded-xl p-5 text-white">
            <div className="flex items-center gap-2 mb-3">
                <AlertTriangle size={18} />
                <h3 className="font-bold">Overtime Alert</h3>
            </div>
            <p className="text-sm text-white/90 mb-3">
                {offenders.length} staff member{offenders.length > 1 ? 's' : ''} projected over 40 hours
            </p>
            <div className="space-y-3 max-h-40 overflow-y-auto">
                {offenders.map(s => (
                    <div key={s.user_id} className="flex items-center gap-2 bg-white/10 p-2 rounded-lg">
                        <Avatar name={s.name} size="sm" color="bg-white/20" />
                        <div>
                            <p className="text-sm font-semibold">{s.name}</p>
                            <p className="text-xs text-white/70">{s.projected_weekly_hours.toFixed(1)}h projected · {s.overtime_hours.toFixed(1)}h OT</p>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

function CostEstimateCard({ totalCost, staff }: { totalCost: number, staff: OvertimeStaffRow[] }) {
    const totalOTCost = staff.reduce((acc, s) => acc + s.projected_overtime_cost, 0);

    return (
        <div className="bg-white rounded-xl border border-border-gray p-5 border-t-4 border-t-teal shadow-sm">
            <div className="flex items-center gap-2 mb-3">
                <DollarSign size={18} className="text-teal" />
                <h3 className="font-bold text-navy">Cost Estimate</h3>
            </div>
            <div className="space-y-4">
                <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Total projected cost:</span>
                    <span className="text-xl font-bold text-navy">${totalCost.toLocaleString()}</span>
                </div>
                {totalOTCost > 0 && (
                    <div className="flex justify-between items-center bg-danger-50 p-2 rounded-lg">
                        <span className="text-xs font-semibold text-danger">Overtime premium cost:</span>
                        <span className="text-sm font-bold text-danger">+${totalOTCost.toLocaleString()}</span>
                    </div>
                )}
            </div>
            <p className="text-xs text-gray-400 mt-4">Calculated from base rates and overtime multipliers.</p>
        </div>
    );
}

function FairnessReportUI({ staff, overallScore, grade }: { staff: FairnessStaffRow[], overallScore: number, grade: string }) {
    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-white rounded-xl border border-border-gray p-5 flex flex-col items-center justify-center text-center">
                    <h3 className="text-sm font-bold text-gray-500 uppercase mb-2">Fairness Score</h3>
                    <div className={`text-5xl font-black mb-1 ${overallScore >= 80 ? 'text-success' : overallScore >= 60 ? 'text-amber-warn' : 'text-danger'}`}>
                        {overallScore}
                    </div>
                    <Badge variant={overallScore >= 80 ? 'green' : overallScore >= 60 ? 'amber' : 'red'}>Grade: {grade}</Badge>
                </div>

                <div className="md:col-span-2 bg-white rounded-xl border border-border-gray p-5">
                    <h3 className="text-sm font-bold text-navy mb-4">Scheduling Variance (%)</h3>
                    <div className="space-y-3">
                        {staff.slice(0, 5).map(s => (
                            <div key={s.user_id} className="flex items-center gap-2 sm:gap-3">
                                <span className="text-xs font-semibold text-gray-600 w-20 sm:w-24 truncate">{s.name}</span>
                                <div className="flex-1 bg-gray-100 h-2 rounded-full overflow-hidden">
                                    <div
                                        className={`h-2 rounded-full ${Math.abs(s.scheduling_variance_pct) > 20 ? 'bg-danger' : 'bg-teal'}`}
                                        style={{ width: `${Math.min(Math.abs(s.scheduling_variance_pct) + 50, 100)}%` }}
                                    />
                                </div>
                                <span className="text-xs font-bold text-navy">{s.scheduling_variance_pct > 0 ? '+' : ''}{s.scheduling_variance_pct}%</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <div className="bg-white rounded-xl border border-border-gray overflow-x-auto shadow-sm">
                <table className="w-full min-w-[680px]">
                    <thead>
                        <tr className="bg-gray-50 border-b border-border-gray">
                            <th className="px-5 py-4 text-left text-xs font-bold text-gray-500 uppercase">Staff Name</th>
                            <th className="px-5 py-4 text-center text-xs font-bold text-gray-500 uppercase">Total Hours</th>
                            <th className="px-5 py-4 text-center text-xs font-bold text-gray-500 uppercase">Desired</th>
                            <th className="px-5 py-4 text-center text-xs font-bold text-gray-500 uppercase">Premium %</th>
                            <th className="px-5 py-4 text-center text-xs font-bold text-gray-500 uppercase">Fairness</th>
                        </tr>
                    </thead>
                    <tbody>
                        {staff.map((s) => (
                            <tr key={s.user_id} className="border-b border-border-gray hover:bg-gray-50 transition-base">
                                <td className="px-5 py-4">
                                    <div className="flex items-center gap-3">
                                        <Avatar name={s.name} size="sm" />
                                        <span className="text-sm font-semibold text-navy">{s.name}</span>
                                    </div>
                                </td>
                                <td className="px-5 py-4 text-center text-sm font-bold text-gray-700">{s.total_hours.toFixed(1)}h</td>
                                <td className="px-5 py-4 text-center text-sm text-gray-500">{s.desired_hours_per_week}h</td>
                                <td className="px-5 py-4 text-center text-sm text-gray-600">{s.premium_shift_pct}%</td>
                                <td className="px-5 py-4">
                                    <div className="flex flex-col items-center gap-1">
                                        <Badge variant={Math.abs(s.scheduling_variance_pct) < 15 ? 'green' : 'amber'}>
                                            {Math.abs(s.scheduling_variance_pct)}% Variance
                                        </Badge>
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
    const [weekStart, setWeekStart] = useState(() => format(startOfWeek(new Date(), { weekStartsOn: 1 }), 'yyyy-MM-dd'));
    const [isNotificationOpen, setIsNotificationOpen] = useState(false);

    const { data: locationsData } = useLocations();
    const { data: notificationsData } = useNotifications();
    const location = locationsData?.locations?.[0]; // Assume first location for demo/manager scope
    const unreadCount = notificationsData?.unread_count || 0;

    const { data: overtimeData, isLoading: isLoadingOT } = useOvertimeDashboard(location?.id || '', weekStart);
    const { data: fairnessData, isLoading: isLoadingFairness } = useFairnessReport(location?.id || '', weekStart, format(addDays(parseISO(weekStart), 6), 'yyyy-MM-dd'));

    const handleNextWeek = () => {
        setWeekStart(prev => format(addDays(parseISO(prev), 7), 'yyyy-MM-dd'));
    };

    const handlePrevWeek = () => {
        setWeekStart(prev => format(subDays(parseISO(prev), 7), 'yyyy-MM-dd'));
    };

    const isLoading = isLoadingOT || isLoadingFairness;

    const centerContent = (
        <div className="flex items-center gap-2 sm:gap-3 text-xs sm:text-sm">
            <button onClick={handlePrevWeek} className="p-1.5 rounded-full hover:bg-white/10 transition-base">
                <ChevronLeft size={20} />
            </button>
            <span className="font-bold min-w-0 sm:min-w-[140px] text-center whitespace-nowrap">Week of {format(parseISO(weekStart), 'MMM d, yyyy')}</span>
            <button onClick={handleNextWeek} className="p-1.5 rounded-full hover:bg-white/10 transition-base">
                <ChevronRight size={20} />
            </button>
        </div>
    );

    return (
        <AppLayout
            title="Analytics"
            role="manager"
            centerContent={centerContent}
            notificationCount={unreadCount}
            onBellClick={() => setIsNotificationOpen(true)}
        >
            <div className="p-4 md:p-6 max-w-6xl mx-auto">
                {/* Header */}
                <div className="mb-8 flex items-start gap-4 flex-wrap justify-between">
                    <div>
                        <h1 className="text-xl sm:text-2xl font-black text-navy">Overtime & Fairness</h1>
                        <p className="text-gray-500 text-sm mt-1">{location?.name || 'Loading location...'} · Data updated every 30m</p>
                    </div>
                    {isLoading && <Loader2 size={24} className="animate-spin text-teal" />}
                </div>

                {/* Tabs */}
                <div className="flex flex-wrap gap-2 mb-8">
                    <button
                        onClick={() => setActiveTab('overtime')}
                        className={`px-4 sm:px-6 py-2.5 rounded-full text-sm font-bold transition-base ${activeTab === 'overtime'
                            ? 'bg-teal text-white shadow-md'
                            : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                            }`}
                    >
                        Overtime Watch
                    </button>
                    <button
                        onClick={() => setActiveTab('fairness')}
                        className={`px-4 sm:px-6 py-2.5 rounded-full text-sm font-bold transition-base ${activeTab === 'fairness'
                            ? 'bg-teal text-white shadow-md'
                            : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                            }`}
                    >
                        Fairness Report
                    </button>
                </div>

                {/* Content */}
                {isLoading ? (
                    <div className="py-20 flex flex-col items-center justify-center text-gray-300">
                        <Loader2 size={40} className="animate-spin mb-4" />
                        <span className="text-sm font-medium">Crunching scheduling data…</span>
                    </div>
                ) : activeTab === 'overtime' ? (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fade-in">
                        <div className="lg:col-span-2">
                            <HoursBarChart staff={overtimeData?.staff || []} />
                        </div>
                        <div className="space-y-6">
                            <OvertimeAlertCard staff={overtimeData?.staff || []} />
                            <CostEstimateCard
                                totalCost={overtimeData?.total_projected_overtime_cost || 0}
                                staff={overtimeData?.staff || []}
                            />
                        </div>
                    </div>
                ) : (
                    <div className="animate-fade-in">
                        <FairnessReportUI
                            staff={fairnessData?.staff || []}
                            overallScore={fairnessData?.fairness_score || 0}
                            grade={fairnessData?.fairness_grade || 'C'}
                        />
                    </div>
                )}
            </div>

            <NotificationCentre
                open={isNotificationOpen}
                onClose={() => setIsNotificationOpen(false)}
            />
        </AppLayout>
    );
}
