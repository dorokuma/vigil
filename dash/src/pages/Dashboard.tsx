import { useQuery } from '@tanstack/react-query';
import { ServersTable } from '../components/ServersTable';

interface Server {
  name: string;
  location: string;
  online: boolean;
  latency: number;
  packetLoss: number;
  uptime: string;
  cpu: number;
  memory: number;
  disk: number;
}

export default function Dashboard() {
  const { data: servers = [], isLoading } = useQuery<Server[]>({
    queryKey: ['servers'],
    queryFn: async () => {
      const res = await fetch('/api/servers');
      if (!res.ok) throw new Error('Failed to fetch');
      return res.json();
    },
    refetchInterval: 15000,
  });

  const onlineCount = servers.filter(s => s.online).length;
  const avgCpu = servers.length 
    ? Math.round(servers.reduce((sum, s) => sum + s.cpu, 0) / servers.length) 
    : 0;
  const avgLatency = servers.length
    ? Math.round(servers.reduce((sum, s) => sum + (s.latency || 0), 0) / servers.length)
    : 0;

  return (
    <div className="p-4 sm:p-8">
      <div className="max-w-7xl mx-auto space-y-6 sm:space-y-8">
        {/* Header: Logo + Stats */}
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
          <div className="flex items-center gap-4">
            <img src="/favicon.svg" alt="Vigil" className="w-10 h-10 sm:w-12 sm:h-12" />
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-800 tracking-tight">Vigil</h1>
          </div>
          {/* Stats bar */}
          <div className="flex items-center gap-4 sm:gap-6 overflow-x-auto pb-1 sm:pb-0">
            <div className="text-right shrink-0">
              <div className="text-xs text-gray-400 font-medium uppercase tracking-wider">在线</div>
              <div className="text-xl sm:text-2xl font-bold text-emerald-500 tabular-nums">
                {onlineCount} <span className="text-sm text-gray-400">/ {servers.length}</span>
              </div>
            </div>
            <div className="w-px h-8 bg-gray-200 shrink-0" />
            <div className="text-right shrink-0">
              <div className="text-xs text-gray-400 font-medium uppercase tracking-wider">平均 CPU</div>
              <div className="text-xl sm:text-2xl font-bold text-sky-500 tabular-nums">{avgCpu}<span className="text-sm text-gray-400">%</span></div>
            </div>
            <div className="w-px h-8 bg-gray-200 shrink-0" />
            <div className="text-right shrink-0">
              <div className="text-xs text-gray-400 font-medium uppercase tracking-wider">平均延迟</div>
              <div className="text-xl sm:text-2xl font-bold text-teal-500 tabular-nums">{avgLatency}<span className="text-sm text-gray-400">ms</span></div>
            </div>
          </div>
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
          <div className="bg-white/80 backdrop-blur-sm border border-gray-100 rounded-2xl p-4 sm:p-5 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-emerald-100 rounded-xl flex items-center justify-center shrink-0">
                <svg className="w-5 h-5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div className="min-w-0">
                <div className="text-xs text-gray-400 uppercase tracking-wider font-medium">正常节点</div>
                <div className="text-xl font-bold text-gray-800">{onlineCount} / {servers.length}</div>
              </div>
            </div>
          </div>
          <div className="bg-white/80 backdrop-blur-sm border border-gray-100 rounded-2xl p-4 sm:p-5 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-sky-100 rounded-xl flex items-center justify-center shrink-0">
                <svg className="w-5 h-5 text-sky-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <div className="min-w-0">
                <div className="text-xs text-gray-400 uppercase tracking-wider font-medium">平均 CPU</div>
                <div className="text-xl font-bold text-gray-800">{avgCpu}%</div>
              </div>
            </div>
          </div>
          <div className="bg-white/80 backdrop-blur-sm border border-gray-100 rounded-2xl p-4 sm:p-5 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-teal-100 rounded-xl flex items-center justify-center shrink-0">
                <svg className="w-5 h-5 text-teal-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <div className="min-w-0">
                <div className="text-xs text-gray-400 uppercase tracking-wider font-medium">更新频率</div>
                <div className="text-xl font-bold text-gray-800">15s</div>
              </div>
            </div>
          </div>
        </div>

        {/* 服务器列表 */}
        <div className="bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-4 sm:px-6 py-4 border-b border-gray-100">
            <h2 className="text-base sm:text-lg font-semibold text-gray-800">服务器列表</h2>
            <div className="text-xs px-2 sm:px-3 py-1.5 bg-sky-50 text-sky-600 rounded-full font-medium shrink-0">15s 刷新</div>
          </div>
          <ServersTable data={servers} isLoading={isLoading} />
        </div>

        {/* Footer */}
        <div className="flex items-center justify-center gap-2 text-xs text-gray-400 pt-4 pb-2">
          <span className="inline-block w-1 h-1 rounded-full bg-gray-300" />
          Vigil
          <span className="inline-block w-1 h-1 rounded-full bg-gray-300" />
          Cloudflare 白嫖计划
        </div>
      </div>
    </div>
  );
}
