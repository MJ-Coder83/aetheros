"use client";

import { motion } from "framer-motion";
import type { ProviderInfo } from "@/types";
import { cn } from "@/lib/utils";

interface ProviderCardProps {
  provider: ProviderInfo;
  isActive: boolean;
  onClick: () => void;
}

const PROVIDER_COLORS: Record<string, string> = {
  openai: "bg-emerald-500/20 text-emerald-400",
  anthropic: "bg-orange-500/20 text-orange-400",
  openrouter: "bg-violet-500/20 text-violet-400",
  nvidia: "bg-green-500/20 text-green-400",
  grok: "bg-blue-500/20 text-blue-400",
  google: "bg-red-500/20 text-red-400",
  mistral: "bg-cyan-500/20 text-cyan-400",
  deepseek: "bg-indigo-500/20 text-indigo-400",
};

function getProviderColor(providerId: string) {
  return PROVIDER_COLORS[providerId] ?? "bg-inkos-cyan/15 text-inkos-cyan";
}

export function ProviderCard({ provider, isActive, onClick }: ProviderCardProps) {
  const colorClass = getProviderColor(provider.provider_id);
  const initial = provider.display_name.charAt(0).toUpperCase();

  return (
    <motion.button
      onClick={onClick}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      transition={{ duration: 0.15, ease: [0.25, 0.46, 0.45, 0.94] }}
      className={cn(
        "w-full text-left rounded-xl border p-4 transition-all duration-200",
        "bg-white/[0.02] hover:bg-white/[0.04]",
        isActive
          ? "border-inkos-cyan/30 shadow-sm shadow-inkos-cyan/5"
          : "border-white/[0.04] hover:border-white/[0.08]",
        "focus-ring"
      )}
    >
      <div className="flex items-start gap-3">
        <div
          className={cn(
            "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-sm font-bold",
            colorClass
          )}
        >
          {provider.icon ? (
            <img
              src={provider.icon}
              alt={provider.display_name}
              className="h-6 w-6"
            />
          ) : (
            initial
          )}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium truncate">
              {provider.display_name}
            </span>
            <span
              className={cn(
                "h-1.5 w-1.5 shrink-0 rounded-full",
                provider.has_key_configured
                  ? "bg-emerald-400"
                  : "bg-muted-foreground/30"
              )}
            />
          </div>

          {provider.selected_model && (
            <p className="mt-1 text-[11px] text-muted-foreground truncate">
              {provider.selected_model}
            </p>
          )}

          {!provider.selected_model && provider.models.length > 0 && (
            <p className="mt-1 text-[11px] text-muted-foreground/50">
              {provider.models.length} model{provider.models.length !== 1 ? "s" : ""}
            </p>
          )}
        </div>
      </div>

      {isActive && (
        <motion.div
          layoutId="active-provider-bar"
          className="mt-3 h-0.5 rounded-full bg-inkos-cyan/40"
          transition={{ duration: 0.15, ease: [0.25, 0.46, 0.45, 0.94] }}
        />
      )}
    </motion.button>
  );
}
