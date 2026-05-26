interface StatusDotProps {
  online: boolean
}

export function StatusDot({ online }: StatusDotProps) {
  return (
    <span className="relative inline-flex items-center justify-center w-2.5 h-2.5">
      <span
        className={`absolute inline-flex w-full h-full rounded-full ${
          online
            ? 'bg-emerald-500 animate-status-pulse'
            : 'bg-red-500'
        }`}
      />
      <span
        className={`relative inline-flex w-1.5 h-1.5 rounded-full ${
          online ? 'bg-emerald-500' : 'bg-red-500'
        }`}
      />
    </span>
  )
}
