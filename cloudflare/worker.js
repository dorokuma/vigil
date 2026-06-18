// Telegram API Proxy — 绑你的自定义域名
// Bot 设置 BASE_URL 指向 https://你的域名

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url)

  // 只代理 /bot 开头的 Telegram API 路径
  if (!url.pathname.startsWith('/bot')) {
    return new Response('Not found', { status: 404 })
  }

  // 转发到 api.telegram.org
  const tgUrl = `https://api.telegram.org${url.pathname}${url.search}`

  const response = await fetch(tgUrl, {
    method: request.method,
    headers: {
      'Content-Type': 'application/json',
    },
    body: request.method === 'POST' ? request.body : undefined,
  })

  return response
}
