import React from "react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline";
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className = "", variant = "primary", children, ...props }, ref) => {
    const baseStyles =
      "px-4 py-2 text-xs font-semibold uppercase tracking-wider rounded-none transition-colors duration-150 focus:outline-none border border-solid cursor-pointer inline-flex items-center justify-center";
    let variantStyles = "";

    switch (variant) {
      case "primary":
        variantStyles =
          "bg-[var(--accent-primary)] border-[var(--accent-primary)] text-white hover:bg-[var(--accent-hover)]";
        break;
      case "secondary":
        variantStyles =
          "bg-[var(--bg-surface)] border-[var(--border-subtle)] text-[var(--text-main)] hover:bg-[var(--bg-page)]";
        break;
      case "outline":
        variantStyles =
          "bg-transparent border-[var(--accent-primary)] text-[var(--accent-primary)] hover:bg-[var(--accent-primary)] hover:text-white";
        break;
    }

    return (
      <button
        ref={ref}
        className={`${baseStyles} ${variantStyles} ${className}`}
        {...props}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";
