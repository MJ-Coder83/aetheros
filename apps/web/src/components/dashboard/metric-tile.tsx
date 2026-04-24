import { Sparkline } from "./sparkline";

type AccentColor = "text" | "cyan" | "emerald" | "amber" | "red";

interface MetricTileProps {
  label: string;
  value: string | number;
  delta?: string;
  accent?: AccentColor;
  sparklineData?: number[];
}

const accentColorMap: Record<AccentColor, string> = {
  text: "text-foreground",
  cyan: "text-inkos-cyan",
  emerald: "text-emerald-400",
  amber: "text-amber-400",
  red: "text-red-400",
};

const sparklineColorMap: Record<AccentColor, "cyan" | "emerald" | "amber" | "violet"> = {
  text: "cyan",
  cyan: "cyan",
  emerald: "emerald",
  amber: "amber",
  red: "cyan",
};

export function MetricTile({
  label,
  value,
  delta,
  accent = "text",
  sparklineData,
}: MetricTileProps) {
  const deltaColor =
    delta && delta.startsWith("+")
      ? "text-emerald-400"
      : delta?.startsWith("-")
        ? "text-amber-400"
        : "text-muted-foreground";

  return (
    <div className="flex-1 h-16 flex flex-col justify-between py-2 px-3 rounded bg-card border border-border">
      <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      <div className="flex items-end gap-2">
        <span
          className={`text-3xl font-semibold tabular-nums ${accentColorMap[accent]}`}
          style={{ fontFamily: "var(--font-plex-mono), monospace" }}
        >
          {value}
        </span>
        {delta && (
          <span className={`text-[10px] mb-1 ${deltaColor}`}>{delta}</span>
        )}
      </div>
      {sparklineData && sparklineData.length >= 2 && (
        <Sparkline data={sparklineData} width={60} height={16} color={sparklineColorMap[accent]} />
      )}
    </div>
  );
}