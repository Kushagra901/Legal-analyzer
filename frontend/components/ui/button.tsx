import React from "react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline";
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className = "", variant = "primary", children, ...props }, ref) => {
    const baseStyles = "px-4 py-2 text-xs font-semibold uppercase tracking-wider rounded-none transition-colors duration-200 focus:outline-none border";
    let variantStyles = "";

    switch (variant) {
      case "primary":
        variantStyles = "bg-[#0d1b2a] border-[#0d1b2a] text-[#faf9f6] hover:bg-[#1a2f4c]";
        break;
      case "secondary":
        variantStyles = "bg-white border-[#e0dfdb] text-[#1c1c1c] hover:bg-[#faf9f6]";
        break;
      case "outline":
        variantStyles = "bg-transparent border-[#0d1b2a] text-[#0d1b2a] hover:bg-[#0d1b2a] hover:text-[#faf9f6]";
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
