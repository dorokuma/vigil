import { useState, useEffect } from 'react';

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
      return res.json();
    },
    refetchInterval: 10000, // 每10秒自动刷新
  });

  const addDemoAlert = async () => {
    const demo = {
      hostname: ['hongkong', 'tokyo', 'beijing'][Math.floor(Math.random() * 3)],
      type: 'cpu_high',
      severity: Math.random() > 0.5 ? 'warning' : 'critical',
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
    // 简单实现：清空本地（生产可加 DELETE 接口）
    localStorage.removeItem('vigil-alerts');
    refetch();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">告警历史</h2>
          <p className="text-sm text-zinc-500 mt-1">实时来自 Python Bot 的告警 · 每10秒刷新</p>
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

      {isLoading ? (
        <div className="text-center py-16 text-zinc-500">加载中...</div>
      ) : alerts.length === 0 ? (
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
