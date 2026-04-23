"use client";

import { useHealthCheck } from "@/hooks/use-api";
import { cn } from "@/lib/utils";

export function StatusIndicator() {
  const { data, isLoading, isError } = useHealthCheck();

  const status = isError ? "offline" : isLoading ? "checking" : "online";
  const colours: Record<string, string> = {
    online: "bg-emerald-400 shadow-emerald-400/50",
    offline: "bg-red-400 shadow-red-400/50",
    checking: "bg-yellow-400 shadow-yellow-400/50 animate-pulse",
  };

  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      <span
        className={cn(
          "inline-block h-2 w-2 rounded-full shadow-sm",
          colours[status],
        )}
      />
      <span className="capitalize">{status}</span>
      {data?.status && (
        <span className="text-inkos-cyan/60">({data.status})</span>
      )}
    </div>
  );
}
