/**
 * @file /apps/web/src/components/SidePanel.tsx
 *
 * @description
 * Shared UI/component module for `SidePanel` used across multiple screens.
 *
 * @dependencies
 * - (No in-repo dependents detected.)
 *
 * @importance
 * This module provides reusable UI primitives that influence consistency and
 * maintainability.
 */

import React, { useEffect } from 'react';
import { X } from 'lucide-react';

interface SidePanelProps {
    open: boolean;
    onClose: () => void;
    title: string;
    subtitle?: string;
    width?: string;
    headerColor?: string;
    children: React.ReactNode;
}

export function SidePanel({
    open,
    onClose,
    title,
    subtitle,
    width = 'sm:w-[420px]',
    headerColor = 'bg-navy',
    children,
}: SidePanelProps) {
    useEffect(() => {
        if (open) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
        return () => {
            document.body.style.overflow = '';
        };
    }, [open]);

    if (!open) return null;

    return (
        <div className="fixed inset-0 z-50 flex justify-end">
            <div className="absolute inset-0" onClick={onClose} />
            <div className={`relative w-full max-w-full ${width} h-full bg-white shadow-2xl flex flex-col animate-slide-in-right`}>
                {/* Header */}
                <div className={`px-4 sm:px-6 py-4 ${headerColor} text-white`}>
                    <div className="flex items-start justify-between">
                        <div>
                            <h2 className="text-lg font-bold">{title}</h2>
                            {subtitle && <p className="text-sm text-white/80 mt-1">{subtitle}</p>}
                        </div>
                        <button
                            onClick={onClose}
                            className="p-1 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-base"
                        >
                            <X size={20} />
                        </button>
                    </div>
                </div>
                {/* Body */}
                <div className="flex-1 overflow-y-auto">{children}</div>
            </div>
        </div>
    );
}
