"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  accent?: "purple" | "cyan" | "emerald" | "amber";
  sub?: string;
}

const accentMap = {
  purple: "border-inkos-purple/30 text-inkos-purple-400",
  cyan: "border-inkos-cyan/30 text-inkos-cyan-400",
  emerald: "border-emerald-400/30 text-emerald-400",
  amber: "border-amber-400/30 text-amber-400",
};

const glowMap = {
  purple: "glow-purple",
  cyan: "glow-cyan",
  emerald: "",
  amber: "",
};

export function StatCard({
  label,
  value,
  icon,
  accent = "purple",
  sub,
}: StatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn(
        "glass rounded-xl p-5 flex flex-col gap-3 border",
        accentMap[accent],
        glowMap[accent],
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          {label}
        </span>
        <span className="opacity-60">{icon}</span>
      </div>
      <p className="text-3xl font-bold tabular-nums tracking-tight">
        {value}
      </p>
      {sub && (
        <p className="text-xs text-muted-foreground">{sub}</p>
      )}
    </motion.div>
  );
}
