'use client';

const STATUS_STYLES: Record<string, string> = {
  new: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-200',
  researching: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
  qualified: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
  review: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  approved: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
  rejected: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
  scheduled: 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300',
  sent: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300',
  replied: 'bg-teal-100 text-teal-800 dark:bg-teal-900/40 dark:text-teal-300',
  interested: 'bg-lime-100 text-lime-800 dark:bg-lime-900/40 dark:text-lime-300',
  not_interested: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300',
  unsubscribed: 'bg-pink-100 text-pink-800 dark:bg-pink-900/40 dark:text-pink-300',
  bounced: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300',
  do_not_contact: 'bg-zinc-100 text-zinc-700 dark:bg-zinc-700 dark:text-zinc-300',
  // campaign statuses
  draft: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-200',
  ready: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
  active: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
  paused: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300',
  completed: 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300',
};

interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md';
}

export default function StatusBadge({ status, size = 'sm' }: StatusBadgeProps) {
  const style = STATUS_STYLES[status] || STATUS_STYLES.new;
  const label = status.charAt(0).toUpperCase() + status.slice(1).replace(/_/g, ' ');
  return (
    <span
      className={`inline-flex items-center rounded-full font-medium ${style} ${
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm'
      }`}
    >
      {label}
    </span>
  );
}
