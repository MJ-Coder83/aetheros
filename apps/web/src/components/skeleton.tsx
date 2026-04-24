/** Reusable skeleton loading components. */
import { cn } from "@/lib/utils";

export function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-white/[0.04]", className)}
      {...props}
    />
  );
}

// Fixed skeleton widths — avoid calling Math.random() during render which
// violates React's purity rules and causes unstable hydration.
const SKELETON_WIDTHS = ["55%", "80%", "65%", "90%", "70%", "60%", "75%"];

export function SkeletonCard({ lines = 3 }: { lines?: number }) {
  return (
    <div className="glass rounded-xl p-5 space-y-3 border border-white/[0.04]">
      <Skeleton className="h-4 w-1/3" />
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className="h-3"
          style={{ width: SKELETON_WIDTHS[i % SKELETON_WIDTHS.length] }}
        />
      ))}
    </div>
  );
}

export function SkeletonStat() {
  return (
    <div className="glass rounded-xl p-5 space-y-3 border border-white/[0.04]">
      <div className="flex items-center justify-between">
        <Skeleton className="h-3 w-20" />
        <Skeleton className="h-8 w-8 rounded-lg" />
      </div>
      <Skeleton className="h-8 w-16" />
      <Skeleton className="h-3 w-28" />
    </div>
  );
}

export function SkeletonRow({ cols = 3 }: { cols?: number }) {
  return (
    <div className="flex items-center gap-4 py-3">
      {Array.from({ length: cols }).map((_, i) => (
        <Skeleton
          key={i}
          className="h-4"
          style={{
            width: i === 0 ? "40%" : i === 1 ? "30%" : "20%",
          }}
        />
      ))}
    </div>
  );
}

export function SkeletonList({ rows = 5 }: { rows?: number }) {
  return (
    <div className="divide-y divide-white/[0.03]">
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonRow key={i} />
      ))}
    </div>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <div className="h-14 w-14 rounded-2xl bg-inkos-cyan/[0.06] border border-inkos-cyan/10 flex items-center justify-center mb-5">
        <Icon className="h-7 w-7 text-inkos-cyan opacity-60" />
      </div>
      <h3 className="text-base font-semibold mb-1.5 text-foreground">
        {title}
      </h3>
      <p className="text-sm text-muted-foreground max-w-sm mb-5 leading-relaxed">
        {description}
      </p>
      {action}
    </div>
  );
}
