import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  createColumnHelper,
  SortingState,
} from '@tanstack/react-table';
import { useState } from 'react';

import type { EnrichedServer } from '../types';

interface ServersTableProps {
  data: EnrichedServer[];
  isLoading: boolean;
}

const columnHelper = createColumnHelper<EnrichedServer>();

export function ServersTable({ data, isLoading }: ServersTableProps) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState('');

  const columns = [
    columnHelper.accessor('name', {
      header: '服务器',
      cell: info => (
        <div className="font-medium flex items-center gap-2">
          <span>{info.getValue()}</span>
          <span className="text-xs px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800">
            {info.row.original.location}
          </span>
        </div>
      ),
    }),
    columnHelper.accessor('online', {
      header: '状态',
      cell: info => (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${info.getValue() 
          ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' 
          : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'}`}>
          {info.getValue() ? '在线' : '离线'}
        </span>
      ),
    }),
    columnHelper.accessor('cpu', {
      header: 'CPU',
      cell: info => (
        <div className="flex items-center gap-2">
          <div className="w-16 h-2 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
            <div 
              className="h-full bg-blue-500 transition-all" 
              style={{ width: `${Math.min(info.getValue(), 100)}%` }} 
            />
          </div>
          <span className="text-xs tabular-nums w-8">{info.getValue()}%</span>
        </div>
      ),
    }),
    columnHelper.accessor('memory', {
      header: '内存',
      cell: info => (
        <div className="flex items-center gap-2">
          <div className="w-16 h-2 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
            <div 
              className="h-full bg-purple-500 transition-all" 
              style={{ width: `${Math.min(info.getValue(), 100)}%` }} 
            />
          </div>
          <span className="text-xs tabular-nums w-8">{info.getValue()}%</span>
        </div>
      ),
    }),
    columnHelper.accessor('latency', {
      header: '延迟',
      cell: info => `${info.getValue()}ms`,
    }),
    columnHelper.accessor('uptime', {
      header: '运行时间',
    }),
  ];

  const table = useReactTable({
    data,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  const exportToCSV = () => {
    const headers = ['服务器', '状态', 'CPU%', '内存%', '延迟(ms)', '运行时间'];
    const rows = data.map(s => [
      s.name,
      s.online ? '在线' : '离线',
      s.cpu,
      s.memory,
      s.latency,
      s.uptime
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.href = url;
    link.download = `vigil-servers-${new Date().toISOString().slice(0,10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return <div className="p-8 text-center text-zinc-500">加载中...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <input
          type="text"
          placeholder="搜索服务器..."
          value={globalFilter}
          onChange={e => setGlobalFilter(e.target.value)}
          className="px-4 py-2 border rounded-lg bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-700 w-72 text-sm"
        />
        <div className="flex items-center gap-3">
          <div className="text-xs text-zinc-500">
            {table.getFilteredRowModel().rows.length} 台服务器
          </div>
          <button
            onClick={exportToCSV}
            className="px-4 py-1.5 text-xs bg-zinc-800 hover:bg-zinc-700 rounded-lg flex items-center gap-1.5 transition-colors"
          >
            📥 导出 CSV
          </button>
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-800">
        <table className="w-full text-sm">
          <thead className="bg-zinc-50 dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800">
            {table.getHeaderGroups().map(headerGroup => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map(header => (
                  <th
                    key={header.id}
                    className="px-6 py-3 text-left font-medium text-zinc-500 dark:text-zinc-400 cursor-pointer select-none"
                    onClick={header.column.getToggleSortingHandler()}
                  >
                    {flexRender(header.column.columnDef.header, header.getContext())}
                    {{
                      asc: ' ↑',
                      desc: ' ↓',
                    }[header.column.getIsSorted() as string] ?? null}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
            {table.getRowModel().rows.map(row => (
              <tr key={row.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-900/50 transition-colors">
                {row.getVisibleCells().map(cell => (
                  <td key={cell.id} className="px-6 py-4 text-zinc-700 dark:text-zinc-300">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
