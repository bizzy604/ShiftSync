import React from 'react';

type BadgeVariant = 'teal' | 'purple' | 'amber' | 'red' | 'green' | 'gray' | 'slate' | 'blue';

interface BadgeProps {
    children: React.ReactNode;
    variant?: BadgeVariant;
    className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
    teal: 'bg-teal-50 text-teal border border-teal/20',
    purple: 'bg-staff-purple-50 text-staff-purple border border-staff-purple/20',
    amber: 'bg-amber-warn-50 text-amber-warn border border-amber-warn/20',
    red: 'bg-danger-50 text-danger border border-danger/20',
    green: 'bg-success-50 text-success border border-success/20',
    gray: 'bg-gray-100 text-gray-600 border border-gray-200',
    slate: 'bg-gray-100 text-admin-slate border border-admin-slate/20',
    blue: 'bg-blue-50 text-blue-700 border border-blue-200',
};

export function Badge({ children, variant = 'gray', className = '' }: BadgeProps) {
    return (
        <span
            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold whitespace-nowrap ${variantStyles[variant]} ${className}`}
        >
            {children}
        </span>
    );
}
