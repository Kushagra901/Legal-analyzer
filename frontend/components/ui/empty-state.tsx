import React from "react";

export interface EmptyStateProps {
  title: string;
  description: string;
  actionText?: string;
  actionLabel?: string;
  onAction?: () => void;
}

export const EmptyState = ({ title, description, actionText, actionLabel, onAction }: EmptyStateProps) => {
  const buttonText = actionText || actionLabel;
  return (
    <div className="border border-[var(--border-subtle)] border-dashed bg-[var(--bg-page)] p-12 text-center flex flex-col items-center justify-center space-y-4 rounded-none min-h-[300px]">
      {/* Skeleton block for designed content representation */}
      <div className="w-16 h-16 border border-[var(--border-subtle)] bg-[var(--bg-surface)] flex flex-col justify-around p-2 opacity-60">
        <div className="h-2 w-full bg-[var(--border-subtle)]"></div>
        <div className="h-2 w-3/4 bg-[var(--border-subtle)]"></div>
        <div className="h-2 w-1/2 bg-[var(--border-subtle)]"></div>
      </div>
      <div className="space-y-1">
        <h3 className="font-serif text-base text-[var(--accent-primary)] font-bold">{title}</h3>
        <p className="text-xs text-[var(--text-muted)] max-w-sm mx-auto leading-relaxed">{description}</p>
      </div>
      {buttonText && onAction && (
        <button
          onClick={onAction}
          className="bg-[var(--accent-primary)] hover:bg-[var(--accent-hover)] text-white text-xs font-semibold px-4 py-2 uppercase tracking-wider transition-colors duration-150 cursor-pointer"
        >
          {buttonText}
        </button>
      )}
    </div>
  );
};
