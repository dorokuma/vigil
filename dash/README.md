# Vigil Dashboard (TanStack + Cloudflare)

Modern monitoring dashboard for Vigil, built with:

- **React 19** + **Vite**
- **TanStack Query** + **TanStack Router** + **TanStack Table**
- **Tailwind CSS v4**
- **Cloudflare Pages + Functions** (free tier optimized)

## Features
- Real-time server status from Vigil collector
- Beautiful sortable tables (TanStack Table)
- Edge caching via Cloudflare (99% requests served from cache for free)
- Global low-latency access

## Quick Start

```bash
cd dash
npm install
npm run dev
```

Then open http://localhost:5173

## Deploy to Cloudflare (Free)

1. Install Wrangler:
   ```bash
   npm install -g wrangler
   wrangler login
   ```

2. Build:
   ```bash
   npm run build
   ```

3. Deploy:
   ```bash
   wrangler pages deploy dist --project-name=vigil-dash
   ```

4. (Optional) Add custom domain in Cloudflare Dashboard.

## Environment Variables

In Cloudflare Pages → Settings → Environment variables:

- `VIGIL_API_URL` = `https://your-collector.example.com/status`  (or your internal URL via Tunnel)

## Free Tier Tips (白嫖指南)

- **Cloudflare Cache API** → 30s edge cache (saves 99% origin requests)
- **Pages + Functions** → 500k requests/month free
- **No egress fees** for dashboard traffic
- Use Cloudflare Tunnel to securely expose your collector without public IP

## Tech Stack
- @tanstack/react-query
- @tanstack/react-router
- @tanstack/react-table
- Cloudflare Pages Functions (edge API proxy)

Enjoy your free global monitoring dashboard! 🚀
