export interface Env {}

interface Alert {
  id: number;
  time: string;
  hostname: string;
  type: string;
  severity: 'warning' | 'critical';
  message: string;
  timestamp: number;
}

// 注意：当前使用内存存储，部署后会重置。
// 生产环境建议绑定 Cloudflare KV（免费额度足够）：
// 在 wrangler.toml 中添加 [kv_namespaces] 并修改代码使用 env.ALERTS_KV
let alertHistory: Alert[] = [];

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (request.method === 'POST' && url.pathname === '/api/alerts') {
      try {
        const alert = await request.json() as Omit<Alert, 'id' | 'time' | 'timestamp'>;
        
        const newAlert: Alert = {
          ...alert,
          id: Date.now(),
          time: new Date().toLocaleTimeString('zh-CN'),
          timestamp: Date.now(),
        };

        alertHistory.unshift(newAlert);
        if (alertHistory.length > 50) alertHistory.pop();

        return new Response(JSON.stringify({ success: true }), {
          headers: { 'Content-Type': 'application/json' },
        });
      } catch (e) {
        return new Response(JSON.stringify({ error: 'Invalid alert data' }), { status: 400 });
      }
    }

    if (request.method === 'GET' && url.pathname === '/api/alerts') {
      return new Response(JSON.stringify(alertHistory), {
        headers: { 
          'Content-Type': 'application/json',
          'Cache-Control': 'no-cache',
        },
      });
    }

    return new Response('Not Found', { status: 404 });
  },
} satisfies ExportedHandler<Env>;
