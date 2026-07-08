import React from "react";

interface ClauseHighlightProps {
  title: string;
  riskLevel: "low" | "medium" | "high";
  text: string;
}

export const ClauseHighlight = ({ title, riskLevel, text }: ClauseHighlightProps) => {
  let riskColor = "";
  switch (riskLevel) {
    case "low":
      riskColor = "bg-green-50 text-green-800 border-green-200";
      break;
    case "medium":
      riskColor = "bg-yellow-50 text-yellow-800 border-yellow-200";
      break;
    case "high":
      riskColor = "bg-red-50 text-red-800 border-red-200";
      break;
  }

  return (
    <div className={`p-4 border ${riskColor} rounded-none`}>
      <h4 className="text-xs font-bold uppercase tracking-wider mb-2">{title}</h4>
      <p className="text-xs leading-relaxed font-mono select-all bg-white/50 p-2 border border-current/10">
        {text}
      </p>
    </div>
  );
};
