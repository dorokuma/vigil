interface Props {
  online: number
  total: number
  avgLatency: number
}

export default function StatsBar({ online, total, avgLatency }: Props) {
  return (
    <div className="grid grid-cols-3 gap-4">
      <div className="rounded-xl border border-gray-800 bg-gray-900/60 p-4 text-center">
        <div className="text-2xl font-bold text-cyan-400">{online}/{total}</div>
        <div className="text-xs text-gray-500 mt-1">在线 / 总数</div>
      </div>
      <div className="rounded-xl border border-gray-800 bg-gray-900/60 p-4 text-center">
        <div className="text-2xl font-bold text-green-400">{(online / total * 100).toFixed(0)}%</div>
        <div className="text-xs text-gray-500 mt-1">在线率</div>
      </div>
      <div className="rounded-xl border border-gray-800 bg-gray-900/60 p-4 text-center">
        <div className="text-2xl font-bold text-amber-400">{avgLatency}ms</div>
        <div className="text-xs text-gray-500 mt-1">平均延迟</div>
      </div>
    </div>
  )
}
