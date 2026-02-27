/**
 * @file /apps/web/src/components/Avatar.tsx
 *
 * @description
 * Shared UI/component module for `Avatar` used across multiple screens.
 *
 * @dependencies
 * - (No in-repo dependents detected.)
 *
 * @importance
 * This module provides reusable UI primitives that influence consistency and
 * maintainability.
 */

import React from 'react';

type AvatarSize = 'sm' | 'md' | 'lg';

interface AvatarProps {
    name: string;
    size?: AvatarSize;
    color?: string;
    className?: string;
    online?: boolean;
}

const sizeMap: Record<AvatarSize, string> = {
    sm: 'w-7 h-7 text-xs',
    md: 'w-9 h-9 text-sm',
    lg: 'w-11 h-11 text-base',
};

function getInitials(name: string): string {
    return name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2);
}

export function Avatar({ name, size = 'md', color = 'bg-navy', className = '', online }: AvatarProps) {
    return (
        <div className={`relative inline-flex items-center justify-center rounded-full font-semibold text-white ${color} ${sizeMap[size]} ${className}`}>
            {getInitials(name)}
            {online !== undefined && (
                <span
                    className={`absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full border-2 border-white ${online ? 'bg-success-light' : 'bg-gray-400'
                        }`}
                />
            )}
        </div>
    );
}
