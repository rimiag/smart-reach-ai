'use client';

export interface StatItem {
  label: string;
  value: number | string;
}

interface StatsCardsProps {
  stats: StatItem[];
}

export default function StatsCards({ stats }: StatsCardsProps) {
  if (!stats.length) return null;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 text-center"
        >
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {stat.value}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">{stat.label}</div>
        </div>
      ))}
    </div>
  );
}
