/**
 * @file /apps/web/src/components/Modal.tsx
 *
 * @description
 * Shared UI/component module for `Modal` used across multiple screens.
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

interface ModalProps {
    open: boolean;
    onClose: () => void;
    title: string;
    subtitle?: string;
    width?: string;
    children: React.ReactNode;
    footer?: React.ReactNode;
}

export function Modal({ open, onClose, title, subtitle, width = 'max-w-lg', children, footer }: ModalProps) {
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
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center animate-fade-in">
            <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
            <div className={`relative bg-white rounded-t-2xl sm:rounded-xl shadow-2xl ${width} w-full mx-2 sm:mx-4 max-h-[92vh] sm:max-h-[90vh] flex flex-col animate-fade-in`}>
                {/* Header */}
                <div className="flex items-start justify-between px-4 sm:px-6 pt-5 sm:pt-6 pb-3 sm:pb-4 border-b border-border-gray">
                    <div>
                        <h2 className="text-lg font-bold text-navy">{title}</h2>
                        {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-base"
                    >
                        <X size={20} />
                    </button>
                </div>
                {/* Body */}
                <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-4">{children}</div>
                {/* Footer */}
                {footer && (
                    <div className="px-4 sm:px-6 py-4 border-t border-border-gray bg-gray-50 rounded-b-2xl sm:rounded-b-xl">{footer}</div>
                )}
            </div>
        </div>
    );
}
