import React from "react";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "low" | "medium" | "high" | "neutral";
}

export const Badge = ({ className = "", variant = "neutral", children, ...props }: BadgeProps) => {
  const badgeStyles = "inline-flex items-center border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded-none";
  let variantStyles = "";

  switch (variant) {
    case "low":
      variantStyles = "bg-green-50 text-green-700 border-green-200";
      break;
    case "medium":
      variantStyles = "bg-yellow-50 text-yellow-700 border-yellow-200";
      break;
    case "high":
      variantStyles = "bg-red-50 text-red-700 border-red-200";
      break;
    case "neutral":
      variantStyles = "bg-[#faf9f6] text-[#5c5b57] border-[#e0dfdb]";
      break;
  }

  return (
    <div className={`${badgeStyles} ${variantStyles} ${className}`} {...props}>
      {children}
    </div>
  );
};
