"use client";

import { Brain, Star, Settings2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { UserProfile } from "@/types";

const levelColors: Record<string, string> = {
  novice: "text-gray-400",
  intermediate: "text-blue-400",
  advanced: "text-purple-400",
  expert: "text-inkos-cyan",
};

export function ProfileSummaryCard({
  profile,
  isLoading,
}: {
  profile: UserProfile | null | undefined;
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <div className="p-3 space-y-2">
        <div className="h-3 w-24 bg-secondary animate-pulse rounded" />
        <div className="h-2 w-full bg-secondary animate-pulse rounded" />
        <div className="h-2 w-3/4 bg-secondary animate-pulse rounded" />
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="p-3 text-xs text-muted-foreground/50">
        No profile data
      </div>
    );
  }

  const intel = profile.intelligence;
  const domainExps = Object.values(intel.domain_expertise)
    .sort((a, b) => b.score - a.score)
    .slice(0, 3);
  const topPrefs = Object.values(intel.preferences)
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, 3);

  return (
    <div className="p-3 space-y-2.5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
          <Brain className="h-3.5 w-3.5 text-inkos-cyan" />
          PROFILE
        </span>
        <a
          href="/profile"
          className="text-[10px] text-inkos-cyan hover:underline"
        >
          View →
        </a>
      </div>

      <div className="flex gap-3 text-center">
        <div className="flex-1">
          <div className="text-sm font-bold text-inkos-cyan tabular-nums">
            {intel.interaction_summary.total_interactions}
          </div>
          <div className="text-[9px] uppercase text-muted-foreground">Interactions</div>
        </div>
        <div className="flex-1">
          <div className="text-sm font-bold text-emerald-400 tabular-nums">
            {Math.round(intel.interaction_summary.approval_rate * 100)}%
          </div>
          <div className="text-[9px] uppercase text-muted-foreground">Approve</div>
        </div>
        <div className="flex-1">
          <div className="text-sm font-bold text-amber-400 tabular-nums">
            {Math.round(intel.interaction_summary.avg_depth * 100)}%
          </div>
          <div className="text-[9px] uppercase text-muted-foreground">Depth</div>
        </div>
      </div>

      {domainExps.length > 0 && (
        <div className="space-y-1">
          <div className="flex items-center gap-1 text-muted-foreground">
            <Star className="h-2.5 w-2.5" />
            <span className="text-[9px] uppercase tracking-wider">Domains</span>
          </div>
          {domainExps.map((exp) => (
            <div key={exp.domain_id} className="flex items-center justify-between text-[11px]">
              <span className="truncate text-muted-foreground">{exp.domain_id}</span>
              <span className={cn("font-mono", levelColors[exp.level] ?? "text-muted-foreground")}>
                {exp.level}
              </span>
            </div>
          ))}
        </div>
      )}

      {topPrefs.length > 0 && (
        <div className="space-y-1">
          <div className="flex items-center gap-1 text-muted-foreground">
            <Settings2 className="h-2.5 w-2.5" />
            <span className="text-[9px] uppercase tracking-wider">Prefs</span>
          </div>
          {topPrefs.map((pref) => (
            <div key={pref.category} className="flex items-center justify-between text-[11px]">
              <span className="truncate text-muted-foreground">{pref.category.replace(/_/g, " ")}</span>
              <span className="font-mono tabular-nums text-muted-foreground">
                {Math.round(pref.value * 100)}%
              </span>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between text-[9px] text-muted-foreground/40 pt-1 border-t border-border">
        <span className="uppercase">{profile.status}</span>
        <span>v{profile.version} · {intel.adaptation_count} adaptations</span>
      </div>
    </div>
  );
}
