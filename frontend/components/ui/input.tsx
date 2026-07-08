import React from "react";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className = "", type = "text", ...props }, ref) => {
    return (
      <input
        type={type}
        ref={ref}
        className={`w-full border border-[#e0dfdb] px-3 py-2 text-xs bg-[#faf9f6] focus:outline-none focus:border-[#0d1b2a] rounded-none ${className}`}
        {...props}
      />
    );
  }
);

Input.displayName = "Input";
