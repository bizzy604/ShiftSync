import React, { useState, useEffect } from 'react';
import { Modal } from '../../components/Modal';
import { useCreateShift, useSkills } from '../../lib/api/hooks';
import { Loader2 } from 'lucide-react';

interface CreateShiftModalProps {
    open: boolean;
    onClose: () => void;
    locationId: string;
    defaultDateStr: string;
    defaultPeriodIndex: number; // 0: Morning, 1: Afternoon, 2: Night
}

const PERIOD_DEFAULTS = [
    { start: '09:00', end: '17:00' },
    { start: '12:00', end: '18:00' },
    { start: '18:00', end: '02:00' },
];

export function CreateShiftModal({ open, onClose, locationId, defaultDateStr, defaultPeriodIndex }: CreateShiftModalProps) {
    const { data: skills, isLoading: isLoadingSkills } = useSkills();
    const availableSkills = skills || [];

    const [date, setDate] = useState(defaultDateStr);
    const [startTime, setStartTime] = useState(PERIOD_DEFAULTS[0].start);
    const [endTime, setEndTime] = useState(PERIOD_DEFAULTS[0].end);
    const [skillId, setSkillId] = useState('');
    const [headcount, setHeadcount] = useState(1);

    const createMutation = useCreateShift();

    // Reset state when modal opens or skills load
    useEffect(() => {
        if (open) {
            setDate(defaultDateStr);
            const period = PERIOD_DEFAULTS[defaultPeriodIndex] || PERIOD_DEFAULTS[0];
            setStartTime(period.start);
            setEndTime(period.end);
            if (availableSkills.length > 0 && !skillId) {
                setSkillId(availableSkills[0].id);
            }
            setHeadcount(1);
        }
    }, [open, defaultDateStr, defaultPeriodIndex, availableSkills, skillId]);

    const handleCreate = () => {
        createMutation.mutate(
            {
                locationId,
                data: {
                    date,
                    start_time: startTime,
                    end_time: endTime,
                    required_skill_id: skillId,
                    headcount_needed: headcount,
                }
            },
            {
                onSuccess: () => {
                    onClose();
                }
            }
        );
    };

    if (!open) return null;

    return (
        <Modal
            open={open}
            onClose={onClose}
            title="Create New Shift"
            subtitle="Add a new shift to the schedule"
            width="max-w-md"
            footer={
                <div className="flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-between gap-3">
                    <button onClick={onClose} className="w-full sm:w-auto text-sm font-bold text-gray-500 hover:text-navy transition-base">
                        Cancel
                    </button>
                    <button
                        onClick={handleCreate}
                        disabled={createMutation.isPending || !date || !startTime || !endTime}
                        className="w-full sm:w-auto justify-center px-5 py-2.5 bg-teal text-white font-semibold rounded-lg hover:bg-teal-dark disabled:opacity-50 transition-base flex items-center gap-2"
                    >
                        {createMutation.isPending ? (
                            <><Loader2 size={16} className="animate-spin" /> Creating…</>
                        ) : (
                            'Create Shift'
                        )}
                    </button>
                </div>
            }
        >
            <div className="space-y-4">
                {/* Required Skill */}
                <div>
                    <label className="block text-sm font-semibold text-navy mb-1.5">Required Skill</label>
                    <select
                        value={skillId}
                        onChange={e => setSkillId(e.target.value)}
                        disabled={isLoadingSkills}
                        className="w-full px-3 py-2 border border-border-gray rounded-lg text-sm bg-gray-50 focus:outline-none focus:ring-2 focus:ring-teal/40 disabled:opacity-50"
                    >
                        {isLoadingSkills ? (
                            <option>Loading skills...</option>
                        ) : availableSkills.length === 0 ? (
                            <option>No skills available</option>
                        ) : (
                            availableSkills.map(s => (
                                <option key={s.id} value={s.id}>{s.name}</option>
                            ))
                        )}
                    </select>
                </div>

                {/* Date */}
                <div>
                    <label className="block text-sm font-semibold text-navy mb-1.5">Date</label>
                    <input
                        type="date"
                        value={date}
                        onChange={e => setDate(e.target.value)}
                        className="w-full px-3 py-2 border border-border-gray rounded-lg text-sm bg-gray-50 focus:outline-none focus:ring-2 focus:ring-teal/40"
                    />
                </div>

                {/* Time Range */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-semibold text-navy mb-1.5">Start Time</label>
                        <input
                            type="time"
                            value={startTime}
                            onChange={e => setStartTime(e.target.value)}
                            className="w-full px-3 py-2 border border-border-gray rounded-lg text-sm bg-gray-50 focus:outline-none focus:ring-2 focus:ring-teal/40"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-semibold text-navy mb-1.5">End Time</label>
                        <input
                            type="time"
                            value={endTime}
                            onChange={e => setEndTime(e.target.value)}
                            className="w-full px-3 py-2 border border-border-gray rounded-lg text-sm bg-gray-50 focus:outline-none focus:ring-2 focus:ring-teal/40"
                        />
                    </div>
                </div>

                {/* Headcount */}
                <div>
                    <label className="block text-sm font-semibold text-navy mb-1.5">Headcount Needed</label>
                    <input
                        type="number"
                        min="1"
                        max="20"
                        value={headcount}
                        onChange={e => setHeadcount(parseInt(e.target.value) || 1)}
                        className="w-full px-3 py-2 border border-border-gray rounded-lg text-sm bg-gray-50 focus:outline-none focus:ring-2 focus:ring-teal/40"
                    />
                </div>
            </div>
        </Modal>
    );
}
