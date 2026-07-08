import React from "react";

interface RiskBadgeProps {
  level: "low" | "medium" | "high";
}

export const RiskBadge = ({ level }: RiskBadgeProps) => {
  let colorClass = "";
  switch (level) {
    case "low":
      colorClass = "bg-green-100 text-green-800 border-green-200";
      break;
    case "medium":
      colorClass = "bg-yellow-100 text-yellow-800 border-yellow-200";
      break;
    case "high":
      colorClass = "bg-red-100 text-red-800 border-red-200";
      break;
  }

  return (
    <span className={`inline-block border px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${colorClass}`}>
      {level} Risk
    </span>
  );
};
