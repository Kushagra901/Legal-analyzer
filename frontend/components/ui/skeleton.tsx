import React from "react";

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  className?: string;
}

export function Skeleton({ className = "", ...props }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse bg-[var(--border-subtle)] opacity-70 rounded-none ${className}`}
      {...props}
    />
  );
}

export default Skeleton;
