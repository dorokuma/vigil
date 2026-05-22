interface VigilServerData {
  hostname: string;
  online: boolean;
  rtt?: number | string;
  loss_pct?: number;
  last_ping: number;
  cpu_percent?: number;
  memory_percent?: number;
  uptime: number;
  disks?: { mount_point: string; percent: number }[];
}

interface EnrichedServer {
  name: string;
  location: string;
  online: boolean;
  latency: number | string;
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
  if (seconds <= 0) return '\u2014';
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  if (d > 0) return `${d}d ${h}h`;
  return `${h}h`;
}

export async function onRequest(context: { request: Request; env: { VIGIL_API_URL?: string } }) {
  const { request, env } = context;
  const url = new URL(request.url);

  if (url.pathname === '/api/servers') {
    const cacheKey = new Request('https://dash/api/servers', { method: 'GET' });
    const cache = caches.default;

    let response = await cache.match(cacheKey);
    if (response) {
      return response;
    }

    try {
      const apiUrl = env.VIGIL_API_URL || 'http://127.0.0.1:9901/api/servers';
      const originResponse = await fetch(apiUrl, {
        cf: { cacheTtl: 15, cacheEverything: true },
      });
      const rawData: VigilServerData[] = await originResponse.json();

      const enriched: EnrichedServer[] = rawData
        .filter((s) => s.hostname !== 'test-alert' && s.hostname !== 'test-tunnel')
        .map((server) => ({
          name: server.hostname,
          location: LOCATION_MAP[server.hostname] || server.hostname,
          online: server.online !== false,
          latency: typeof server.rtt === 'string' ? server.rtt : Math.round(server.rtt || 0),
          packetLoss: server.loss_pct || 0,
          uptime: formatUptime(server.uptime),
          cpu: Math.round(server.cpu_percent || 0),
          memory: Math.round(server.memory_percent || 0),
          disk: Math.max(0, ...(server.disks || []).map(d => Math.round(d.percent))),
        }));

      const jsonResponse = new Response(JSON.stringify(enriched), {
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
          'Cache-Control': 'public, max-age=20, s-maxage=30',
          'CDN-Cache-Control': 'max-age=30',
        },
      });

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
}
