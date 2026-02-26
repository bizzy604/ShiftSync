import React, { useState } from 'react';
import { Search, Check, AlertTriangle, X, Loader2, CheckCircle } from 'lucide-react';
import { Modal } from '../../components/Modal';
import { Avatar } from '../../components/Avatar';
import { Badge } from '../../components/Badge';

interface StaffCandidate {
    id: string;
    name: string;
    hours: number;
    maxHours: number;
    constraintStatus: 'pass' | 'warning' | 'violation';
    constraintMessage?: string;
    constraintDetail?: string;
}

const mockCandidates: StaffCandidate[] = [
    {
        id: '1',
        name: 'Carlos M.',
        hours: 38,
        maxHours: 40,
        constraintStatus: 'warning',
        constraintMessage: '6th consecutive day — warning',
    },
    {
        id: '2',
        name: 'Maria L.',
        hours: 22,
        maxHours: 40,
        constraintStatus: 'violation',
        constraintMessage: 'Rest period violation: only 7h gap',
        constraintDetail:
            'Rest Period Violation — Previous shift ends at 10pm. This shift starts at 2pm. Only 7h gap. Minimum required: 10h.',
    },
    {
        id: '3',
        name: 'Jordan T.',
        hours: 24,
        maxHours: 40,
        constraintStatus: 'pass',
    },
    {
        id: '4',
        name: 'Priya N.',
        hours: 32,
        maxHours: 40,
        constraintStatus: 'pass',
    },
];

type ModalState = 'select' | 'loading' | 'success';

interface AssignmentModalProps {
    open: boolean;
    onClose: () => void;
}

export function AssignmentModal({ open, onClose }: AssignmentModalProps) {
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedStaff, setSelectedStaff] = useState<string | null>(null);
    const [expandedViolation, setExpandedViolation] = useState<string | null>(null);
    const [overrideReason, setOverrideReason] = useState('');
    const [showOverrideInput, setShowOverrideInput] = useState<string | null>(null);
    const [modalState, setModalState] = useState<ModalState>('select');

    const selectedName = mockCandidates.find((c) => c.id === selectedStaff)?.name;

    const filteredCandidates = mockCandidates.filter((c) =>
        c.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const handleAssign = () => {
        setModalState('loading');
        setTimeout(() => setModalState('success'), 1500);
    };

    const resetAndClose = () => {
        setModalState('select');
        setSelectedStaff(null);
        setExpandedViolation(null);
        setOverrideReason('');
        setShowOverrideInput(null);
        setSearchQuery('');
        onClose();
    };

    if (modalState === 'success') {
        return (
            <Modal open={open} onClose={resetAndClose} title="Assignment Complete" width="max-w-md">
                <div className="py-8 flex flex-col items-center text-center animate-fade-in">
                    <div className="w-16 h-16 rounded-full bg-success-50 flex items-center justify-center mb-4">
                        <CheckCircle size={36} className="text-success" />
                    </div>
                    <h3 className="text-lg font-bold text-navy mb-1">{selectedName} assigned</h3>
                    <p className="text-sm text-gray-500">Wednesday 2pm–10pm · Bartender · Ocean Ave</p>
                    <button
                        onClick={resetAndClose}
                        className="mt-6 px-6 py-2.5 bg-teal text-white font-semibold rounded-lg hover:bg-teal-dark transition-base"
                    >
                        Done
                    </button>
                </div>
            </Modal>
        );
    }

    return (
        <Modal
            open={open}
            onClose={resetAndClose}
            title="Assign Staff — Bartender Shift"
            subtitle="Wednesday, August 13, 2025"
            width="max-w-xl"
            footer={
                <div className="flex items-center justify-between">
                    <button onClick={resetAndClose} className="text-sm text-gray-500 hover:text-navy transition-base">
                        Cancel
                    </button>
                    <button
                        onClick={handleAssign}
                        disabled={!selectedStaff || modalState === 'loading'}
                        className="px-5 py-2.5 bg-teal text-white font-semibold rounded-lg hover:bg-teal-dark disabled:opacity-50 disabled:cursor-not-allowed transition-base flex items-center gap-2"
                    >
                        {modalState === 'loading' ? (
                            <>
                                <Loader2 size={16} className="animate-spin" /> Assigning…
                            </>
                        ) : selectedName ? (
                            `Assign ${selectedName}`
                        ) : (
                            'Select a staff member'
                        )}
                    </button>
                </div>
            }
        >
            {/* Shift Details */}
            <div className="bg-gray-50 rounded-lg p-4 mb-5">
                <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                        <span className="text-gray-500">Time:</span>
                        <span className="ml-2 font-medium text-navy">2:00 PM – 10:00 PM</span>
                    </div>
                    <div>
                        <span className="text-gray-500">Location:</span>
                        <span className="ml-2 font-medium text-navy">Ocean Ave</span>
                    </div>
                    <div>
                        <span className="text-gray-500">Required skill:</span>
                        <span className="ml-2 font-medium text-navy">Bartender</span>
                    </div>
                    <div>
                        <span className="text-gray-500">Headcount:</span>
                        <span className="ml-2 font-medium text-navy">1</span>
                    </div>
                </div>
            </div>

            {/* Search */}
            <div className="mb-4">
                <label className="text-sm font-semibold text-navy mb-2 block">Select a staff member</label>
                <div className="relative">
                    <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Search by name…"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-9 pr-4 py-2.5 rounded-lg border border-border-gray bg-gray-50 text-sm text-navy placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-teal/40 transition-base"
                        disabled={modalState === 'loading'}
                    />
                </div>
            </div>

            {/* Staff List */}
            <div className="space-y-1">
                {filteredCandidates.map((c) => {
                    const isSelected = selectedStaff === c.id;
                    const isExpanded = expandedViolation === c.id;
                    const showingOverride = showOverrideInput === c.id;

                    return (
                        <div key={c.id}>
                            <button
                                onClick={() => {
                                    if (c.constraintStatus === 'violation') {
                                        setExpandedViolation(isExpanded ? null : c.id);
                                        return;
                                    }
                                    if (c.constraintStatus === 'warning') {
                                        setShowOverrideInput(showingOverride ? null : c.id);
                                        return;
                                    }
                                    setSelectedStaff(c.id);
                                }}
                                disabled={modalState === 'loading'}
                                className={`w-full flex items-center gap-3 px-4 py-3.5 rounded-lg text-left transition-base ${isSelected
                                        ? 'bg-teal-50 border-2 border-teal'
                                        : c.constraintStatus === 'violation'
                                            ? 'bg-gray-50 opacity-75 hover:opacity-100'
                                            : 'bg-gray-50 hover:bg-gray-100'
                                    } ${modalState === 'loading' ? 'pointer-events-none opacity-50' : ''}`}
                            >
                                <Avatar name={c.name} size="md" />
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-semibold text-navy">{c.name}</p>
                                    <div className="flex items-center gap-2 mt-1">
                                        <div className="w-24 bg-gray-200 rounded-full h-1.5">
                                            <div
                                                className="h-1.5 rounded-full bg-teal"
                                                style={{ width: `${(c.hours / c.maxHours) * 100}%` }}
                                            />
                                        </div>
                                        <span className="text-xs text-gray-500">{c.hours}h / {c.maxHours}h</span>
                                    </div>
                                </div>
                                {c.constraintStatus === 'pass' && (
                                    <Check size={18} className="text-success flex-shrink-0" />
                                )}
                                {c.constraintStatus === 'warning' && (
                                    <div className="flex-shrink-0" title={c.constraintMessage}>
                                        <AlertTriangle size={18} className="text-amber-warn" />
                                    </div>
                                )}
                                {c.constraintStatus === 'violation' && (
                                    <div className="flex-shrink-0" title={c.constraintMessage}>
                                        <X size={18} className="text-danger" />
                                    </div>
                                )}
                            </button>

                            {/* Violation Detail */}
                            {isExpanded && c.constraintDetail && (
                                <div className="ml-4 mt-1 p-3 bg-danger-50 border border-danger/20 rounded-lg text-sm text-danger animate-fade-in">
                                    <p className="font-medium">{c.constraintDetail}</p>
                                    <button className="mt-2 text-xs text-teal font-semibold hover:underline">
                                        View Alternatives
                                    </button>
                                </div>
                            )}

                            {/* Override Input */}
                            {showingOverride && (
                                <div className="ml-4 mt-1 p-3 bg-amber-warn-50 border border-amber-warn/20 rounded-lg animate-fade-in">
                                    <p className="text-xs text-amber-warn font-medium mb-2">{c.constraintMessage}</p>
                                    <textarea
                                        placeholder="Override reason (min 10 characters)…"
                                        value={overrideReason}
                                        onChange={(e) => setOverrideReason(e.target.value)}
                                        className="w-full px-3 py-2 border border-border-gray rounded-lg text-sm text-navy placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-amber-warn/40 resize-none"
                                        rows={2}
                                    />
                                    <button
                                        disabled={overrideReason.length < 10}
                                        onClick={() => {
                                            setSelectedStaff(c.id);
                                            setShowOverrideInput(null);
                                        }}
                                        className="mt-2 px-4 py-1.5 text-xs font-semibold bg-amber-warn text-white rounded-lg disabled:opacity-50 hover:bg-amber-warn/90 transition-base"
                                    >
                                        Assign with Override
                                    </button>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </Modal>
    );
}
