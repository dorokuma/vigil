interface Alert {
  id: number;
  time: string;
  hostname: string;
  type: string;
  severity: 'warning' | 'critical';
  message: string;
  timestamp: number;
}

const ALERT_KEY = 'vigil_alerts';

const getAlerts = async (env: { ALERTS_KV?: KVNamespace }): Promise<Alert[]> => {
  if (env.ALERTS_KV) {
    const data = await env.ALERTS_KV.get(ALERT_KEY, 'json');
    return data || [];
  }
  return (globalThis as any).__vigil_alerts || [];
};

const saveAlerts = async (env: { ALERTS_KV?: KVNamespace }, alerts: Alert[]) => {
  if (env.ALERTS_KV) {
    await env.ALERTS_KV.put(ALERT_KEY, JSON.stringify(alerts));
  } else {
    (globalThis as any).__vigil_alerts = alerts;
  }
};

export async function onRequest(context: { request: Request; env: { ALERTS_KV?: KVNamespace } }) {
  const { request, env } = context;
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

      const alerts = await getAlerts(env);
      alerts.unshift(newAlert);
      if (alerts.length > 50) alerts.pop();
      await saveAlerts(env, alerts);

      return new Response(JSON.stringify({ success: true }), {
        headers: { 'Content-Type': 'application/json' },
      });
    } catch (e) {
      return new Response(JSON.stringify({ error: 'Invalid alert data' }), { status: 400 });
    }
  }

  if (request.method === 'GET' && url.pathname === '/api/alerts') {
    const alerts = await getAlerts(env);
    return new Response(JSON.stringify(alerts), {
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache',
      },
    });
  }

  return new Response('Not Found', { status: 404 });
}
