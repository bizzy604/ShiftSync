import React, { useState } from 'react';
import { Check, ArrowLeft, X, Loader2 } from 'lucide-react';
import { Modal } from '../../components/Modal';
import { Avatar } from '../../components/Avatar';
import { Badge } from '../../components/Badge';

/* ========== Types ========== */

interface SwapCandidate {
    id: string;
    name: string;
    hours: number;
    availableStatus: string;
    available: boolean;
}

const mockCandidates: SwapCandidate[] = [
    { id: '1', name: 'Maria L.', hours: 22, availableStatus: 'Available Wed 6pm–11pm', available: true },
    { id: '2', name: 'Jordan T.', hours: 24, availableStatus: 'Available Wed 6pm–11pm', available: true },
    { id: '3', name: 'Sam K.', hours: 28, availableStatus: 'Unavailable', available: false },
];

type FlowStep = 'select' | 'note' | 'status' | 'approved';

/* ========== Sub-Components ========== */

function StepIndicator({ current, total, label }: { current: number; total: number; label: string }) {
    return (
        <div className="flex items-center gap-2 mb-5">
            <Badge variant="purple">Step {current} of {total}</Badge>
            <span className="text-xs text-gray-500">{label}</span>
        </div>
    );
}

function SwapTimeline({ currentStep }: { currentStep: number }) {
    const steps = ['Requested', 'Maria Accepts', 'Manager Approves'];

    return (
        <div className="flex items-center justify-between my-6 px-4">
            {steps.map((step, i) => {
                const isComplete = i < currentStep;
                const isCurrent = i === currentStep;

                return (
                    <React.Fragment key={step}>
                        <div className="flex flex-col items-center gap-2 flex-shrink-0">
                            <div
                                className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${isComplete
                                        ? 'bg-staff-purple text-white'
                                        : isCurrent
                                            ? 'bg-staff-purple/20 border-2 border-staff-purple'
                                            : 'bg-gray-200'
                                    } ${isCurrent ? 'animate-pulse-dot' : ''}`}
                            >
                                {isComplete ? (
                                    <Check size={16} />
                                ) : (
                                    <span className={`w-2.5 h-2.5 rounded-full ${isCurrent ? 'bg-staff-purple' : 'bg-gray-400'}`} />
                                )}
                            </div>
                            <span
                                className={`text-[11px] font-medium text-center max-w-[80px] ${isComplete || isCurrent ? 'text-navy' : 'text-gray-400'
                                    }`}
                            >
                                {step}
                            </span>
                        </div>
                        {i < steps.length - 1 && (
                            <div className={`flex-1 h-0.5 mx-2 mt-[-20px] ${isComplete ? 'bg-staff-purple' : 'bg-gray-200'}`} />
                        )}
                    </React.Fragment>
                );
            })}
        </div>
    );
}

/* ========== Main Component ========== */

interface SwapRequestFlowProps {
    open: boolean;
    onClose: () => void;
}

export function SwapRequestFlow({ open, onClose }: SwapRequestFlowProps) {
    const [step, setStep] = useState<FlowStep>('select');
    const [selectedStaff, setSelectedStaff] = useState<string | null>(null);
    const [note, setNote] = useState('');
    const [submitting, setSubmitting] = useState(false);

    const selectedName = mockCandidates.find((c) => c.id === selectedStaff)?.name;

    const handleSubmit = () => {
        setSubmitting(true);
        setTimeout(() => {
            setSubmitting(false);
            setStep('status');
        }, 1500);
    };

    const resetAndClose = () => {
        setStep('select');
        setSelectedStaff(null);
        setNote('');
        onClose();
    };

    /* ---- Status View ---- */
    if (step === 'status') {
        return (
            <Modal
                open={open}
                onClose={resetAndClose}
                title="Swap Request Status"
                subtitle="Your shift: Wednesday, Aug 13 · Bartender · 6:00 PM – 11:00 PM"
                width="max-w-md"
            >
                <div className="py-4 animate-fade-in">
                    <div className="text-center mb-4">
                        <h3 className="text-base font-bold text-navy">Swap Requested</h3>
                        <p className="text-sm text-gray-500">Waiting for {selectedName} to accept</p>
                    </div>

                    <SwapTimeline currentStep={1} />

                    <div className="mt-6 text-center">
                        <button
                            onClick={() => setStep('approved')}
                            className="text-xs text-staff-purple font-medium hover:underline mr-4"
                        >
                            Simulate Accept + Approve
                        </button>
                        <button
                            onClick={resetAndClose}
                            className="text-xs text-gray-500 hover:underline"
                        >
                            Cancel Request
                        </button>
                    </div>
                </div>
            </Modal>
        );
    }

    /* ---- Approved View ---- */
    if (step === 'approved') {
        return (
            <Modal
                open={open}
                onClose={resetAndClose}
                title="Swap Approved!"
                width="max-w-md"
            >
                <div className="py-6 animate-fade-in">
                    <SwapTimeline currentStep={3} />

                    <div className="text-center mt-4">
                        <div className="w-14 h-14 rounded-full bg-success-50 flex items-center justify-center mx-auto mb-3">
                            <Check size={28} className="text-success" />
                        </div>
                        <h3 className="text-base font-bold text-navy mb-1">Swap Complete</h3>
                        <p className="text-sm text-gray-500">
                            {selectedName} will cover your Wednesday Aug 13 shift.
                        </p>
                        <Badge variant="green" className="mt-3">Swap Approved</Badge>
                    </div>

                    <div className="mt-6 text-center">
                        <button
                            onClick={resetAndClose}
                            className="px-6 py-2 bg-staff-purple text-white font-semibold rounded-lg hover:bg-staff-purple-light transition-base"
                        >
                            Done
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
                title="Request Shift Swap"
                subtitle="Your shift: Wednesday, Aug 13 · Bartender · 6:00 PM – 11:00 PM · Ocean Ave"
                width="max-w-lg"
                footer={
                    <div className="flex items-center justify-between">
                        <button
                            onClick={() => setStep('select')}
                            className="flex items-center gap-1 text-sm text-gray-500 hover:text-navy transition-base"
                        >
                            <ArrowLeft size={16} /> Back
                        </button>
                        <button
                            onClick={handleSubmit}
                            disabled={submitting}
                            className="px-5 py-2.5 bg-staff-purple text-white font-semibold rounded-lg hover:bg-staff-purple-light disabled:opacity-60 transition-base flex items-center gap-2"
                        >
                            {submitting ? (
                                <>
                                    <Loader2 size={16} className="animate-spin" /> Sending…
                                </>
                            ) : (
                                'Send Swap Request'
                            )}
                        </button>
                    </div>
                }
            >
                <StepIndicator current={2} total={2} label="Add a Note" />

                {/* Confirmation */}
                <div className="flex items-center gap-3 p-3 bg-staff-purple-50 rounded-lg mb-5">
                    <Avatar name={selectedName ?? ''} size="md" color="bg-staff-purple" />
                    <div>
                        <p className="text-sm font-semibold text-navy">Swapping with: {selectedName}</p>
                        <p className="text-xs text-gray-500">They will be asked to accept this swap</p>
                    </div>
                </div>

                {/* Note textarea */}
                <div>
                    <label className="block text-sm font-medium text-navy mb-1.5">
                        Message (optional)
                    </label>
                    <textarea
                        placeholder="Add a note for the staff member and manager…"
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                        className="w-full px-4 py-3 rounded-lg border border-border-gray bg-gray-50 text-sm text-navy placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-staff-purple/40 resize-none transition-base"
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
            title="Request Shift Swap"
            subtitle="Your shift: Wednesday, Aug 13 · Bartender · 6:00 PM – 11:00 PM · Ocean Ave"
            width="max-w-lg"
            footer={
                <div className="flex items-center justify-between">
                    <button onClick={resetAndClose} className="text-sm text-gray-500 hover:text-navy transition-base">
                        Cancel
                    </button>
                    <button
                        onClick={() => setStep('note')}
                        disabled={!selectedStaff}
                        className="px-5 py-2.5 bg-staff-purple text-white font-semibold rounded-lg hover:bg-staff-purple-light disabled:opacity-50 transition-base"
                    >
                        Next: Add a Note →
                    </button>
                </div>
            }
        >
            <StepIndicator current={1} total={2} label="Choose a staff member" />

            <p className="text-xs text-gray-500 mb-4">
                Only staff certified at Ocean Ave with the Bartender skill are shown.
            </p>

            <div className="space-y-2">
                {mockCandidates.map((c) => {
                    const isSelected = selectedStaff === c.id;

                    return (
                        <button
                            key={c.id}
                            onClick={() => c.available && setSelectedStaff(c.id)}
                            disabled={!c.available}
                            className={`w-full flex items-center gap-3 px-4 py-3.5 rounded-xl text-left transition-base ${isSelected
                                    ? 'bg-staff-purple-50 border-2 border-staff-purple'
                                    : c.available
                                        ? 'bg-gray-50 hover:bg-gray-100 border border-transparent'
                                        : 'bg-gray-50 opacity-50 cursor-not-allowed border border-transparent'
                                }`}
                        >
                            <Avatar
                                name={c.name}
                                size="md"
                                color={c.available ? 'bg-staff-purple' : 'bg-gray-400'}
                            />
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-semibold text-navy">{c.name}</p>
                                <p className="text-xs text-gray-500">{c.hours}h this week</p>
                            </div>
                            <Badge variant={c.available ? 'green' : 'gray'}>
                                {c.availableStatus}
                            </Badge>
                        </button>
                    );
                })}
            </div>
        </Modal>
    );
}
