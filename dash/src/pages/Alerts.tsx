import { useQuery } from '@tanstack/react-query';

interface Alert {
  id: number;
  time: string;
  hostname: string;
  type: string;
  severity: 'warning' | 'critical';
  message: string;
  timestamp: number;
}

export default function Alerts() {
  const { data: alerts = [], isLoading, refetch } = useQuery<Alert[]>({
    queryKey: ['alerts'],
    queryFn: async () => {
      const res = await fetch('/api/alerts');
      if (!res.ok) throw new Error('Failed to fetch');
      return res.json();
    },
    refetchInterval: 10000,
  });

  const addDemoAlert = async () => {
    const demo = {
      hostname: ['hongkong', 'tokyo', 'beijing'][Math.floor(Math.random() * 3)],
      type: 'cpu_high',
      severity: Math.random() > 0.5 ? 'warning' : 'critical' as const,
      message: '模拟告警 - ' + new Date().toLocaleTimeString(),
    };
    await fetch('/api/alerts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(demo),
    });
    refetch();
  };

  const clearHistory = async () => {
    localStorage.removeItem('vigil-alerts');
    refetch();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-gray-800">告警历史</h2>
          <p className="text-sm text-gray-400 mt-1">来自 Vigil Collector 的实时告警 · 每10秒刷新</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={addDemoAlert}
            className="px-4 py-2 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-xl text-sm text-gray-600 transition-all"
          >
            + 添加模拟告警
          </button>
          <button
            onClick={clearHistory}
            className="px-4 py-2 bg-red-50 hover:bg-red-100 border border-red-200 rounded-xl text-sm text-red-500 transition-all"
          >
            清空历史
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-16 text-gray-400">加载中...</div>
      ) : alerts.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          暂无告警记录
        </div>
      ) : (
        <div className="space-y-2">
          {alerts.map((alert, index) => (
            <div
              key={alert.id}
              className={`p-4 rounded-xl border ${alert.severity === 'critical' 
                ? 'border-red-200 bg-red-50/50' 
                : 'border-amber-200 bg-amber-50/50'}`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <span className={`mt-0.5 px-2 py-0.5 text-xs rounded-full font-medium ${
                    alert.severity === 'critical' 
                      ? 'bg-red-100 text-red-600' 
                      : 'bg-amber-100 text-amber-600'
                  }`}>
                    {alert.severity === 'critical' ? '严重' : '警告'}
                  </span>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-400 font-mono">{alert.time}</span>
                      <span className="text-sm font-medium text-gray-700">{alert.hostname}</span>
                    </div>
                    <div className="mt-0.5 text-sm text-gray-500">{alert.message}</div>
                  </div>
                </div>
                <div className="text-xs text-gray-300">#{alerts.length - index}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
