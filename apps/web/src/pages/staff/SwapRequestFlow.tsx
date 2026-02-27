import React, { useState } from 'react';
import { Check, ArrowLeft, X, Loader2, Info, UserPlus } from 'lucide-react';
import { Modal } from '../../components/Modal';
import { Avatar } from '../../components/Avatar';
import { Badge } from '../../components/Badge';
import { useShiftSuggestions, useCreateSwapRequest } from '../../lib/api/hooks';
import { MyAssignmentResponse } from '../../lib/api/types';
import { format, parseISO } from 'date-fns';

/* ========== Types ========== */

type FlowStep = 'select' | 'note' | 'status' | 'approved';

/* ========== Sub-Components ========== */

function StepIndicator({ current, total, label }: { current: number; total: number; label: string }) {
    return (
        <div className="flex items-center gap-2 mb-5 flex-wrap">
            <Badge variant="purple">Step {current} of {total}</Badge>
            <span className="text-xs text-gray-500 font-bold uppercase tracking-tight">{label}</span>
        </div>
    );
}

function SwapTimeline({ currentStep, targetName }: { currentStep: number; targetName: string }) {
    const steps = ['Requested', `${targetName} Accepts`, 'Manager Approves'];

    return (
        <div className="overflow-x-auto pb-2">
            <div className="flex items-center justify-between my-8 px-2 sm:px-4 min-w-[560px]">
                {steps.map((step, i) => {
                    const isComplete = i < currentStep;
                    const isCurrent = i === currentStep;

                    return (
                        <React.Fragment key={step}>
                            <div className="flex flex-col items-center gap-2 flex-shrink-0 relative">
                                <div
                                    className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${isComplete
                                        ? 'bg-staff-purple text-white shadow-lg shadow-staff-purple/20'
                                        : isCurrent
                                            ? 'bg-staff-purple/20 border-2 border-staff-purple shadow-lg shadow-staff-purple/10'
                                            : 'bg-gray-100 text-gray-400'
                                        } ${isCurrent ? 'animate-pulse' : ''}`}
                                >
                                    {isComplete ? (
                                        <Check size={20} />
                                    ) : (
                                        <span className={`w-3 h-3 rounded-full ${isCurrent ? 'bg-staff-purple' : 'bg-gray-300'}`} />
                                    )}
                                </div>
                                <span
                                    className={`text-[10px] font-black uppercase tracking-tight text-center max-w-[80px] absolute -bottom-8 ${isComplete || isCurrent ? 'text-navy' : 'text-gray-400'
                                        }`}
                                >
                                    {step}
                                </span>
                            </div>
                            {i < steps.length - 1 && (
                                <div className={`flex-1 h-1 mx-2 ${isComplete ? 'bg-staff-purple' : 'bg-gray-100'}`} />
                            )}
                        </React.Fragment>
                    );
                })}
            </div>
        </div>
    );
}

/* ========== Main Component ========== */

interface SwapRequestFlowProps {
    open: boolean;
    onClose: () => void;
    myAssignment: MyAssignmentResponse | null;
}

export function SwapRequestFlow({ open, onClose, myAssignment }: SwapRequestFlowProps) {
    const [step, setStep] = useState<FlowStep>('select');
    const [selectedStaffId, setSelectedStaffId] = useState<string | null>(null);
    const [note, setNote] = useState('');

    const { data: suggestions, isLoading: isLoadingSuggestions } = useShiftSuggestions(myAssignment?.shift.id || '');
    const createSwapMutation = useCreateSwapRequest();

    const selectedStaff = suggestions?.find((s: any) => s.user_id === selectedStaffId);
    const selectedName = selectedStaff?.name || 'Staff Member';

    const handleSubmit = () => {
        if (!myAssignment || !selectedStaffId) return;

        createSwapMutation.mutate({
            my_assignment_id: myAssignment.id,
            target_user_id: selectedStaffId,
        }, {
            onSuccess: () => {
                setStep('status');
            }
        });
    };

    const resetAndClose = () => {
        setStep('select');
        setSelectedStaffId(null);
        setNote('');
        onClose();
    };

    if (!myAssignment) return null;

    const shiftInfo = `${format(parseISO(myAssignment.shift.shift_date), 'eeee, MMM d')} · ${myAssignment.shift.required_skill} · ${myAssignment.shift.start_local.slice(11, 16)} – ${myAssignment.shift.end_local.slice(11, 16)}`;

    /* ---- Status View ---- */
    if (step === 'status') {
        return (
            <Modal
                open={open}
                onClose={resetAndClose}
                title="Swap Status"
                subtitle={shiftInfo}
                width="max-w-md"
            >
                <div className="py-6 animate-fade-in">
                    <div className="text-center mb-10">
                        <div className="w-16 h-16 bg-staff-purple/10 rounded-full flex items-center justify-center mx-auto mb-4">
                            <Loader2 size={32} className="text-staff-purple animate-spin" />
                        </div>
                        <h3 className="text-lg font-black text-navy uppercase tracking-tight">Swap Requested</h3>
                        <p className="text-sm text-gray-500 font-medium">Waiting for {selectedName} to accept your request.</p>
                    </div>

                    <SwapTimeline currentStep={1} targetName={selectedName} />

                    <div className="mt-16 text-center space-y-4">
                        <div className="p-4 bg-gray-50 rounded-2xl border border-border-gray text-left flex gap-3">
                            <Info size={16} className="text-gray-400 shrink-0 mt-0.5" />
                            <p className="text-xs text-gray-500 leading-relaxed font-medium">
                                Once accepted by the staff member, the request will be sent to your manager for final approval. You'll be notified of any status changes.
                            </p>
                        </div>
                        <button
                            onClick={resetAndClose}
                            className="w-full py-3 bg-navy text-white text-xs font-black uppercase tracking-widest rounded-xl hover:bg-navy-light transition-all shadow-lg active:scale-95"
                        >
                            Got it, thanks
                        </button>
                    </div>
                </div>
            </Modal>
        );
    }

    /* ---- Step 2: Note ---- */
    if (step === 'note') {
        return (
            <Modal
                open={open}
                onClose={resetAndClose}
                title="Shift Swap Request"
                subtitle={shiftInfo}
                width="max-w-lg"
                footer={
                    <div className="flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-between w-full gap-3">
                        <button
                            onClick={() => setStep('select')}
                            className="w-full sm:w-auto justify-center sm:justify-start flex items-center gap-2 text-xs font-black uppercase tracking-widest text-gray-500 hover:text-navy transition-all"
                        >
                            <ArrowLeft size={16} /> Back
                        </button>
                        <button
                            onClick={handleSubmit}
                            disabled={createSwapMutation.isPending}
                            className="w-full sm:w-auto justify-center px-8 py-3 bg-staff-purple text-white text-xs font-black uppercase tracking-widest rounded-xl hover:bg-staff-purple-light shadow-lg hover:shadow-staff-purple/20 transition-all active:scale-95 disabled:opacity-50 flex items-center gap-2"
                        >
                            {createSwapMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : 'Send Request'}
                        </button>
                    </div>
                }
            >
                <StepIndicator current={2} total={2} label="Add a message" />

                <div className="flex items-center gap-4 p-4 bg-staff-purple/5 rounded-2xl border border-staff-purple/10 mb-6 flex-wrap">
                    <Avatar name={selectedName} size="lg" color="bg-staff-purple" />
                    <div>
                        <p className="text-[10px] font-black text-staff-purple uppercase tracking-widest mb-0.5">Swapping with</p>
                        <p className="text-lg font-black text-navy">{selectedName}</p>
                        <p className="text-xs text-gray-500 font-medium leading-tight">Your shift will be offered to this staff member.</p>
                    </div>
                </div>

                <div className="space-y-2">
                    <label className="text-[10px] font-black text-navy uppercase tracking-widest opacity-60 ml-1">
                        Message to Staff & Manager
                    </label>
                    <textarea
                        placeholder="Explain why you need a swap (optional)…"
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                        className="w-full px-5 py-4 rounded-2xl border border-border-gray bg-white text-sm font-medium text-navy placeholder:text-gray-300 focus:ring-4 focus:ring-staff-purple/5 focus:border-staff-purple/40 resize-none transition-all outline-none"
                        rows={4}
                    />
                </div>
            </Modal>
        );
    }

    /* ---- Step 1: Select Staff ---- */
    return (
        <Modal
            open={open}
            onClose={resetAndClose}
            title="Shift Swap Request"
            subtitle={shiftInfo}
            width="max-w-lg"
            footer={
                <div className="flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-between w-full gap-3">
                    <button onClick={resetAndClose} className="w-full sm:w-auto text-xs font-black uppercase tracking-widest text-gray-500 hover:text-navy transition-all">
                        Cancel
                    </button>
                    <button
                        onClick={() => setStep('note')}
                        disabled={!selectedStaffId}
                        className="w-full sm:w-auto px-8 py-3 bg-navy text-white text-xs font-black uppercase tracking-widest rounded-xl hover:bg-navy-light shadow-lg transition-all active:scale-95 disabled:opacity-50"
                    >
                        Next Step
                    </button>
                </div>
            }
        >
            <StepIndicator current={1} total={2} label="Choose a colleague" />

            <div className="bg-navy/5 p-4 rounded-2xl border border-navy/10 mb-6 flex gap-3">
                <div className="w-8 h-8 rounded-full bg-staff-purple/20 flex items-center justify-center shrink-0">
                    <UserPlus size={16} className="text-staff-purple" />
                </div>
                <p className="text-[11px] text-navy font-medium leading-relaxed">
                    Below are staff members who are <span className="font-bold">certified</span> at this location and hold the <span className="font-bold">required skills</span> for this shift.
                </p>
            </div>

            <div className="space-y-2 max-h-[360px] overflow-y-auto pr-2 custom-scrollbar">
                {isLoadingSuggestions ? (
                    <div className="py-20 flex flex-col items-center justify-center text-gray-300">
                        <Loader2 size={32} className="animate-spin mb-4" />
                        <span className="text-[10px] font-black uppercase tracking-widest">Finding available staff…</span>
                    </div>
                ) : (
                    suggestions?.map((s: any) => {
                        const isSelected = selectedStaffId === s.user_id;

                        return (
                            <button
                                key={s.user_id}
                                onClick={() => setSelectedStaffId(s.user_id)}
                                className={`w-full flex items-center gap-4 px-5 py-4 rounded-2xl text-left transition-all group border-2 ${isSelected
                                    ? 'bg-staff-purple/5 border-staff-purple shadow-lg shadow-staff-purple/10'
                                    : 'bg-white border-transparent hover:bg-gray-50 hover:border-border-gray'
                                    }`}
                            >
                                <Avatar
                                    name={s.name}
                                    size="lg"
                                    color={isSelected ? 'bg-staff-purple' : 'bg-navy/10'}
                                />
                                <div className="flex-1 min-w-0">
                                    <p className={`text-sm font-black transition-colors ${isSelected ? 'text-staff-purple' : 'text-navy'}`}>{s.name}</p>
                                    <p className="text-[10px] text-gray-400 font-bold uppercase tracking-tight">{s.reason}</p>
                                </div>
                                <div className={`w-6 h-6 rounded-full border-2 transition-all flex items-center justify-center ${isSelected ? 'bg-staff-purple border-staff-purple text-white' : 'border-gray-200 group-hover:border-gray-300'
                                    }`}>
                                    {isSelected && <Check size={14} />}
                                </div>
                            </button>
                        );
                    })
                )}
                {!isLoadingSuggestions && suggestions?.length === 0 && (
                    <div className="py-20 text-center bg-gray-50/50 rounded-2xl border border-dashed border-border-gray">
                        <p className="text-[10px] font-black uppercase tracking-widest text-gray-400">No qualified staff available for swap</p>
                    </div>
                )}
            </div>
        </Modal>
    );
}
