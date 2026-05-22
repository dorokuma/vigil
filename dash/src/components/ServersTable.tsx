import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
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
        <div className="font-medium text-gray-800 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 shrink-0" />
          <span>{info.row.original.location}</span>
        </div>
      ),
    }),
    columnHelper.accessor('online', {
      header: '状态',
      cell: info => (
        <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium whitespace-nowrap ${
          info.getValue() 
            ? 'bg-emerald-50 text-emerald-600' 
            : 'bg-red-50 text-red-600'
        }`}>
          <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${
            info.getValue() ? 'bg-emerald-400' : 'bg-red-400'
          }`} />
          {info.getValue() ? '正常' : '离线'}
        </span>
      ),
    }),
    columnHelper.accessor('cpu', {
      header: 'CPU',
      cell: info => (
        <div className="flex items-center gap-2">
          <div className="w-11 sm:w-14 h-1.5 bg-gray-100 rounded-full overflow-hidden hidden sm:block">
            <div 
              className="h-full bg-gradient-to-r from-sky-400 to-blue-500 rounded-full transition-all" 
              style={{ width: `${Math.min(info.getValue(), 100)}%` }} 
            />
          </div>
          <span className="text-xs tabular-nums text-gray-500 w-8">{info.getValue()}%</span>
        </div>
      ),
    }),
    columnHelper.accessor('memory', {
      header: '内存',
      cell: info => (
        <div className="flex items-center gap-2">
          <div className="w-11 sm:w-14 h-1.5 bg-gray-100 rounded-full overflow-hidden hidden sm:block">
            <div 
              className="h-full bg-gradient-to-r from-teal-400 to-emerald-500 rounded-full transition-all" 
              style={{ width: `${Math.min(info.getValue(), 100)}%` }} 
            />
          </div>
          <span className="text-xs tabular-nums text-gray-500 w-8">{info.getValue()}%</span>
        </div>
      ),
    }),
    columnHelper.accessor('disk', {
      header: '磁盘',
      cell: info => (
        <div className="flex items-center gap-2">
          <div className="w-11 sm:w-14 h-1.5 bg-gray-100 rounded-full overflow-hidden hidden sm:block">
            <div 
              className={`h-full rounded-full transition-all ${
                info.getValue() > 90 ? 'bg-red-400' : info.getValue() > 70 ? 'bg-amber-400' : 'bg-violet-400'
              }`}
              style={{ width: `${Math.min(info.getValue(), 100)}%` }} 
            />
          </div>
          <span className="text-xs tabular-nums text-gray-500 w-8">{info.getValue()}%</span>
        </div>
      ),
    }),
    columnHelper.accessor('latency', {
      header: () => <span className="min-w-[5rem] block whitespace-nowrap">延迟</span>,
      cell: info => {
        const v = info.getValue();
        if (typeof v === 'string') {
          return <span className="text-xs text-gray-400 font-medium whitespace-nowrap">{v}</span>;
        }
        const num = v as number;
        const color = num < 50 ? 'text-emerald-500' : num < 150 ? 'text-amber-500' : 'text-red-500';
        return <span className={`text-xs tabular-nums font-medium whitespace-nowrap ${color}`}>{num}ms</span>;
      },
    }),
    columnHelper.accessor('uptime', {
      header: '运行',
      cell: info => (
        <span className="text-xs text-gray-400 whitespace-nowrap">{info.getValue()}</span>
      ),
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
    return <div className="p-8 text-center text-gray-400">加载中...</div>;
  }

  return (
    <div className="p-4 sm:p-6 space-y-4">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <input
          type="text"
          placeholder="搜索服务器..."
          value={globalFilter}
          onChange={e => setGlobalFilter(e.target.value)}
          className="px-4 py-2 border border-gray-200 rounded-xl bg-gray-50 focus:bg-white focus:border-sky-300 focus:ring-2 focus:ring-sky-100 outline-none w-full sm:w-72 text-sm text-gray-700 placeholder-gray-400 transition-all"
        />
        <div className="flex items-center gap-3 w-full sm:w-auto justify-between sm:justify-end">
          <div className="text-xs text-gray-400 font-medium shrink-0">
            {table.getFilteredRowModel().rows.length} 台
          </div>
          <button
            onClick={exportToCSV}
            className="px-4 py-1.5 text-xs bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-xl text-gray-600 flex items-center gap-1.5 transition-all shrink-0"
          >
            📥 CSV
          </button>
        </div>
      </div>

      <div className="overflow-x-auto -mx-4 sm:mx-0 rounded-none sm:rounded-xl border-0 sm:border border-gray-100">
        <div className="min-w-[600px] sm:min-w-0">
          <table className="w-full text-sm">
            <thead>
              {table.getHeaderGroups().map(headerGroup => (
                <tr key={headerGroup.id} className="border-b border-gray-50">
                  {headerGroup.headers.map(header => (
                    <th
                      key={header.id}
                      className="px-4 sm:px-6 py-3.5 text-left font-medium text-gray-400 text-xs uppercase tracking-wider cursor-pointer select-none hover:text-gray-600 transition-colors whitespace-nowrap"
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
            <tbody className="divide-y divide-gray-50">
              {table.getRowModel().rows.map(row => (
                <tr key={row.id} className="hover:bg-sky-50/50 transition-colors">
                  {row.getVisibleCells().map(cell => (
                    <td key={cell.id} className="px-4 sm:px-6 py-3 sm:py-4 text-gray-600">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
