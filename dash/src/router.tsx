import {
  createRootRoute,
  createRoute,
  createRouter,
  Link,
  Outlet,
} from '@tanstack/react-router'
import { QueryClient } from '@tanstack/react-query'
import { Sun, Moon, Server, Bell } from 'lucide-react'
import { useTheme } from './hooks/useTheme'
import Dashboard from './pages/Dashboard'
import Alerts from './pages/Alerts'

function Header() {
  const { theme, toggleTheme } = useTheme()

  return (
    <header className="glass-header sticky top-0 z-50 px-6 py-0">
      <div className="mx-auto max-w-7xl flex items-center justify-between h-14">
        {/* 左侧：Logo + 导航 */}
        <div className="flex items-center gap-8">
          <Link to="/" className="flex items-center gap-2 font-semibold text-lg tracking-tight">
            <span className="text-cyan-500 dark:text-cyan-400">✨</span>
            <span className="text-zinc-800 dark:text-zinc-100">Vigil</span>
          </Link>
          <nav className="flex items-center gap-1">
            <Link
              to="/"
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg
                         text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100
                         dark:text-zinc-400 dark:hover:text-zinc-100 dark:hover:bg-zinc-800
                         data-[status=active]:text-cyan-600 dark:data-[status=active]:text-cyan-400
                         data-[status=active]:bg-cyan-50 dark:data-[status=active]:bg-cyan-500/10
                         transition-colors"
              activeOptions={{ exact: true }}
            >
              <Server size={15} />
              服务器
            </Link>
            <Link
              to="/alerts"
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg
                         text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100
                         dark:text-zinc-400 dark:hover:text-zinc-100 dark:hover:bg-zinc-800
                         data-[status=active]:text-cyan-600 dark:data-[status=active]:text-cyan-400
                         data-[status=active]:bg-cyan-50 dark:data-[status=active]:bg-cyan-500/10
                         transition-colors"
            >
              <Bell size={15} />
              告警
            </Link>
          </nav>
        </div>

        {/* 右侧：主题切换 */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs text-zinc-400 dark:text-zinc-500">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 animate-status-pulse" />
            <span className="hidden sm:inline">Live</span>
          </div>
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg text-zinc-500 hover:text-zinc-700 hover:bg-zinc-100
                       dark:text-zinc-400 dark:hover:text-zinc-200 dark:hover:bg-zinc-800
                       transition-colors"
            aria-label="切换主题"
          >
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </button>
        </div>
      </div>
    </header>
  )
}

// 根路由
const rootRoute = createRootRoute({
  component: () => (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 transition-colors">
      <Header />
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
