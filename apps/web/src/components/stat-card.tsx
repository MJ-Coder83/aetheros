"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  accent?: "cyan" | "emerald" | "amber" | "teal";
  sub?: string;
}

const accentMap = {
  cyan: "border-inkos-cyan/15 text-inkos-cyan",
  emerald: "border-emerald-500/15 text-emerald-400",
  teal: "border-inkos-teal-300/15 text-inkos-teal-300",
  amber: "border-amber-400/15 text-amber-400",
};

const glowMap = {
  cyan: "glow-cyan",
  emerald: "glow-emerald",
  teal: "glow-teal",
  amber: "",
};

const iconBgMap = {
  cyan: "bg-inkos-cyan/8",
  emerald: "bg-emerald-500/8",
  teal: "bg-inkos-teal-300/8",
  amber: "bg-amber-400/8",
};

export function StatCard({
  label,
  value,
  icon,
  accent = "cyan",
  sub,
}: StatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
      className={cn(
        "glass glass-hover rounded-xl p-5 flex flex-col gap-3 border",
        accentMap[accent],
        glowMap[accent],
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground">
          {label}
        </span>
        <div
          className={cn(
            "h-8 w-8 rounded-lg flex items-center justify-center",
            iconBgMap[accent],
          )}
        >
          <span className="opacity-70">{icon}</span>
        </div>
      </div>
      <p className="text-3xl font-bold tabular-nums tracking-tight text-foreground">
        {value}
      </p>
      {sub && (
        <p className="text-xs text-muted-foreground leading-relaxed">{sub}</p>
      )}
    </motion.div>
  );
}
