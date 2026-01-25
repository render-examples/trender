'use client'

interface LoadingSkeletonProps {
  count?: number
}

export default function LoadingSkeleton({ count = 10 }: LoadingSkeletonProps) {
  return (
    <div className="flex gap-3 sm:gap-4 overflow-hidden px-4 sm:px-8">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="flex-shrink-0 w-[280px] sm:w-80 h-60 sm:h-[280px] bg-zinc-900 rounded-lg relative overflow-hidden"
        >
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent loading-shimmer" />
        </div>
      ))}
    </div>
  )
}
