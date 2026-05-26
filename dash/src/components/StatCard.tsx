import type { LucideIcon } from 'lucide-react'

interface StatCardProps {
  icon: LucideIcon
  label: string
  value: string
  subtext?: string
  barValue?: number // 0-100, 可选进度条
  accent: 'cyan' | 'emerald' | 'violet' | 'amber' | 'rose'
}

const accentStyles = {
  cyan: {
    bg: 'bg-cyan-50 dark:bg-cyan-500/10',
    icon: 'text-cyan-600 dark:text-cyan-400',
    bar: 'bg-cyan-500 dark:bg-cyan-400',
  },
  emerald: {
    bg: 'bg-emerald-50 dark:bg-emerald-500/10',
    icon: 'text-emerald-600 dark:text-emerald-400',
    bar: 'bg-emerald-500 dark:bg-emerald-400',
  },
  violet: {
    bg: 'bg-violet-50 dark:bg-violet-500/10',
    icon: 'text-violet-600 dark:text-violet-400',
    bar: 'bg-violet-500 dark:bg-violet-400',
  },
  amber: {
    bg: 'bg-amber-50 dark:bg-amber-500/10',
    icon: 'text-amber-600 dark:text-amber-400',
    bar: 'bg-amber-500 dark:bg-amber-400',
  },
  rose: {
    bg: 'bg-rose-50 dark:bg-rose-500/10',
    icon: 'text-rose-600 dark:text-rose-400',
    bar: 'bg-rose-500 dark:bg-rose-400',
  },
}

export function StatCard({ icon: Icon, label, value, subtext, barValue, accent }: StatCardProps) {
  const s = accentStyles[accent]

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200/60 dark:border-zinc-800/60 p-5 shadow-sm dark:shadow-none animate-fade-in">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <div className={`shrink-0 w-10 h-10 rounded-xl flex items-center justify-center ${s.bg}`}>
            <Icon size={20} className={s.icon} />
          </div>
          <span className="text-sm font-medium text-zinc-500 dark:text-zinc-400 truncate">
            {label}
          </span>
        </div>
        <span className="shrink-0 text-2xl font-semibold tracking-tight tabular-nums text-zinc-900 dark:text-zinc-100">
          {value}
        </span>
      </div>
      {barValue !== undefined && (
        <div className="mt-3">
          <div className="h-1.5 rounded-full bg-zinc-100 dark:bg-zinc-800 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${s.bar}`}
              style={{ width: `${Math.max(0, Math.min(barValue, 100))}%` }}
            />
          </div>
        </div>
      )}
      {subtext && (
        <div className="mt-1.5 text-xs text-zinc-400 dark:text-zinc-500">{subtext}</div>
      )}
    </div>
  )
}
