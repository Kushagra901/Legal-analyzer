import React from "react";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "low" | "medium" | "high" | "neutral";
}

export const Badge = ({ className = "", variant = "neutral", children, ...props }: BadgeProps) => {
  const badgeStyles =
    "inline-flex items-center border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded-none";
  let variantStyles = "";

  switch (variant) {
    case "low":
      variantStyles = "bg-[var(--risk-low-bg)] text-[var(--risk-low)] border-[var(--risk-low)]";
      break;
    case "medium":
      variantStyles = "bg-[var(--risk-medium-bg)] text-[var(--risk-medium)] border-[var(--risk-medium)]";
      break;
    case "high":
      variantStyles = "bg-[var(--risk-high-bg)] text-[var(--risk-high)] border-[var(--risk-high)]";
      break;
    case "neutral":
      variantStyles = "bg-[var(--bg-page)] text-[var(--text-muted)] border-[var(--border-subtle)]";
      break;
  }

  return (
    <div className={`${badgeStyles} ${variantStyles} ${className}`} {...props}>
      {children}
    </div>
  );
};
