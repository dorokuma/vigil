import { useState, useEffect } from 'react';

interface Alert {
  id: number;
  time: string;
  hostname: string;
  type: string;
  severity: 'warning' | 'critical';
  message: string;
}

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([]);

  useEffect(() => {
    const saved = localStorage.getItem('vigil-alerts');
    if (saved) setAlerts(JSON.parse(saved));
  }, []);

  const addDemoAlert = () => {
    const newAlert: Alert = {
      id: Date.now(),
      time: new Date().toLocaleTimeString(),
      hostname: ['hongkong', 'tokyo', 'beijing'][Math.floor(Math.random() * 3)],
      type: ['cpu_high', 'memory_high', 'offline'][Math.floor(Math.random() * 3)],
      severity: Math.random() > 0.5 ? 'warning' : 'critical',
      message: '模拟告警 - ' + new Date().toLocaleTimeString(),
    };
    const updated = [newAlert, ...alerts].slice(0, 50);
    setAlerts(updated);
    localStorage.setItem('vigil-alerts', JSON.stringify(updated));
  };

  const clearHistory = () => {
    setAlerts([]);
    localStorage.removeItem('vigil-alerts');
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">告警历史</h2>
          <p className="text-sm text-zinc-500 mt-1">最近 50 条告警记录（本地存储）</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={addDemoAlert}
            className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm"
          >
            + 添加模拟告警
          </button>
          <button
            onClick={clearHistory}
            className="px-4 py-2 bg-red-900/50 hover:bg-red-900 rounded-lg text-sm text-red-400"
          >
            清空历史
          </button>
        </div>
      </div>

      {alerts.length === 0 ? (
        <div className="text-center py-16 text-zinc-500">
          暂无告警记录
        </div>
      ) : (
        <div className="space-y-2">
          {alerts.map((alert, index) => (
            <div
              key={alert.id}
              className={`p-4 rounded-xl border flex justify-between items-start ${alert.severity === 'critical' 
                ? 'border-red-500/50 bg-red-950/30' 
                : 'border-yellow-500/50 bg-yellow-950/30'}`}
            >
              <div>
                <div className="flex items-center gap-3">
                  <span className={`px-2 py-0.5 text-xs rounded ${alert.severity === 'critical' ? 'bg-red-500' : 'bg-yellow-500'} text-black font-medium`}>
                    {alert.severity.toUpperCase()}
                  </span>
                  <span className="font-mono text-sm text-zinc-400">{alert.time}</span>
                  <span className="font-medium">{alert.hostname}</span>
                </div>
                <div className="mt-1 text-sm">{alert.message}</div>
              </div>
              <div className="text-xs text-zinc-500">#{alerts.length - index}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
