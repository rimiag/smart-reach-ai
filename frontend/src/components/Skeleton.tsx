'use client';

interface SkeletonProps {
  rows?: number;
  className?: string;
}

/** Pulse-loading placeholder rows, used instead of "Loading..." text. */
export default function Skeleton({ rows = 3, className = '' }: SkeletonProps) {
  return (
    <div className={`space-y-3 ${className}`} role="status" aria-label="Loading">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-5 animate-pulse"
        >
          <div className="h-4 w-1/3 rounded bg-gray-200 dark:bg-gray-700" />
          <div className="mt-3 h-3 w-2/3 rounded bg-gray-100 dark:bg-gray-700/60" />
          <div className="mt-2 h-3 w-1/2 rounded bg-gray-100 dark:bg-gray-700/60" />
        </div>
      ))}
      <span className="sr-only">Loading…</span>
    </div>
  );
}
