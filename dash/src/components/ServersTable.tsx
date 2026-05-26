import { useMemo, useState } from 'react'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
} from '@tanstack/react-table'
import { Search, Download, ChevronUp, ChevronDown } from 'lucide-react'
import { StatusDot } from './StatusDot'
import type { EnrichedServer } from '../types'

interface ServersTableProps {
  data: EnrichedServer[]
  isLoading: boolean
}

/* ── 颜色辅助函数 ── */

function cpuBarColor(value: number): string {
  if (value >= 80) return 'bg-rose-500 dark:bg-rose-400'
  if (value >= 50) return 'bg-amber-500 dark:bg-amber-400'
  return 'bg-emerald-500 dark:bg-emerald-400'
}

function latencyColor(value: number | string | null): string {
  if (value === null || value === 0 || typeof value === 'string' || !value) return 'text-zinc-400 dark:text-zinc-600'
  if (value >= 150) return 'text-rose-600 dark:text-rose-400'
  if (value >= 50) return 'text-amber-600 dark:text-amber-400'
  return 'text-emerald-600 dark:text-emerald-400'
}

/* ── 列定义 ── */

const columnHelper = createColumnHelper<EnrichedServer>()

export function ServersTable({ data, isLoading }: ServersTableProps) {
  const [sorting, setSorting] = useState<SortingState>([])
  const [globalFilter, setGlobalFilter] = useState('')

  const columns = useMemo(
    () => [
      columnHelper.accessor('online', {
        header: '',
        enableSorting: true,
        cell: (info) => (
          <div className="flex justify-center">
            <StatusDot online={info.getValue()} />
          </div>
        ),
      }),
      columnHelper.accessor('name', {
        header: '服务器',
        cell: (info) => (
          <span className="font-medium text-zinc-900 dark:text-zinc-100">
            {info.getValue()}
          </span>
        ),
      }),
      columnHelper.accessor('location', {
        header: '地区',
        cell: (info) => (
          <span className="inline-flex items-center px-2 py-0.5 text-xs rounded-md
                         bg-zinc-100 text-zinc-600
                         dark:bg-zinc-800 dark:text-zinc-400">
            {info.getValue()}
          </span>
        ),
      }),
      columnHelper.accessor('cpu', {
        header: 'CPU',
        cell: (info) => {
          const val = info.getValue()
          return (
            <div className="flex items-center gap-2.5 min-w-[100px]">
              <div className="flex-1 h-1.5 rounded-full bg-zinc-100 dark:bg-zinc-800 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${cpuBarColor(val)}`}
                  style={{ width: `${Math.min(val, 100)}%` }}
                />
              </div>
              <span className="text-xs tabular-nums w-8 text-right text-zinc-600 dark:text-zinc-400">
                {val}%
              </span>
            </div>
          )
        },
      }),
      columnHelper.accessor('memory', {
        header: '内存',
        cell: (info) => {
          const val = info.getValue()
          return (
            <div className="flex items-center gap-2.5 min-w-[100px]">
              <div className="flex-1 h-1.5 rounded-full bg-zinc-100 dark:bg-zinc-800 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${cpuBarColor(val)}`}
                  style={{ width: `${Math.min(val, 100)}%` }}
                />
              </div>
              <span className="text-xs tabular-nums w-8 text-right text-zinc-600 dark:text-zinc-400">
                {val}%
              </span>
            </div>
          )
        },
      }),
      columnHelper.accessor('latency', {
        header: '延迟',
        cell: (info) => {
          const val = info.getValue()
          const loss = info.row.original.packetLoss
          const numericLat = typeof val === 'number' ? val : 0
          return (
            <span className={`tabular-nums text-sm ${latencyColor(val)}`}>
              {numericLat > 0 ? `${val}ms` : '—'}
              {loss > 0 && (
                <span className="text-rose-500 dark:text-rose-400 ml-1 text-xs">
                  / {loss}%丢包
                </span>
              )}
            </span>
          )
        },
      }),
      columnHelper.accessor('uptime', {
        header: '运行时间',
        cell: (info) => {
          const val = info.getValue()
          return (
            <span className="text-sm text-zinc-500 dark:text-zinc-400 tabular-nums">
              {val || '—'}
            </span>
          )
        },
      }),
    ],
    [],
  )

  const table = useReactTable({
    data,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  })

  const csvEscape = (val: unknown): string => {
    const str = String(val ?? '')
    if (str.includes(',') || str.includes('"') || str.includes('\n')) {
      return `"${str.replace(/"/g, '""')}"`
    }
    return str
  }

  const exportToCSV = () => {
    const headers = ['服务器', '地区', '状态', 'CPU%', '内存%', '延迟(ms)', '丢包%', '运行时间']
    const rows = data.map((s) => [
      csvEscape(s.name),
      csvEscape(s.location),
      csvEscape(s.online ? '在线' : '离线'),
      csvEscape(s.cpu),
      csvEscape(s.memory),
      csvEscape(s.latency),
      csvEscape(s.packetLoss),
      csvEscape(s.uptime),
    ])
    const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `vigil-servers-${new Date().toISOString().slice(0, 10)}.csv`
    link.click()
    URL.revokeObjectURL(link.href)
  }

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200/60 dark:border-zinc-800/60 p-6">
        <div className="space-y-4 animate-pulse">
          <div className="h-9 bg-zinc-100 dark:bg-zinc-800 rounded-lg w-full" />
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-12 bg-zinc-50 dark:bg-zinc-800/50 rounded-lg w-full" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200/60 dark:border-zinc-800/60 shadow-sm dark:shadow-none animate-fade-in">
      {/* 工具栏 */}
      <div className="flex items-center justify-between gap-4 px-5 py-4 border-b border-zinc-100 dark:border-zinc-800">
        <div className="relative flex-1 max-w-xs">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 dark:text-zinc-500"
          />
          <input
            type="text"
            placeholder="搜索服务器..."
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-sm rounded-lg
                       bg-zinc-50 border border-zinc-200 text-zinc-900
                       dark:bg-zinc-800 dark:border-zinc-700 dark:text-zinc-100
                       placeholder:text-zinc-400 dark:placeholder:text-zinc-500
                       focus:outline-none focus:ring-2 focus:ring-cyan-500/30 focus:border-cyan-500
                       dark:focus:border-cyan-400 transition-all"
          />
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-zinc-400 dark:text-zinc-500 tabular-nums">
            {table.getFilteredRowModel().rows.length} 台服务器
          </span>
          <button
            onClick={exportToCSV}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg
                       text-zinc-600 hover:text-zinc-900 bg-zinc-100 hover:bg-zinc-200
                       dark:text-zinc-400 dark:hover:text-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700
                       transition-colors"
          >
            <Download size={13} />
            导出 CSV
          </button>
        </div>
      </div>

      {/* 表格 */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    className="px-5 py-3.5 text-left text-xs font-medium
                               text-zinc-500 dark:text-zinc-400
                               cursor-pointer select-none whitespace-nowrap
                               hover:text-zinc-700 dark:hover:text-zinc-200 transition-colors"
                    onClick={header.column.getToggleSortingHandler()}
                  >
                    <div className="flex items-center gap-1">
                      {flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}
                      <span className="inline-flex flex-col leading-none text-[10px] text-zinc-300 dark:text-zinc-600">
                        {header.column.getIsSorted() === 'asc' ? (
                          <ChevronUp size={12} className="text-cyan-500 dark:text-cyan-400" />
                        ) : header.column.getIsSorted() === 'desc' ? (
                          <ChevronDown size={12} className="text-cyan-500 dark:text-cyan-400" />
                        ) : (
                          <>
                            <ChevronUp size={8} />
                            <ChevronDown size={8} className="-mt-0.5" />
                          </>
                        )}
                      </span>
                    </div>
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {table.getRowModel().rows.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-5 py-12 text-center text-sm text-zinc-400 dark:text-zinc-500"
                >
                  没有匹配的服务器
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  className="hover:bg-zinc-50 dark:hover:bg-zinc-800/30 transition-colors"
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-5 py-3.5">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
