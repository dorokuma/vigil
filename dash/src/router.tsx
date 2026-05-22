import {
  createRootRoute,
  createRoute,
  createRouter,
} from '@tanstack/react-router'
import { Outlet } from '@tanstack/react-router'
import { QueryClient } from '@tanstack/react-query'
import Dashboard from './pages/Dashboard'
import Alerts from './pages/Alerts'

const rootRoute = createRootRoute({
  component: () => (
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-white to-teal-50">
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
