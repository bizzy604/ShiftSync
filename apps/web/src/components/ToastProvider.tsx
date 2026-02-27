/**
 * @file /apps/web/src/components/ToastProvider.tsx
 *
 * @description
 * Shared UI/component module for `ToastProvider` used across multiple screens.
 *
 * @dependencies
 * - (No in-repo dependents detected.)
 *
 * @importance
 * This module provides reusable UI primitives that influence consistency and
 * maintainability.
 */

import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2, Info, X } from 'lucide-react';
import { createPortal } from 'react-dom';

type ToastType = 'success' | 'error' | 'info';

type ToastRecord = {
    id: number;
    type: ToastType;
    title: string;
    message?: string;
};

type ToastContextValue = {
    showSuccess: (title: string, message?: string) => void;
    showError: (title: string, message?: string) => void;
    showInfo: (title: string, message?: string) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

function iconForType(type: ToastType) {
    if (type === 'success') return <CheckCircle2 size={18} className="text-success" />;
    if (type === 'error') return <AlertTriangle size={18} className="text-danger" />;
    return <Info size={18} className="text-navy" />;
}

function styleForType(type: ToastType): string {
    if (type === 'success') return 'border-success/30 bg-success/5';
    if (type === 'error') return 'border-danger/30 bg-danger/5';
    return 'border-navy/20 bg-white';
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
    const [toasts, setToasts] = useState<ToastRecord[]>([]);

    const dismiss = useCallback((id: number) => {
        setToasts((prev) => prev.filter((item) => item.id !== id));
    }, []);

    const show = useCallback((type: ToastType, title: string, message?: string) => {
        const id = Date.now() + Math.floor(Math.random() * 1000);
        setToasts((prev) => [...prev, { id, type, title, message }]);
        window.setTimeout(() => dismiss(id), 4500);
    }, [dismiss]);

    const value = useMemo<ToastContextValue>(() => ({
        showSuccess: (title: string, message?: string) => show('success', title, message),
        showError: (title: string, message?: string) => show('error', title, message),
        showInfo: (title: string, message?: string) => show('info', title, message),
    }), [show]);

    return (
        <ToastContext.Provider value={value}>
            {children}
            {typeof document !== 'undefined'
                ? createPortal(
                    <div className="fixed bottom-4 right-4 z-[3000] flex w-[360px] max-w-[calc(100vw-2rem)] flex-col gap-2 pointer-events-none">
                        {toasts.map((toast) => (
                            <div
                                key={toast.id}
                                className={`rounded-xl border px-4 py-3 shadow-lg animate-fade-in pointer-events-auto ${styleForType(toast.type)}`}
                            >
                                <div className="flex items-start gap-3">
                                    <div className="mt-0.5">{iconForType(toast.type)}</div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-bold text-navy">{toast.title}</p>
                                        {toast.message ? (
                                            <p className="mt-0.5 text-xs text-gray-600 leading-relaxed">{toast.message}</p>
                                        ) : null}
                                    </div>
                                    <button
                                        onClick={() => dismiss(toast.id)}
                                        className="rounded p-0.5 text-gray-400 hover:text-gray-600 transition-base"
                                        aria-label="Dismiss notification"
                                    >
                                        <X size={14} />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>,
                    document.body
                )
                : null}
        </ToastContext.Provider>
    );
}

export function useToast(): ToastContextValue {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error('useToast must be used inside ToastProvider.');
    }
    return context;
}
