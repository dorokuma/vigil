import type { ServerStatus } from '../pages/Dashboard'

interface Props {
  server: ServerStatus
}

export default function ServerCard({ server }: Props) {
  const statusColor = server.online ? 'bg-green-500' : 'bg-red-500'
  const latencyColor =
    server.latency === 0 ? 'text-gray-500' : server.latency < 50 ? 'text-green-400' : server.latency < 150 ? 'text-yellow-400' : 'text-red-400'

  return (
    <div className={`rounded-xl border p-5 transition-all duration-200 hover:scale-[1.02] ${
      server.online ? 'border-gray-800 bg-gray-900/80' : 'border-red-900/50 bg-gray-900/40 opacity-70'
    }`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`w-2.5 h-2.5 rounded-full ${statusColor} shadow-lg ${server.online ? 'shadow-green-500/30' : 'shadow-red-500/30'}`} />
          <span className="font-semibold text-base">{server.name}</span>
        </div>
        <span className="text-xs text-gray-500">{server.location}</span>
      </div>

      <div className="grid grid-cols-3 gap-3 text-center text-sm">
        <div>
          <div className="text-gray-500 text-xs mb-1">延迟</div>
          <div className={`font-mono font-bold ${latencyColor}`}>
            {server.online ? `${server.latency}ms` : '—'}
          </div>
        </div>
        <div>
          <div className="text-gray-500 text-xs mb-1">丢包</div>
          <div className={`font-mono font-bold ${server.packetLoss === 0 ? 'text-green-400' : 'text-red-400'}`}>
            {server.online ? `${server.packetLoss}%` : '—'}
          </div>
        </div>
        <div>
          <div className="text-gray-500 text-xs mb-1">运行</div>
          <div className="font-mono font-bold text-gray-300 text-xs">{server.uptime}</div>
        </div>
      </div>

      {/* 资源条 */}
      <div className="mt-4 space-y-2">
        <MiniBar label="CPU" value={server.cpu} color="cyan" />
        <MiniBar label="内存" value={server.memory} color="purple" />
        <MiniBar label="磁盘" value={server.disk} color="amber" />
      </div>
    </div>
  )
}

function MiniBar({ label, value, color }: { label: string; value: number; color: string }) {
  const colorMap: Record<string, string> = {
    cyan: 'bg-cyan-500',
    purple: 'bg-purple-500',
    amber: 'bg-amber-500',
  }
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-6 text-gray-500">{label}</span>
      <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${colorMap[color]}`}
          style={{ width: `${value}%` }}
        />
      </div>
      <span className="w-8 text-right font-mono text-gray-400">{value}%</span>
    </div>
  )
}
