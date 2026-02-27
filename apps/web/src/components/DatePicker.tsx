/**
 * @file /apps/web/src/components/DatePicker.tsx
 *
 * @description
 * Shared UI/component module for `DatePicker` used across multiple screens.
 *
 * @dependencies
 * - (No in-repo dependents detected.)
 *
 * @importance
 * This module provides reusable UI primitives that influence consistency and
 * maintainability.
 */

import React from "react";
import ReactDatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import { cn } from "../lib/utils";

/**
 * DatePicker
 * A thin wrapper around react-datepicker with Tailwind-friendly className
 * Props: forwards all ReactDatePicker props. Use JSDoc for editor help.
 */
export function DatePicker(props: React.ComponentProps<typeof ReactDatePicker>) {
  return (
    <ReactDatePicker
      wrapperClassName={cn("date-picker-wrapper")}
      popperClassName={cn("date-picker-popper")}
      className={cn("input", props.className ?? "")}
      {...props}
    />
  );
}

export default DatePicker;
