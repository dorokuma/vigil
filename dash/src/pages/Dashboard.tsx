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
    refetchInterval: 15000, // 每15秒自动刷新
  });

  const onlineCount = servers.filter(s => s.online).length;
  const avgCpu = servers.length 
    ? Math.round(servers.reduce((sum, s) => sum + s.cpu, 0) / servers.length) 
    : 0;

  return (
    <div className="min-h-screen bg-zinc-950 text-white p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-4xl font-semibold tracking-tight">Vigil Dashboard</h1>
            <p className="text-zinc-400 mt-1">实时服务器监控 · Powered by Cloudflare</p>
          </div>
          <div className="text-right">
            <div className="text-sm text-zinc-500">在线服务器</div>
            <div className="text-3xl font-semibold tabular-nums text-green-400">
              {onlineCount} / {servers.length}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
            <div className="text-sm text-zinc-500">平均 CPU</div>
            <div className="text-5xl font-semibold tabular-nums mt-2">{avgCpu}<span className="text-2xl text-zinc-500">%</span></div>
          </div>
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
            <div className="text-sm text-zinc-500">总服务器</div>
            <div className="text-5xl font-semibold tabular-nums mt-2">{servers.length}</div>
          </div>
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
            <div className="text-sm text-zinc-500">更新频率</div>
            <div className="text-5xl font-semibold tabular-nums mt-2">15s</div>
          </div>
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-3xl p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold">服务器列表</h2>
            <div className="text-xs px-3 py-1 bg-zinc-800 rounded-full">每15秒自动刷新</div>
          </div>
          <ServersTable data={servers} isLoading={isLoading} />
        </div>

        <div className="text-center text-xs text-zinc-500 pt-8">
          Vigil + TanStack + Cloudflare Pages · 全球边缘加速 · 完全免费
        </div>
      </div>
    </div>
  );
}
