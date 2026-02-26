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
