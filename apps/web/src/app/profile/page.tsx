"use client";

import { useState, useCallback } from "react";
import { motion } from "framer-motion";
import {
  User,
  Brain,
  Star,
  BarChart3,
  Settings2,
  Shield,
  Loader2,
  Camera,
  History,
  RotateCcw,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type {
  UserProfile,
  DomainExpertise,
  UserPreference,
  PreferenceCategory,
  ProfileSnapshot,
  InteractionType,
} from "@/types";
import {
  useGetOrCreateProfile,
  useRecordInteraction,
  useSetPreference,
  useProfileSnapshots,
  useCreateSnapshot,
  useRollbackProfile,
} from "@/hooks/use-api";

const statusColors: Record<string, string> = {
  active: "bg-emerald-500/20 text-emerald-400 border-emerald-400/30",
  archived: "bg-gray-500/20 text-gray-400 border-gray-400/30",
  suspended: "bg-amber-500/20 text-amber-400 border-amber-400/30",
};

const levelColors: Record<string, string> = {
  novice: "text-gray-400",
  intermediate: "text-blue-400",
  advanced: "text-purple-400",
  expert: "text-inkos-cyan",
};

const categoryLabels: Record<string, string> = {
  response_detail: "Response Detail",
  automation_level: "Automation Level",
  notification_frequency: "Notification Freq",
  risk_tolerance: "Risk Tolerance",
  workflow_style: "Workflow Style",
  explanation_depth: "Explanation Depth",
  suggestion_frequency: "Suggestion Freq",
};

const VALID_CATEGORIES: PreferenceCategory[] = [
  "response_detail",
  "automation_level",
  "notification_frequency",
  "risk_tolerance",
  "workflow_style",
  "explanation_depth",
  "suggestion_frequency",
];

function ExpertiseBar({ exp }: { exp: DomainExpertise }) {
  const pct = Math.round(exp.score * 100);
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="w-32 truncate font-medium">{exp.domain_id}</span>
      <div className="flex-1 h-2 rounded-full bg-inkos-navy-800/30 overflow-hidden">
        <motion.div
          className="h-full bg-gradient-to-r from-inkos-teal-300 to-inkos-cyan"
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>
      <span className={cn("w-16 text-right text-xs font-medium", levelColors[exp.level] ?? "text-muted-foreground")}>
        {exp.level}
      </span>
      <span className="w-10 text-right text-xs text-muted-foreground">{pct}%</span>
    </div>
  );
}

function PreferenceSlider({
  pref,
  onSetExplicit,
}: {
  pref: UserPreference;
  onSetExplicit: (category: PreferenceCategory, value: number) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draftValue, setDraftValue] = useState(pref.value);
  const pct = Math.round(pref.value * 100);
  const isInferred = pref.explicit_value === null;
  const label = categoryLabels[pref.category] ?? pref.category;

  const handleSave = useCallback(() => {
    onSetExplicit(pref.category as PreferenceCategory, draftValue);
    setEditing(false);
  }, [draftValue, onSetExplicit, pref.category]);

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium">{label}</span>
        <span className="text-xs text-muted-foreground">
          {pct}%{" "}
          <span className={isInferred ? "text-amber-400/60" : "text-inkos-cyan/60"}>
            ({isInferred ? "inferred" : "explicit"})
          </span>
        </span>
      </div>
      {editing ? (
        <div className="space-y-2">
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={draftValue}
            onChange={(e) => setDraftValue(parseFloat(e.target.value))}
            className="w-full h-1.5 accent-inkos-cyan cursor-pointer"
          />
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-muted-foreground">
              {Math.round(draftValue * 100)}%
            </span>
            <div className="flex gap-1.5">
              <button
                onClick={() => setEditing(false)}
                className="text-[10px] px-2 py-0.5 rounded border border-white/[0.06] text-muted-foreground hover:text-foreground transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                className="text-[10px] px-2 py-0.5 rounded border border-inkos-cyan/20 bg-inkos-cyan/10 text-inkos-cyan hover:bg-inkos-cyan/20 transition-colors"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div
          className="cursor-pointer group"
          onClick={() => {
            setDraftValue(pref.value);
            setEditing(true);
          }}
        >
          <div className="h-1.5 rounded-full bg-inkos-navy-800/30 overflow-hidden">
            <motion.div
              className={cn(
                "h-full rounded-full",
                isInferred ? "bg-amber-400/60" : "bg-inkos-cyan/80",
              )}
              initial={{ width: 0 }}
              animate={{ width: `${pct}%` }}
              transition={{ duration: 0.4 }}
            />
          </div>
          <div className="flex items-center justify-between text-[10px] text-muted-foreground/50">
            <span>Confidence: {Math.round(pref.confidence * 100)}%</span>
            <span className="opacity-0 group-hover:opacity-100 transition-opacity text-inkos-cyan">
              Click to edit
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

function SnapshotsPanel({
  snapshots,
  onRollback,
  isRollingBack,
}: {
  snapshots: ProfileSnapshot[];
  onRollback: (snapshotId: string) => void;
  isRollingBack: boolean;
}) {
  if (snapshots.length === 0) {
    return (
      <p className="text-xs text-muted-foreground/50">No snapshots yet. Create one to preserve your current profile state.</p>
    );
  }

  return (
    <div className="space-y-2 max-h-48 overflow-y-auto">
      {snapshots.map((snap) => (
        <div
          key={snap.id}
          className="flex items-center justify-between px-3 py-2 rounded-lg bg-inkos-navy-800/30 border border-inkos-cyan/4"
        >
          <div>
            <span className="text-xs font-medium">v{snap.id.slice(0,8)}</span>
            {snap.reason && (
              <span className="text-[10px] text-muted-foreground ml-2">{snap.reason}</span>
            )}
            <span className="text-[10px] text-muted-foreground/50 ml-2">
              {new Date(snap.created_at).toLocaleString()}
            </span>
          </div>
          <button
            onClick={() => onRollback(snap.id)}
            disabled={isRollingBack}
            className="text-[10px] px-2 py-0.5 rounded border border-amber-400/15 text-amber-400/70 hover:text-amber-400 hover:border-amber-400/30 transition-colors disabled:opacity-40"
          >
            <RotateCcw className="h-3 w-3 inline mr-1" />
            Rollback
          </button>
        </div>
      ))}
    </div>
  );
}

export default function ProfilePage() {
  const [userId, setUserId] = useState("");
  const [activeUserId, setActiveUserId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: profile, isLoading, refetch } = useGetOrCreateProfile(activeUserId);
  const { data: snapshots } = useProfileSnapshots(activeUserId);
  const recordInteraction = useRecordInteraction();
  const setPreference = useSetPreference();
  const createSnapshot = useCreateSnapshot();
  const rollbackProfile = useRollbackProfile();

  const handleLoadProfile = useCallback(() => {
    if (!userId.trim()) return;
    setError(null);
    setActiveUserId(userId.trim());
  }, [userId]);

  const handleRecordInteraction = useCallback(
    (type: string) => {
      if (!activeUserId) return;
      recordInteraction.mutate({
        user_id: activeUserId,
        interaction_type: type as InteractionType,
        domain: "general",
        depth: 0.75,
        approved: type === "approval",
      });
    },
    [activeUserId, recordInteraction],
  );

  const handleSetPreference = useCallback(
    (category: PreferenceCategory, value: number) => {
      if (!activeUserId) return;
      setPreference.mutate({ user_id: activeUserId, category, value });
    },
    [activeUserId, setPreference],
  );

  const handleCreateSnapshot = useCallback(() => {
    if (!activeUserId) return;
    createSnapshot.mutate({ userId: activeUserId, reason: "Manual snapshot" });
  }, [activeUserId, createSnapshot]);

  const handleRollback = useCallback(
    (snapshotId: string) => {
      if (!activeUserId) return;
      rollbackProfile.mutate({ userId: activeUserId, snapshotId });
    },
    [activeUserId, rollbackProfile],
  );

  const domainExps = profile
    ? Object.values(profile.intelligence.domain_expertise).sort((a, b) => b.score - a.score)
    : [];

  const prefs = profile ? Object.values(profile.intelligence.preferences) : [];
  const summary = profile?.intelligence?.interaction_summary;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-8 page-transition">
      <div>
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-3">
          <Brain className="h-8 w-8 text-inkos-cyan text-glow-teal" />
          <span>
            <span className="text-inkos-cyan text-glow-teal">Intelligence</span>{" "}
            Profile
          </span>
        </h1>
        <p className="text-muted-foreground mt-1">
          Personalized user profiles that adapt Prime&apos;s behaviour based on
          domain expertise, interaction patterns, and inferred preferences.
        </p>
      </div>

      <div className="glass rounded-xl border border-inkos-cyan/8 p-5 space-y-4">
        <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
          Load or Create Profile
        </h2>
        <div className="flex gap-3">
          <input
            type="text"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleLoadProfile()}
            placeholder="Enter user ID (e.g. alice)"
            className="flex-1 rounded-md border border-inkos-cyan/8 bg-inkos-navy-800/30 px-3 py-2 text-sm placeholder:text-muted-foreground/50 focus:border-inkos-cyan focus:outline-none focus:ring-1 focus:ring-inkos-cyan"
          />
          <button
            onClick={handleLoadProfile}
            disabled={!userId.trim() || isLoading}
            className={cn(
              "flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-all",
              userId.trim() && !isLoading
                ? "bg-inkos-cyan/80 text-white hover:bg-inkos-cyan"
                : "bg-inkos-navy-800/40 text-muted-foreground cursor-not-allowed",
            )}
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <User className="h-4 w-4" />
            )}
            Load Profile
          </button>
        </div>

        {activeUserId && (
          <div className="flex flex-wrap gap-2 pt-2 border-t border-inkos-cyan/4">
            <span className="text-[10px] uppercase text-muted-foreground self-center mr-1">
              Record:
            </span>
            {(["query", "approval", "rejection", "simulation", "feedback"] as const).map(
              (type) => (
                <button
                  key={type}
                  onClick={() => handleRecordInteraction(type)}
                  disabled={recordInteraction.isPending}
                  className="text-[10px] px-2 py-1 rounded border border-inkos-cyan/8 text-muted-foreground hover:text-inkos-cyan hover:border-inkos-cyan/20 transition-all"
                >
                  {type}
                </button>
              ),
            )}
          </div>
        )}

        {error && (
          <div className="flex items-start gap-2 rounded-md border border-red-400/30 bg-red-500/10 p-3">
            <Shield className="h-4 w-4 text-red-400 mt-0.5 shrink-0" />
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}
      </div>

      {profile && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="glass rounded-lg border border-inkos-cyan/8 p-3 text-center">
              <div className="text-2xl font-bold text-inkos-cyan">
                {summary?.total_interactions ?? 0}
              </div>
              <div className="text-[10px] uppercase text-muted-foreground mt-1">
                Interactions
              </div>
            </div>
            <div className="glass rounded-lg border border-inkos-cyan/8 p-3 text-center">
              <div className="text-2xl font-bold text-inkos-cyan">
                {domainExps.length}
              </div>
              <div className="text-[10px] uppercase text-muted-foreground mt-1">
                Domains
              </div>
            </div>
            <div className="glass rounded-lg border border-inkos-cyan/8 p-3 text-center">
              <div className="text-2xl font-bold text-amber-400">
                {Math.round((summary?.avg_depth ?? 0) * 100)}%
              </div>
              <div className="text-[10px] uppercase text-muted-foreground mt-1">
                Avg Depth
              </div>
            </div>
            <div className="glass rounded-lg border border-inkos-cyan/8 p-3 text-center">
              <div className="text-2xl font-bold text-emerald-400">
                {Math.round((summary?.approval_rate ?? 0) * 100)}%
              </div>
              <div className="text-[10px] uppercase text-muted-foreground mt-1">
                Approval Rate
              </div>
            </div>
          </div>

          {domainExps.length > 0 && (
            <div className="glass rounded-xl border border-inkos-cyan/8 p-5 space-y-3">
              <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                <Star className="h-4 w-4 text-amber-400" />
                Domain Expertise
              </h2>
              <div className="space-y-2.5">
                {domainExps.map((exp) => (
                  <ExpertiseBar key={exp.domain_id} exp={exp} />
                ))}
              </div>
            </div>
          )}

          <div className="glass rounded-xl border border-inkos-cyan/8 p-5 space-y-4">
            <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Settings2 className="h-4 w-4 text-inkos-cyan" />
              Preferences
              <span className="ml-auto text-[10px] font-normal text-muted-foreground/50">
                Click any slider to set an explicit value
              </span>
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {VALID_CATEGORIES.map((cat) => {
                const pref = prefs.find((p) => p.category === cat);
                if (pref) {
                  return (
                    <PreferenceSlider
                      key={pref.category}
                      pref={pref}
                      onSetExplicit={handleSetPreference}
                    />
                  );
                }
                return (
                  <div key={cat} className="space-y-1">
                    <span className="text-xs font-medium">{categoryLabels[cat] ?? cat}</span>
                    <div
                      className="cursor-pointer group"
                      onClick={() => handleSetPreference(cat, 0.5)}
                    >
                      <div className="h-1.5 rounded-full bg-inkos-navy-800/30 overflow-hidden">
                        <div className="h-full w-0" />
                      </div>
                      <div className="flex items-center justify-between text-[10px] text-muted-foreground/50">
                        <span>Not yet set</span>
                        <span className="opacity-0 group-hover:opacity-100 transition-opacity text-inkos-cyan">
                          Click to set
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {summary && (
            <div className="glass rounded-xl border border-inkos-cyan/8 p-5 space-y-3">
              <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-inkos-cyan" />
                Interaction Breakdown
              </h2>
              <div className="flex flex-wrap gap-2">
                {Object.entries(summary.interactions_by_type).map(
                  ([type, count]) => (
                    <div
                      key={type}
                      className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-inkos-navy-800/30 border border-inkos-cyan/4"
                    >
                      <span className="text-xs text-muted-foreground">{type}</span>
                      <span className="text-sm font-bold text-inkos-cyan">{count}</span>
                    </div>
                  ),
                )}
              </div>
            </div>
          )}

          <div className="glass rounded-xl border border-inkos-cyan/8 p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                <History className="h-4 w-4 text-inkos-cyan" />
                Snapshots
              </h2>
              <button
                onClick={handleCreateSnapshot}
                disabled={createSnapshot.isPending}
                className="text-[10px] px-2 py-1 rounded border border-inkos-cyan/15 text-muted-foreground hover:text-inkos-cyan hover:border-inkos-cyan/30 transition-all disabled:opacity-40"
              >
                {createSnapshot.isPending ? (
                  <Loader2 className="h-3 w-3 animate-spin inline mr-1" />
                ) : (
                  <Camera className="h-3 w-3 inline mr-1" />
                )}
                Create Snapshot
              </button>
            </div>
            <SnapshotsPanel
              snapshots={snapshots ?? []}
              onRollback={handleRollback}
              isRollingBack={rollbackProfile.isPending}
            />
          </div>

          <div className="flex items-center gap-4 text-[10px] text-muted-foreground">
            <span
              className={cn(
                "uppercase px-1.5 py-0.5 rounded border",
                statusColors[profile.status] ?? "bg-muted",
              )}
            >
              {profile.status}
            </span>
            <span>Version {profile.version}</span>
            <span>Adaptations: {profile.intelligence.adaptation_count}</span>
            <span className="ml-auto">
              Updated: {new Date(profile.updated_at).toLocaleString()}
            </span>
          </div>
        </motion.div>
      )}
    </div>
  );
}
