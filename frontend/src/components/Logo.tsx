'use client';

import Link from 'next/link';

interface LogoProps {
  /** compact = icon + name on one line (sidebar); full = name + tagline stacked */
  variant?: 'compact' | 'full';
  /** light text for dark backgrounds (sidebar / landing hero) */
  onDark?: boolean;
  href?: string | null;
}

export default function Logo({ variant = 'compact', onDark = false, href = '/' }: LogoProps) {
  const nameColor = onDark ? 'text-white' : 'text-gray-900 dark:text-white';
  const taglineColor = onDark ? 'text-blue-200' : 'text-gray-500 dark:text-gray-400';

  const mark = (
    <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-blue-600 shadow-sm">
      <svg className="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122"
        />
      </svg>
    </span>
  );

  const body =
    variant === 'full' ? (
      <span className="flex flex-col">
        <span className={`text-lg font-bold leading-tight ${nameColor}`}>
          Smart Reach <span className="text-indigo-500">AI</span>
        </span>
        <span className={`text-[11px] font-medium tracking-wide ${taglineColor}`}>
          Discover. Engage. Convert.
        </span>
      </span>
    ) : (
      <span className={`text-base font-bold leading-tight ${nameColor}`}>
        Smart Reach <span className="text-indigo-500">AI</span>
      </span>
    );

  const content = (
    <span className="flex items-center gap-2.5">
      {mark}
      {body}
    </span>
  );

  if (href === null) return content;
  return (
    <Link href={href} className="inline-flex">
      {content}
    </Link>
  );
}
