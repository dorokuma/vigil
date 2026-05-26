import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, AlertOctagon, Plus, Trash2 } from 'lucide-react'

interface Alert {
  id: number
  time: string
  hostname: string
  type: string
  severity: 'warning' | 'critical'
  message: string
  timestamp: number
}

export default function Alerts() {
  const {
    data: alerts = [],
    isLoading,
    refetch,
  } = useQuery<Alert[]>({
    queryKey: ['alerts'],
    queryFn: async () => {
      const res = await fetch('/api/alerts')
      if (!res.ok) throw new Error('Failed to fetch')
      return res.json()
    },
    refetchInterval: 10_000,
  })

  const addDemoAlert = async () => {
    const demo = {
      hostname: ['hongkong', 'tokyo', 'beijing'][Math.floor(Math.random() * 3)],
      type: 'cpu_high',
      severity: Math.random() > 0.5 ? 'warning' : 'critical' as 'warning' | 'critical',
      message: '模拟告警 - ' + new Date().toLocaleTimeString(),
    }
    await fetch('/api/alerts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(demo),
    })
    refetch()
  }

  const clearHistory = async () => {
    await fetch('/api/alerts', { method: 'DELETE' })
    refetch()
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 + 操作 */}
      <div className="flex items-start justify-between animate-fade-in">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
            告警历史
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
            实时来自 Python Bot 的告警 · 每10秒刷新
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={addDemoAlert}
            className="flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg
                       text-zinc-600 bg-zinc-100 hover:bg-zinc-200
                       dark:text-zinc-300 dark:bg-zinc-800 dark:hover:bg-zinc-700
                       transition-colors"
          >
            <Plus size={14} />
            模拟告警
          </button>
          <button
            onClick={clearHistory}
            className="flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg
                       text-rose-600 bg-rose-50 hover:bg-rose-100
                       dark:text-rose-400 dark:bg-rose-500/10 dark:hover:bg-rose-500/20
                       transition-colors"
          >
            <Trash2 size={14} />
            清空
          </button>
        </div>
      </div>

      {/* 告警列表 */}
      <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200/60 dark:border-zinc-800/60 shadow-sm dark:shadow-none animate-fade-in">
        {isLoading ? (
          <div className="p-8 space-y-4 animate-pulse">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-16 bg-zinc-100 dark:bg-zinc-800 rounded-lg" />
            ))}
          </div>
        ) : alerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-zinc-400 dark:text-zinc-500">
            <AlertTriangle size={32} className="mb-3 opacity-50" />
            <p className="text-sm">暂无告警记录</p>
            <p className="text-xs mt-1">系统运行正常，没有需要关注的事件</p>
          </div>
        ) : (
          <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {alerts.map((alert, index) => {
              const isCritical = alert.severity === 'critical'
              return (
                <div
                  key={alert.id}
                  className={`relative flex items-start gap-4 px-5 py-4 transition-colors
                    hover:bg-zinc-50 dark:hover:bg-zinc-800/30`}
                >
                  {/* 左侧时间线指示器 */}
                  <div className="flex flex-col items-center shrink-0 pt-0.5">
                    <div
                      className={`w-2.5 h-2.5 rounded-full ring-4 ${
                        isCritical
                          ? 'bg-rose-500 ring-rose-500/20 dark:ring-rose-500/30'
                          : 'bg-amber-500 ring-amber-500/20 dark:ring-amber-500/30'
                      }`}
                    />
                    {index < alerts.length - 1 && (
                      <div className="w-px flex-1 bg-zinc-200 dark:bg-zinc-700 mt-2" />
                    )}
                  </div>

                  {/* 告警内容 */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-md ${
                          isCritical
                            ? 'bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-300'
                            : 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300'
                        }`}
                      >
                        {isCritical ? <AlertOctagon size={10} /> : <AlertTriangle size={10} />}
                        {isCritical ? 'CRITICAL' : 'WARNING'}
                      </span>
                      <span className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
                        {alert.hostname}
                      </span>
                      <span className="text-xs text-zinc-400 dark:text-zinc-500 font-mono">
                        {alert.time}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
                      {alert.message}
                    </p>
                  </div>

                  {/* 右侧序号 */}
                  <span className="shrink-0 text-xs text-zinc-300 dark:text-zinc-600 tabular-nums">
                    #{alerts.length - index}
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
