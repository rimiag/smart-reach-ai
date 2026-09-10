'use client';

const STAGES = ['Setup', 'Research', 'Qualify & Draft', 'Review & Send'];

interface StageIndicatorProps {
  /** 0-based index of the current stage */
  current: number;
  /** all stages completed */
  done?: boolean;
}

export default function StageIndicator({ current, done = false }: StageIndicatorProps) {
  return (
    <div className="flex items-center gap-2 mb-6" aria-label="Campaign progress">
      {STAGES.map((stage, index) => {
        const isComplete = done || index < current;
        const isCurrent = !done && index === current;
        return (
          <div key={stage} className="flex items-center gap-2">
            <div
              className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
                isComplete || isCurrent
                  ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300'
                  : 'bg-gray-100 text-gray-400 dark:bg-gray-700 dark:text-gray-500'
              }`}
            >
              {(isComplete || isCurrent) && (
                <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
                  {isComplete ? (
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  ) : (
                    <circle cx="10" cy="10" r="4" />
                  )}
                </svg>
              )}
              {stage}
            </div>
            {index < STAGES.length - 1 && (
              <span className="text-gray-300 dark:text-gray-600">→</span>
            )}
          </div>
        );
      })}
    </div>
  );
}
