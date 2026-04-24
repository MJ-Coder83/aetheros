"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  User,
  Brain,
  Star,
  BarChart3,
  Settings2,
  Camera,
  RotateCw,
  ChevronDown,
  ChevronRight,
  Shield,
  TrendingUp,
  Target,
  Zap,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";

/* ── Types ───────────────────────────────────────────────────── */

interface DomainExp {
  domain_id: string;
  level: string;
  score: number;
  interaction_count: number;
  avg_depth: number;
}

interface PrefItem {
  category: string;
  value: number;
  explicit_value: number | null;
  inferred_value: number;
  confidence: number;
}

interface Profile {
  id: string;
  user_id: string;
  status: string;
  domain_expertise: Record<string, DomainExp>;
  preferences: Record<string, PrefItem>;
  interaction_summary: {
    total_interactions: number;
    interactions_by_type: Record<string, number>;
    avg_depth: number;
    peak_depth: number;
    approval_rate: number;
  };
  adaptation_count: number;
  version: number;
  created_at: string;
  updated_at: string;
}

/* ── Status colors ───────────────────────────────────────────── */

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

/* ── Expertise bar ───────────────────────────────────────────── */

function ExpertiseBar({ exp }: { exp: DomainExp }) {
  const pct = Math.round(exp.score * 100);
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="w-32 truncate font-medium">{exp.domain_id}</span>
      <div className="flex-1 h-2 rounded-full bg-inkos-navy-800/30 overflow-hidden">
        <motion.div
          className="h-full bg-gradient-to-r from-inkos-purple to-inkos-cyan"
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

/* ── Preference slider ───────────────────────────────────────── */

function PreferenceSlider({ pref }: { pref: PrefItem }) {
  const pct = Math.round(pref.value * 100);
  const isInferred = pref.explicit_value === null;
  const label = categoryLabels[pref.category] ?? pref.category;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium">{label}</span>
        <span className="text-xs text-muted-foreground">
          {pct}%{" "}
          <span className={isInferred ? "text-amber-400/60" : "text-inkos-cyan/60"}>
            ({isInferred ? "inferred" : "explicit"})
          </span>
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-inkos-navy-800/30 overflow-hidden">
        <motion.div
          className={cn(
            "h-full rounded-full",
            isInferred
              ? "bg-amber-400/60"
              : "bg-inkos-cyan/80",
          )}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.4 }}
        />
      </div>
      <div className="flex items-center justify-between text-[10px] text-muted-foreground/50">
        <span>Confidence: {Math.round(pref.confidence * 100)}%</span>
      </div>
    </div>
  );
}

/* ── Main page ───────────────────────────────────────────────── */

export default function IntelligenceProfilePage() {
  const [userId, setUserId] = useState("");
  const [profile, setProfile] = useState<Profile | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLoadProfile = async () => {
    if (!userId.trim()) return;
    setIsLoading(true);
    setError(null);

    try {
      const res = await fetch(`/api/profiles/${encodeURIComponent(userId.trim())}`, {
        method: "POST",
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: "Failed to load profile" }));
        throw new Error(body.detail ?? `Error ${res.status}`);
      }
      const data = (await res.json()) as Profile;
      setProfile(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsLoading(false);
    }
  };

  const handleRecordInteraction = async (type: string) => {
    if (!userId.trim()) return;
    setIsRecording(true);
    setError(null);

    try {
      const res = await fetch("/api/profiles/interactions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId.trim(),
          interaction_type: type,
          domain: "general",
          depth: 0.5 + Math.random() * 0.5,
          approved: type === "approval",
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: "Failed" }));
        throw new Error(body.detail ?? `Error ${res.status}`);
      }
      const data = (await res.json()) as Profile;
      setProfile(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsRecording(false);
    }
  };

  const domainExps = profile
    ? Object.values(profile.domain_expertise).sort((a, b) => b.score - a.score)
    : [];

  const prefs = profile
    ? Object.values(profile.preferences)
    : [];

  const summary = profile?.interaction_summary;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-8">
      {/* Page header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
          <Brain className="h-8 w-8 text-inkos-purple text-glow-purple" />
          <span>
            <span className="text-inkos-purple text-glow-purple">
              Intelligence
            </span>{" "}
            Profile
          </span>
        </h1>
        <p className="text-muted-foreground mt-1">
          Personalized user profiles that adapt Prime&apos;s behaviour based on
          domain expertise, interaction patterns, and inferred preferences.
        </p>
      </div>

      {/* User ID input */}
      <div className="glass rounded-xl border border-inkos-purple/20 p-5 space-y-4">
        <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
          Load or Create Profile
        </h2>

        <div className="flex gap-3">
          <input
            type="text"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            placeholder="Enter user ID (e.g. alice)"
            className="flex-1 rounded-md border border-inkos-purple/20 bg-inkos-navy-800/30 px-3 py-2 text-sm placeholder:text-muted-foreground/50 focus:border-inkos-cyan focus:outline-none focus:ring-1 focus:ring-inkos-cyan"
          />
          <button
            onClick={handleLoadProfile}
            disabled={!userId.trim() || isLoading}
            className={cn(
              "flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-all",
              userId.trim() && !isLoading
                ? "bg-inkos-purple/80 text-white hover:bg-inkos-purple"
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

        {/* Quick interaction buttons */}
        {userId.trim() && (
          <div className="flex flex-wrap gap-2 pt-2 border-t border-inkos-purple/10">
            <span className="text-[10px] uppercase text-muted-foreground self-center mr-1">
              Record:
            </span>
            {(["query", "approval", "rejection", "simulation", "feedback"] as const).map(
              (type) => (
                <button
                  key={type}
                  onClick={() => handleRecordInteraction(type)}
                  disabled={isRecording}
                  className="text-[10px] px-2 py-1 rounded border border-inkos-purple/15 text-muted-foreground hover:text-inkos-cyan hover:border-inkos-cyan/30 transition-all"
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

      {/* Profile display */}
      {profile && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          {/* Overview cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="glass rounded-lg border border-inkos-purple/15 p-3 text-center">
              <div className="text-2xl font-bold text-inkos-cyan">
                {summary?.total_interactions ?? 0}
              </div>
              <div className="text-[10px] uppercase text-muted-foreground mt-1">
                Interactions
              </div>
            </div>
            <div className="glass rounded-lg border border-inkos-purple/15 p-3 text-center">
              <div className="text-2xl font-bold text-inkos-purple">
                {domainExps.length}
              </div>
              <div className="text-[10px] uppercase text-muted-foreground mt-1">
                Domains
              </div>
            </div>
            <div className="glass rounded-lg border border-inkos-purple/15 p-3 text-center">
              <div className="text-2xl font-bold text-amber-400">
                {Math.round((summary?.avg_depth ?? 0) * 100)}%
              </div>
              <div className="text-[10px] uppercase text-muted-foreground mt-1">
                Avg Depth
              </div>
            </div>
            <div className="glass rounded-lg border border-inkos-purple/15 p-3 text-center">
              <div className="text-2xl font-bold text-emerald-400">
                {Math.round((summary?.approval_rate ?? 0) * 100)}%
              </div>
              <div className="text-[10px] uppercase text-muted-foreground mt-1">
                Approval Rate
              </div>
            </div>
          </div>

          {/* Domain expertise */}
          {domainExps.length > 0 && (
            <div className="glass rounded-xl border border-inkos-purple/20 p-5 space-y-3">
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

          {/* Preferences */}
          {prefs.length > 0 && (
            <div className="glass rounded-xl border border-inkos-purple/20 p-5 space-y-4">
              <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                <Settings2 className="h-4 w-4 text-inkos-cyan" />
                Inferred Preferences
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {prefs.map((pref) => (
                  <PreferenceSlider key={pref.category} pref={pref} />
                ))}
              </div>
            </div>
          )}

          {/* Interaction breakdown */}
          {summary && (
            <div className="glass rounded-xl border border-inkos-purple/20 p-5 space-y-3">
              <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-inkos-purple" />
                Interaction Breakdown
              </h2>
              <div className="flex flex-wrap gap-2">
                {Object.entries(summary.interactions_by_type).map(
                  ([type, count]) => (
                    <div
                      key={type}
                      className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-inkos-navy-800/30 border border-inkos-purple/10"
                    >
                      <span className="text-xs text-muted-foreground">
                        {type}
                      </span>
                      <span className="text-sm font-bold text-inkos-cyan">
                        {count}
                      </span>
                    </div>
                  ),
                )}
              </div>
            </div>
          )}

          {/* Profile metadata */}
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
            <span>Adaptations: {profile.adaptation_count}</span>
            <span className="ml-auto">
              Updated: {new Date(profile.updated_at).toLocaleString()}
            </span>
          </div>
        </motion.div>
      )}
    </div>
  );
}
