'use client'

interface LoadingSkeletonProps {
  count?: number
}

export default function LoadingSkeleton({ count = 10 }: LoadingSkeletonProps) {
  return (
    <div className="flex gap-4 overflow-hidden px-8">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="flex-shrink-0 w-80 h-60 bg-zinc-900 rounded-lg relative overflow-hidden"
        >
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent loading-shimmer" />
        </div>
      ))}
    </div>
  )
}
