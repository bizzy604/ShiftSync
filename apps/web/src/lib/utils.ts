/**
 * @file /apps/web/src/lib/utils.ts
 *
 * @description
 * TypeScript module implementing `utils` functionality.
 *
 * @dependencies
 * - (No in-repo dependents detected.)
 *
 * @importance
 * This module is important for maintainable frontend behavior around `utils`.
 */

import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
