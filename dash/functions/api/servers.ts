export interface Env {
  VIGIL_API_URL: string;
}

interface VigilServerData {
  hostname: string;
  is_offline: boolean;
  last_seen: number;
  uptime: number;
  cpu_percent: number;
  memory_percent: number;
  load: { "1m": number; "5m": number; "15m": number };
  rtt?: number;
  loss_pct?: number;
}

interface EnrichedServer {
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

const LOCATION_MAP: Record<string, string> = {
  hongkong: '🇭🇰 香港',
  tokyo: '🇯🇵 东京',
  mumbai: '🇮🇳 孟买',
  sanjose: '🇺🇸 圣何塞',
  columbus: '🇺🇸 哥伦布',
  aione: '🤖 AI One',
  singapore: '🇸🇬 新加坡',
  beijing: '🇨🇳 北京',
  eqi12: '🏠 家里',
};

function formatUptime(seconds: number): string {
  if (seconds <= 0) return '—';
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  if (d > 0) return `${d}d ${h}h`;
  return `${h}h`;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === '/api/servers') {
      const cacheKey = new Request('https://dash/api/servers', { method: 'GET' });
      const cache = caches.default;

      // 尝试从 Cloudflare Edge Cache 获取（白嫖 99% 请求）
      let response = await cache.match(cacheKey);
      if (response) {
        return response;
      }

      try {
        const apiUrl = env.VIGIL_API_URL || 'http://127.0.0.1:9901/status';
        const originResponse = await fetch(apiUrl, {
          cf: { cacheTtl: 15, cacheEverything: true }
        });
        const rawData: VigilServerData[] = await originResponse.json();

        const enriched: EnrichedServer[] = rawData
          .filter((s) => s.hostname !== 'test-alert')
          .map((server) => ({
            name: server.hostname,
            location: LOCATION_MAP[server.hostname] || server.hostname,
            online: !server.is_offline,
            latency: Math.round(server.rtt || 0),
            packetLoss: server.loss_pct || 0,
            uptime: formatUptime(server.uptime),
            cpu: Math.round(server.cpu_percent || 0),
            memory: Math.round(server.memory_percent || 0),
            disk: 0,
          }));

        const jsonResponse = new Response(JSON.stringify(enriched), {
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Cache-Control': 'public, max-age=20, s-maxage=30',
            'CDN-Cache-Control': 'max-age=30',
          },
        });

        // 写入 Cloudflare Edge Cache（免费且全球加速）
        await cache.put(cacheKey, jsonResponse.clone());

        return jsonResponse;
      } catch (err) {
        return new Response(JSON.stringify({ error: 'Failed to fetch server data' }), {
          status: 502,
          headers: { 'Content-Type': 'application/json' },
        });
      }
    }

    return new Response('Not Found', { status: 404 });
  },
} satisfies ExportedHandler<Env>;
