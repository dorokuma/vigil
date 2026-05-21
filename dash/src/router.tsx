import {
  createRootRoute,
  createRoute,
  createRouter,
} from '@tanstack/react-router'
import { Outlet } from '@tanstack/react-router'
import { QueryClient } from '@tanstack/react-query'
import Dashboard from './pages/Dashboard'

// 根路由
const rootRoute = createRootRoute({
  component: () => (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <header className="border-b border-gray-800 px-6 py-4">
        <div className="mx-auto max-w-7xl flex items-center justify-between">
          <h1 className="text-xl font-bold text-cyan-400">✨ Server Dashboard</h1>
          <span className="text-sm text-gray-500">hotkids.eu 集群监控</span>
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

const routeTree = rootRoute.addChildren([indexRoute])

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
