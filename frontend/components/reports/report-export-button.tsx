import React from "react";

export const ReportExportButton = () => {
  const handleExport = () => {
    if (typeof window !== "undefined") {
      window.print();
    }
  };

  return (
    <button
      onClick={handleExport}
      className="bg-[#0d1b2a] hover:bg-[#1a2f4c] text-[#faf9f6] text-xs font-semibold px-4 py-2 uppercase tracking-wider transition-colors duration-200"
    >
      Export PDF
    </button>
  );
};
