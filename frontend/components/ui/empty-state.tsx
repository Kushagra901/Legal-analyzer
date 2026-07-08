import React from "react";

interface EmptyStateProps {
  title: string;
  description: string;
  actionText?: string;
  onAction?: () => void;
}

export const EmptyState = ({ title, description, actionText, onAction }: EmptyStateProps) => {
  return (
    <div className="border border-[#e0dfdb] border-dashed bg-[#faf9f6] p-12 text-center flex flex-col items-center justify-center space-y-4 rounded-none min-h-[300px]">
      {/* Skeleton block to give contextual feel */}
      <div className="w-16 h-16 border border-[#e0dfdb] bg-white flex flex-col justify-around p-2 opacity-60">
        <div className="h-2 w-full bg-[#e0dfdb]"></div>
        <div className="h-2 w-3/4 bg-[#e0dfdb]"></div>
        <div className="h-2 w-1/2 bg-[#e0dfdb]"></div>
      </div>
      <div className="space-y-1">
        <h3 className="font-serif text-base text-[#0d1b2a]">{title}</h3>
        <p className="text-xs text-[#5c5b57] max-w-sm mx-auto leading-relaxed">{description}</p>
      </div>
      {actionText && onAction && (
        <button
          onClick={onAction}
          className="bg-[#0d1b2a] hover:bg-[#1a2f4c] text-[#faf9f6] text-xs font-semibold px-4 py-2 uppercase tracking-wider transition-colors duration-200"
        >
          {actionText}
        </button>
      )}
    </div>
  );
};
