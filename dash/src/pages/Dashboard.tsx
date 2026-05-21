import { useQuery } from '@tanstack/react-query'
import ServerCard from '../components/ServerCard'
import StatsBar from '../components/StatsBar'

export interface ServerStatus {
  name: string
  location: string
  online: boolean
  latency: number
  packetLoss: number
  uptime: string
  cpu: number
  memory: number
  disk: number
}


export default function Dashboard() {
  const { data: servers, isLoading } = useQuery<ServerStatus[]>({
    queryKey: ['servers'],
    queryFn: async () => {
      const res = await fetch('/api/servers')
      if (!res.ok) throw new Error('Failed to fetch')
      return res.json()
    },
    refetchInterval: 30_000,
  })

  const online = servers?.filter((s) => s.online).length ?? 0
  const total = servers?.length ?? 0
  const avgLatency = servers
    ? Math.round(servers.filter((s) => s.online).reduce((a, b) => a + b.latency, 0) / online)
    : 0

  return (
    <div className="space-y-6">
      <StatsBar online={online} total={total} avgLatency={avgLatency} />

      {isLoading ? (
        <div className="text-center py-20 text-gray-500 text-lg animate-pulse">
          🌀 加载中...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {servers?.map((server) => (
            <ServerCard key={server.name} server={server} />
          ))}
        </div>
      )}
    </div>
  )
}
