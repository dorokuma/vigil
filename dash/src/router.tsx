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

const rootRoute = createRootRoute({
  component: () => (
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-white to-teal-50">
      <header className="border-b border-gray-200/60 px-4 sm:px-6 py-2 sm:py-3 sticky top-0 bg-white/70 backdrop-blur-xl z-50 shadow-sm">
        <div className="mx-auto max-w-7xl flex items-center justify-between gap-4">
          <div className="flex items-center gap-4 sm:gap-8">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 sm:w-8 sm:h-8 bg-gradient-to-br from-sky-400 to-teal-400 rounded-xl flex items-center justify-center shadow-sm shrink-0">
                <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <span className="text-base sm:text-lg font-bold text-gray-800 tracking-tight">Vigil</span>
            </div>
            <nav className="flex items-center gap-0.5 sm:gap-1 text-sm">
              <Link to="/" className="px-2.5 sm:px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors data-[status=active]:bg-sky-50 data-[status=active]:text-sky-600 data-[status=active]:font-medium text-gray-500 text-xs sm:text-sm" activeOptions={{ exact: true }}>
                服务器
              </Link>
              <Link to="/alerts" className="px-2.5 sm:px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors data-[status=active]:bg-sky-50 data-[status=active]:text-sky-600 data-[status=active]:font-medium text-gray-500 text-xs sm:text-sm">
                告警
              </Link>
            </nav>
          </div>
          <span className="text-xs text-gray-400 hidden sm:block">Cloudflare + TanStack</span>
        </div>
      </header>
      <main className="mx-auto max-w-7xl">
        <Outlet />
      </main>
    </div>
  ),
})

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
