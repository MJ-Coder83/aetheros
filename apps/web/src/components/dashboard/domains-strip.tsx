"use client";

import { motion } from "framer-motion";
import { Sparkline } from "./sparkline";
import type { DomainDescriptor } from "@/types";

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
        <span className="text-xs font-semibold text-foreground mb-2 block tracking-wide">
          DOMAINS
        </span>
        <div className="flex gap-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <motion.div
              key={i}
              className="flex-1 rounded-lg p-2 h-16 relative"
              style={{
                background: "rgba(15, 22, 41, 0.6)",
                backdropFilter: "blur(12px)",
                border: "1px solid rgba(34, 211, 238, 0.08)",
              }}
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.1 }}
            >
              <div className="h-3 w-16 bg-secondary animate-pulse rounded mb-2" />
              <div className="h-2 w-12 bg-secondary animate-pulse rounded" />
            </motion.div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="mb-3">
      <span className="text-xs font-semibold text-foreground mb-2 block tracking-wide">
        DOMAINS
      </span>
      <div className="flex gap-2">
        {domains.slice(0, 3).map((domain, i) => {
          const skillCount = skillsByDomain?.[domain.name] ?? 0;
          const sparkData = mockSparkline(domain.name.length + i);
          return (
            <motion.div
              key={domain.domain_id}
              className="flex-1 rounded-lg p-2 relative overflow-hidden corner-accent"
              style={{
                background: `
                  linear-gradient(135deg, rgba(34, 211, 238, 0.03) 0%, transparent 50%, rgba(103, 232, 249, 0.02) 100%),
                  rgba(15, 22, 41, 0.7)
                `,
                backdropFilter: "blur(16px)",
                border: "1px solid rgba(34, 211, 238, 0.1)",
                boxShadow: "inset 0 1px 0 rgba(34, 211, 238, 0.04), 0 4px 8px rgba(0, 0, 0, 0.2)",
              }}
              initial={{ opacity: 0, x: 8, scale: 0.98 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              transition={{ delay: i * 0.1 }}
              whileHover={{
                y: -2,
                borderColor: "rgba(34, 211, 238, 0.2)",
                boxShadow: "inset 0 1px 0 rgba(34, 211, 238, 0.08), 0 8px 16px rgba(0, 0, 0, 0.3)",
              }}
            >
              {/* Subtle glow overlay */}
              <div
                className="absolute inset-0 pointer-events-none"
                style={{
                  background: "radial-gradient(ellipse at top right, rgba(34, 211, 238, 0.06) 0%, transparent 50%)",
                }}
              />

              <div className="flex items-center justify-between mb-1 relative z-10">
                <span
                  className="text-[10px] text-inkos-cyan truncate terminal-text-glow"
                  style={{ fontFamily: "var(--font-plex-mono), monospace" }}
                >
                  {domain.name}
                </span>
                <span className="text-[9px] text-muted-foreground font-[family-name:var(--font-plex-mono)]">
                  {domain.agent_count}
                </span>
              </div>
              <div className="flex items-center gap-1 relative z-10">
                <span className="text-[9px] text-muted-foreground">
                  {skillCount} skills
                </span>
                <Sparkline
                  data={sparkData}
                  width={40}
                  height={12}
                  color={i === 0 ? "emerald" : i === 1 ? "cyan" : "amber"}
                  animated
                />
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
