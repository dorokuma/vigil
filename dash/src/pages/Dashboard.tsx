import { useQuery } from '@tanstack/react-query'
import { Server, Cpu, HardDrive, Gauge } from 'lucide-react'
import { StatCard } from '../components/StatCard'
import { ServersTable } from '../components/ServersTable'
import type { EnrichedServer } from '../types'

export default function Dashboard() {
  const { data: servers = [], isLoading } = useQuery<EnrichedServer[]>({
    queryKey: ['servers'],
    queryFn: async () => {
      const res = await fetch('/api/servers')
      if (!res.ok) throw new Error('Failed to fetch')
      return res.json()
    },
    refetchInterval: 15_000,
  })

  const onlineCount = servers.filter((s) => s.online).length
  const totalCount = servers.length
  const avgCpu = totalCount
    ? Math.round(servers.reduce((sum, s) => sum + s.cpu, 0) / totalCount)
    : 0
  const avgMem = totalCount
    ? Math.round(servers.reduce((sum, s) => sum + s.memory, 0) / totalCount)
    : 0
  const avgLat = totalCount
    ? Math.round(
        servers.reduce((sum, s) => {
          const lat = typeof s.latency === 'number' ? s.latency : 0
          return sum + lat
        }, 0) / totalCount,
      )
    : 0

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="animate-fade-in">
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">
          服务器监控
        </h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
          实时状态 · 每15秒自动刷新 · Cloudflare 全球加速
        </p>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="animate-fade-in animate-fade-in-d1">
          <StatCard
            icon={Server}
            label="在线服务器"
            value={`${onlineCount} / ${totalCount}`}
            subtext={totalCount > 0 ? `${Math.round((onlineCount / totalCount) * 100)}% 在线率` : '暂无数据'}
            accent="emerald"
          />
        </div>
        <div className="animate-fade-in animate-fade-in-d2">
          <StatCard
            icon={Cpu}
            label="平均 CPU"
            value={`${avgCpu}%`}
            barValue={avgCpu}
            subtext="所有服务器平均"
            accent="cyan"
          />
        </div>
        <div className="animate-fade-in animate-fade-in-d3">
          <StatCard
            icon={HardDrive}
            label="平均内存"
            value={`${avgMem}%`}
            barValue={avgMem}
            subtext="所有服务器平均"
            accent="violet"
          />
        </div>
        <div className="animate-fade-in animate-fade-in-d4">
          <StatCard
            icon={Gauge}
            label="平均延迟"
            value={avgLat > 0 ? `${avgLat}ms` : '—'}
            subtext="全球平均响应"
            accent="amber"
          />
        </div>
      </div>

      {/* 服务器列表 */}
      <ServersTable data={servers} isLoading={isLoading} />
    </div>
  )
}
