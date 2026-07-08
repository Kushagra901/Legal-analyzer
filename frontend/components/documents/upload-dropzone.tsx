import React from "react";

export const UploadDropzone = () => {
  return (
    <div className="border border-dashed border-[#e0dfdb] bg-[#faf9f6] hover:bg-[#f5f4f0] h-48 flex flex-col items-center justify-center text-[#5c5b57] text-xs p-6 cursor-pointer transition-colors duration-150">
      <svg
        className="w-8 h-8 text-[#8a8985] mb-3"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="1.5"
          d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        />
      </svg>
      <span className="font-semibold text-[#0d1b2a]">Drag & drop contract file here</span>
      <span className="text-[10px] text-[#8a8985] mt-1">PDF, TXT, or DOCX (max. 10MB)</span>
    </div>
  );
};
