import {
  createRootRoute,
  createRoute,
  createRouter,
  Link,
} from '@tanstack/react-router'
import { Outlet } from '@tanstack/react-router'
import { QueryClient } from '@tanstack/react-query'
import Dashboard from './pages/Dashboard'
import Alerts from './pages/Alerts'

// 根路由
const rootRoute = createRootRoute({
  component: () => (
    <div className="min-h-screen bg-zinc-950 text-white">
      <header className="border-b border-zinc-800 px-6 py-4 sticky top-0 bg-zinc-950/80 backdrop-blur z-50">
        <div className="mx-auto max-w-7xl flex items-center justify-between">
          <div className="flex items-center gap-8">
            <h1 className="text-xl font-bold text-cyan-400">✨ Vigil</h1>
            <nav className="flex items-center gap-6 text-sm">
              <Link to="/" className="hover:text-cyan-400 transition-colors data-[status=active]:text-cyan-400" activeOptions={{ exact: true }}>
                服务器
              </Link>
              <Link to="/alerts" className="hover:text-cyan-400 transition-colors data-[status=active]:text-cyan-400">
                告警历史
              </Link>
            </nav>
          </div>
          <span className="text-xs text-zinc-500">Cloudflare + TanStack</span>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  ),
})

// 首页
const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: Dashboard,
})

const alertsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/alerts',
  component: Alerts,
})

const routeTree = rootRoute.addChildren([indexRoute, alertsRoute])

export function createAppRouter(queryClient: QueryClient) {
  return createRouter({
    routeTree,
    context: { queryClient },
    defaultPreload: 'intent',
  })
}

declare module '@tanstack/react-router' {
  interface Register {
    router: ReturnType<typeof createAppRouter>
  }
}
