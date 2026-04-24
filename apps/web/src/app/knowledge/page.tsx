"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowRightLeft,
  AlertCircle,
  Loader2,
  ChevronDown,
  ChevronRight,
  ArrowRight,
  Lightbulb,
} from "lucide-react";
import { cn } from "@/lib/utils";

/* ── Types ───────────────────────────────────────────────────── */

interface TransferResult {
  transfer_id: string;
  status: string;
  source_domain_id: string;
  target_domain_id: string;
  items_transferred: number;
  items_adapted: number;
  items_skipped: number;
  total_items: number;
  compatibility_score: number;
  errors: string[];
  warnings: string[];
}

interface TransferRecord {
  id: string;
  source_domain_id: string;
  target_domain_id: string;
  knowledge_types: string[];
  status: string;
  result: TransferResult | null;
  created_at: string;
  completed_at: string | null;
}

interface Recommendation {
  source_domain_id: string;
  compatible_items: number;
  average_compatibility: number;
  top_items: {
    name: string;
    type: string;
    compatibility: number;
    adaptation: string;
  }[];
}

/* ── Status helpers ──────────────────────────────────────────── */

const transferStatusColors: Record<string, string> = {
  draft: "bg-amber-500/20 text-amber-400 border-amber-400/30",
  proposed: "bg-blue-500/20 text-blue-400 border-blue-400/30",
  approved: "bg-indigo-500/20 text-indigo-400 border-indigo-400/30",
  transferring: "bg-inkos-cyan/20 text-inkos-cyan border-inkos-cyan/30",
  completed: "bg-emerald-500/20 text-emerald-400 border-emerald-400/30",
  failed: "bg-red-500/20 text-red-400 border-red-400/30",
  rejected: "bg-gray-500/20 text-gray-400 border-gray-400/30",
  rolled_back: "bg-orange-500/20 text-orange-400 border-orange-400/30",
};

const typeIcons: Record<string, string> = {
  skill: "⚡",
  pattern: "🔄",
  best_practice: "💡",
  config: "⚙️",
  workflow: "📐",
  agent_role: "🤖",
};

/* ── Recommendation card ─────────────────────────────────────── */

function RecommendationCard({
  rec,
  onTransfer,
}: {
  rec: Recommendation;
  onTransfer: (sourceId: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="glass rounded-lg border border-inkos-cyan/8 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ArrowRight className="h-4 w-4 text-inkos-cyan" />
          <span className="font-medium">{rec.source_domain_id}</span>
          <span className="text-muted-foreground text-xs">
            {rec.compatible_items} compatible items
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={cn(
              "text-sm font-bold",
              rec.average_compatibility >= 0.7
                ? "text-emerald-400"
                : rec.average_compatibility >= 0.4
                  ? "text-amber-400"
                  : "text-orange-400",
            )}
          >
            {Math.round(rec.average_compatibility * 100)}%
          </span>
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-muted-foreground hover:text-white"
          >
            {expanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>
        </div>
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="space-y-1.5 pt-2 border-t border-inkos-cyan/4">
              {rec.top_items.map((item, i) => (
                <div
                  key={i}
                  className="flex items-center gap-2 text-xs"
                >
                  <span>{typeIcons[item.type] ?? "📦"}</span>
                  <span className="flex-1 truncate">{item.name}</span>
                  <span className="text-muted-foreground">
                    {Math.round(item.compatibility * 100)}%
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-inkos-navy-800/40 text-muted-foreground border border-inkos-cyan/4">
                    {item.adaptation}
                  </span>
                </div>
              ))}
            </div>
            <button
              onClick={() => onTransfer(rec.source_domain_id)}
              className="mt-3 flex items-center gap-2 rounded-md px-3 py-1.5 text-xs font-medium bg-inkos-cyan/80 text-white hover:bg-inkos-cyan transition-all"
            >
              <ArrowRightLeft className="h-3.5 w-3.5" />
              Transfer from {rec.source_domain_id}
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ── Transfer history card ───────────────────────────────────── */

function TransferHistoryCard({ record }: { record: TransferRecord }) {
  return (
    <div className="glass rounded-lg border border-inkos-cyan/8 p-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 text-sm">
          <span className="font-medium">{record.source_domain_id}</span>
          <ArrowRight className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="font-medium">{record.target_domain_id}</span>
        </div>
        <span
          className={cn(
            "text-[10px] font-medium uppercase px-1.5 py-0.5 rounded border",
            transferStatusColors[record.status] ??
              "bg-muted text-muted-foreground",
          )}
        >
          {record.status}
        </span>
      </div>

      {record.result && (
        <div className="flex items-center gap-4 text-[10px] text-muted-foreground">
          <span>
            {record.result.items_transferred} transferred
          </span>
          <span>{record.result.items_adapted} adapted</span>
          <span>{record.result.items_skipped} skipped</span>
          <span className="ml-auto">
            {Math.round(record.result.compatibility_score * 100)}% compat
          </span>
        </div>
      )}

      {record.result &&
        record.result.errors.length > 0 && (
          <div className="mt-2 pt-2 border-t border-red-400/10 space-y-1">
            {record.result.errors.map((err, i) => (
              <p key={i} className="text-[10px] text-red-400/80">
                {err}
              </p>
            ))}
          </div>
        )}
    </div>
  );
}

/* ── Main page ───────────────────────────────────────────────── */

const KNOWLEDGE_TYPES = [
  "skill",
  "pattern",
  "best_practice",
  "config",
  "workflow",
  "agent_role",
];

const EXAMPLE_DOMAINS = [
  "legal-research",
  "finance-ops",
  "research-lab",
  "engineering",
  "healthcare",
];

export default function KnowledgeTransferPage() {
  const [sourceDomain, setSourceDomain] = useState("");
  const [targetDomain, setTargetDomain] = useState("");
  const [selectedTypes, setSelectedTypes] = useState<string[]>(["skill", "pattern", "best_practice"]);
  const [isTransferring, setIsTransferring] = useState(false);
  const [isRecommending, setIsRecommending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [transfers, setTransfers] = useState<TransferRecord[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);

  const toggleType = (t: string) => {
    setSelectedTypes((prev) =>
      prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t],
    );
  };

  const handleTransfer = async () => {
    if (!sourceDomain.trim() || !targetDomain.trim()) return;
    setIsTransferring(true);
    setError(null);

    try {
      const res = await fetch("/api/knowledge-transfer/transfer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_domain_id: sourceDomain.trim(),
          target_domain_id: targetDomain.trim(),
          source_metadata: { name: sourceDomain.trim() },
          target_metadata: { name: targetDomain.trim() },
          knowledge_types: selectedTypes.length > 0 ? selectedTypes : null,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: "Transfer failed" }));
        throw new Error(body.detail ?? `Error ${res.status}`);
      }
      const record = (await res.json()) as TransferRecord;
      setTransfers((prev) => [record, ...prev]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsTransferring(false);
    }
  };

  const handleRecommendations = async () => {
    if (!targetDomain.trim()) return;
    setIsRecommending(true);
    setError(null);

    try {
      const res = await fetch("/api/knowledge-transfer/recommendations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          domain_id: targetDomain.trim(),
          all_domain_metadata: {
            "legal-research": { name: "Legal Research", skills: [{ name: "Case Law Search" }] },
            "finance-ops": { name: "Finance Operations", skills: [{ name: "Risk Assessment" }] },
            "research-lab": { name: "Research Lab", skills: [{ name: "Data Analysis" }] },
            "engineering": { name: "Engineering", skills: [{ name: "Code Review" }] },
            "healthcare": { name: "Healthcare", skills: [{ name: "Diagnostics" }] },
          },
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: "Request failed" }));
        throw new Error(body.detail ?? `Error ${res.status}`);
      }
      const recs = (await res.json()) as Recommendation[];
      setRecommendations(recs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsRecommending(false);
    }
  };

  const handleRecommendedTransfer = (sourceId: string) => {
    setSourceDomain(sourceId);
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-8 page-transition">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-3">
          <ArrowRightLeft className="h-8 w-8 text-inkos-cyan text-glow-teal" />
          <span>
            <span className="text-inkos-cyan text-glow-teal">
              Cross-Domain
            </span>{" "}
            Knowledge Transfer
          </span>
        </h1>
        <p className="text-muted-foreground mt-1">
          Identify, package, and transfer skills, patterns, and best practices
          between domains with compatibility assessment and adaptation.
        </p>
      </div>

      {/* Transfer form */}
      <div className="glass rounded-xl border border-inkos-cyan/8 p-5 space-y-4">
        <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
          Initiate Transfer
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">
              Source Domain
            </label>
            <input
              type="text"
              value={sourceDomain}
              onChange={(e) => setSourceDomain(e.target.value)}
              placeholder="e.g. legal-research"
              className="w-full rounded-md border border-inkos-cyan/8 bg-inkos-navy-800/30 px-3 py-2 text-sm placeholder:text-muted-foreground/50 focus:border-inkos-cyan focus:outline-none focus:ring-1 focus:ring-inkos-cyan"
            />
            <div className="flex flex-wrap gap-1 mt-1.5">
              {EXAMPLE_DOMAINS.map((d) => (
                <button
                  key={d}
                  onClick={() => setSourceDomain(d)}
                  className="text-[10px] px-1.5 py-0.5 rounded border border-inkos-cyan/8 text-muted-foreground hover:text-inkos-cyan hover:border-inkos-cyan/20 transition-all"
                >
                  {d}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">
              Target Domain
            </label>
            <input
              type="text"
              value={targetDomain}
              onChange={(e) => setTargetDomain(e.target.value)}
              placeholder="e.g. finance-ops"
              className="w-full rounded-md border border-inkos-cyan/8 bg-inkos-navy-800/30 px-3 py-2 text-sm placeholder:text-muted-foreground/50 focus:border-inkos-cyan focus:outline-none focus:ring-1 focus:ring-inkos-cyan"
            />
            <div className="flex flex-wrap gap-1 mt-1.5">
              {EXAMPLE_DOMAINS.map((d) => (
                <button
                  key={d}
                  onClick={() => setTargetDomain(d)}
                  className="text-[10px] px-1.5 py-0.5 rounded border border-inkos-cyan/8 text-muted-foreground hover:text-inkos-cyan hover:border-inkos-cyan/20 transition-all"
                >
                  {d}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Knowledge type chips */}
        <div>
          <label className="text-xs text-muted-foreground mb-1.5 block">
            Knowledge Types
          </label>
          <div className="flex flex-wrap gap-1.5">
            {KNOWLEDGE_TYPES.map((t) => (
              <button
                key={t}
                onClick={() => toggleType(t)}
                className={cn(
                  "text-xs px-2.5 py-1 rounded-md border transition-all",
                  selectedTypes.includes(t)
                    ? "bg-inkos-cyan/30 border-inkos-cyan/15 text-inkos-cyan"
                    : "bg-inkos-navy-800/30 border-inkos-cyan/4 text-muted-foreground hover:border-inkos-cyan/8",
                )}
              >
                {typeIcons[t]} {t.replace("_", " ")}
              </button>
            ))}
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={handleTransfer}
            disabled={
              !sourceDomain.trim() ||
              !targetDomain.trim() ||
              isTransferring
            }
            className={cn(
              "flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-all",
              sourceDomain.trim() && targetDomain.trim() && !isTransferring
                ? "bg-inkos-cyan/80 text-white hover:bg-inkos-cyan"
                : "bg-inkos-navy-800/40 text-muted-foreground cursor-not-allowed",
            )}
          >
            {isTransferring ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Transferring...
              </>
            ) : (
              <>
                <ArrowRightLeft className="h-4 w-4" />
                Transfer Knowledge
              </>
            )}
          </button>

          <button
            onClick={handleRecommendations}
            disabled={!targetDomain.trim() || isRecommending}
            className={cn(
              "flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-all",
              targetDomain.trim() && !isRecommending
                ? "bg-inkos-cyan/80 text-inkos-navy-900 hover:bg-inkos-cyan"
                : "bg-inkos-navy-800/40 text-muted-foreground cursor-not-allowed",
            )}
          >
            {isRecommending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Finding...
              </>
            ) : (
              <>
                <Lightbulb className="h-4 w-4" />
                Get Recommendations
              </>
            )}
          </button>
        </div>

        {error && (
          <div className="flex items-start gap-2 rounded-md border border-red-400/30 bg-red-500/10 p-3">
            <AlertCircle className="h-4 w-4 text-red-400 mt-0.5 shrink-0" />
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}
      </div>

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
            Recommendations for &ldquo;{targetDomain}&rdquo;
          </h2>
          <div className="grid gap-3">
            {recommendations.map((rec) => (
              <RecommendationCard
                key={rec.source_domain_id}
                rec={rec}
                onTransfer={handleRecommendedTransfer}
              />
            ))}
          </div>
        </div>
      )}

      {/* Transfer history */}
      {transfers.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
            Transfer History ({transfers.length})
          </h2>
          <div className="grid gap-3">
            {transfers.map((t) => (
              <TransferHistoryCard key={t.id} record={t} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
