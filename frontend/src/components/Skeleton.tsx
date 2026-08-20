"use client";

interface SkeletonProps {
  className?: string;
}

/** Pulsing skeleton placeholder for loading states. */
export function Skeleton({ className = "" }: SkeletonProps) {
  return (
    <div
      className={`rounded-md bg-gray-200 dark:bg-white/[0.06] animate-pulse motion-reduce:animate-none ${className}`}
      aria-hidden="true"
    />
  );
}

/** Skeleton for a card layout */
export function SkeletonCard() {
  return (
    <div className="rounded-md border border-border bg-background p-5 space-y-3">
      <Skeleton className="h-4 w-1/3" />
      <Skeleton className="h-3 w-full" />
      <Skeleton className="h-3 w-4/5" />
      <Skeleton className="h-3 w-2/3" />
    </div>
  );
}

/** Skeleton for a code block */
export function SkeletonCode() {
  return (
    <div className="rounded-md border border-border bg-background overflow-hidden">
      <div className="px-4 py-2.5 border-b border-border/50 bg-muted/20">
        <Skeleton className="h-3 w-24" />
      </div>
      <div className="p-4 space-y-2">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-5/6" />
        <Skeleton className="h-3 w-4/5" />
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-3/4" />
        <Skeleton className="h-3 w-5/6" />
      </div>
    </div>
  );
}

/** Skeleton for the terminal */
export function SkeletonTerminal() {
  return (
    <div className="rounded-md border border-border overflow-hidden">
      <div className="px-4 py-2 bg-[#161b22] border-b border-gray-700/50">
        <Skeleton className="h-3 w-20 bg-gray-700" />
      </div>
      <div className="bg-[#0d1117] p-4 space-y-2">
        <Skeleton className="h-3 w-3/4 bg-gray-800" />
        <Skeleton className="h-3 w-1/2 bg-gray-800" />
        <Skeleton className="h-3 w-5/6 bg-gray-800" />
        <Skeleton className="h-3 w-2/3 bg-gray-800" />
      </div>
    </div>
  );
}

/** Page-level skeleton layout */
export function SkeletonPage() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <Skeleton className="h-9 w-9 rounded-md" />
        <div className="space-y-1.5">
          <Skeleton className="h-5 w-48" />
          <Skeleton className="h-3 w-72" />
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-4">
          <SkeletonCard />
        </div>
        <div className="lg:col-span-8">
          <SkeletonCode />
        </div>
      </div>
    </div>
  );
}
