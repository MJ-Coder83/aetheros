import type { DomainDescriptor } from "@/types";
import { Sparkline } from "./sparkline";

interface DomainsStripProps {
  domains: DomainDescriptor[];
  skillsByDomain?: Record<string, number>;
}

function mockSparkline(seed: number): number[] {
  const data: number[] = [];
  let val = 5 + (seed % 4);
  for (let i = 0; i < 7; i++) {
    val = Math.max(1, Math.min(15, val + (Math.sin(seed + i * 0.9) > 0 ? -1 : 1)));
    data.push(val);
  }
  return data;
}

export function DomainsStrip({ domains, skillsByDomain }: DomainsStripProps) {
  if (!domains || domains.length === 0) {
    return (
      <div className="mb-3">
        <span className="text-xs font-semibold text-foreground mb-2 block">
          DOMAINS
        </span>
        <div className="flex gap-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="flex-1 bg-card rounded border border-border p-2 h-16"
            >
              <div className="h-3 w-16 bg-secondary animate-pulse rounded mb-2" />
              <div className="h-2 w-12 bg-secondary animate-pulse rounded" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="mb-3">
      <span className="text-xs font-semibold text-foreground mb-2 block">
        DOMAINS
      </span>
      <div className="flex gap-2">
        {domains.slice(0, 3).map((domain, i) => {
          const skillCount = skillsByDomain?.[domain.name] ?? 0;
          const sparkData = mockSparkline(domain.name.length + i);
          return (
            <div
              key={domain.domain_id}
              className="flex-1 bg-card rounded border border-border p-2"
            >
              <div className="flex items-center justify-between mb-1">
                <span
                  className="text-[10px] text-inkos-cyan truncate"
                  style={{ fontFamily: "var(--font-plex-mono), monospace" }}
                >
                  {domain.name}
                </span>
                <span className="text-[9px] text-muted-foreground">
                  {domain.agent_count} agents
                </span>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-[9px] text-muted-foreground">
                  {skillCount} skills
                </span>
                <Sparkline
                  data={sparkData}
                  width={40}
                  height={12}
                  color={i === 0 ? "emerald" : i === 1 ? "cyan" : "amber"}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}