"use client";

import { useState, useMemo } from "react";
import { motion } from "framer-motion";
import { ScrollText, Search, Filter } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useTapeEntries } from "@/hooks/use-api";
import { cn } from "@/lib/utils";
import { formatDistanceToNow, format } from "date-fns";

const EVENT_TYPE_COLOURS: Record<string, string> = {
  "prime.introspection": "border-inkos-purple/40 text-inkos-purple-400",
  "prime.proposal_created": "border-inkos-cyan/40 text-inkos-cyan-400",
  "prime.proposal_approved": "border-emerald-400/40 text-emerald-400",
  "prime.proposal_rejected": "border-red-400/40 text-red-400",
  "prime.proposal_implemented": "border-emerald-400/40 text-emerald-400",
  "prime.skill_analysis": "border-inkos-purple/40 text-inkos-purple-400",
  "prime.skill_evolution_applied": "border-inkos-cyan/40 text-inkos-cyan-400",
  "simulation.started": "border-amber-400/40 text-amber-400",
  "simulation.completed": "border-emerald-400/40 text-emerald-400",
  "simulation.timeout": "border-red-400/40 text-red-400",
  "simulation.failed": "border-red-400/40 text-red-400",
  "simulation.comparison": "border-inkos-cyan/40 text-inkos-cyan-400",
  "simulation.rolled_back": "border-amber-400/40 text-amber-400",
  "simulation.scenarios_generated": "border-inkos-purple/40 text-inkos-purple-400",
};

export default function TapePage() {
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState<string | null>(null);
  const { data: entries, isLoading } = useTapeEntries({ limit: 100 });

  const eventTypes = useMemo(() => {
    if (!entries) return [];
    const types = new Set(entries.map((e) => e.event_type));
    return Array.from(types).sort();
  }, [entries]);

  const filtered = useMemo(() => {
    if (!entries) return [];
    let result = entries;
    if (filterType) {
      result = result.filter((e) => e.event_type === filterType);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (e) =>
          e.event_type.toLowerCase().includes(q) ||
          (e.agent_id ?? "").toLowerCase().includes(q) ||
          JSON.stringify(e.payload).toLowerCase().includes(q),
      );
    }
    return result;
  }, [entries, filterType, search]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-3"
      >
        <ScrollText className="h-7 w-7 text-inkos-cyan" />
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-inkos-cyan text-glow-cyan">
            Tape Viewer
          </h1>
          <p className="text-sm text-muted-foreground">
            Immutable audit trail — {entries?.length ?? 0} events
          </p>
        </div>
      </motion.div>

      {/* Filters */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="flex flex-wrap items-center gap-3"
      >
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search events..."
            className="pl-9 bg-inkos-navy-800/50 border-inkos-purple/20 placeholder:text-muted-foreground/50"
          />
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <button
            onClick={() => setFilterType(null)}
            className={cn(
              "text-xs px-2.5 py-1 rounded-full border transition-all",
              !filterType
                ? "bg-inkos-purple/20 border-inkos-purple/40 text-inkos-purple-400"
                : "border-border text-muted-foreground hover:border-inkos-purple/30",
            )}
          >
            All
          </button>
          {eventTypes.map((type) => (
            <button
              key={type}
              onClick={() => setFilterType(filterType === type ? null : type)}
              className={cn(
                "text-xs px-2.5 py-1 rounded-full border transition-all truncate max-w-[180px]",
                filterType === type
                  ? "bg-inkos-purple/20 border-inkos-purple/40 text-inkos-purple-400"
                  : "border-border text-muted-foreground hover:border-inkos-purple/30",
              )}
            >
              {type}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Timeline */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
      >
        <Card className="glass border-inkos-purple/20">
          <CardContent className="p-0">
            {isLoading ? (
              <div className="space-y-3 p-6 animate-pulse">
                {Array.from({ length: 8 }).map((_, i) => (
                  <div
                    key={i}
                    className="h-12 rounded bg-muted/30"
                  />
                ))}
              </div>
            ) : filtered.length === 0 ? (
              <p className="py-12 text-center text-sm text-muted-foreground">
                {entries?.length === 0
                  ? "No Tape events yet. Start the backend to see activity."
                  : "No events match your search criteria."}
              </p>
            ) : (
              <ScrollArea className="max-h-[calc(100vh-320px)]">
                <div className="relative">
                  {/* Timeline line */}
                  <div className="absolute left-5 top-0 bottom-0 w-px bg-inkos-purple/20" />

                  <ul>
                    {filtered.map((entry, idx) => (
                      <li key={entry.id} className="relative pl-12 pr-4 py-3">
                        {/* Dot */}
                        <div
                          className={cn(
                            "absolute left-[14px] top-5 h-2.5 w-2.5 rounded-full border-2",
                            idx === 0
                              ? "bg-inkos-cyan border-inkos-cyan shadow-sm shadow-inkos-cyan/50"
                              : "bg-inkos-navy-900 border-inkos-purple/40",
                          )}
                        />

                        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                          <div className="flex items-center gap-2 min-w-0">
                            <Badge
                              variant="outline"
                              className={cn(
                                "shrink-0 text-[10px] font-mono",
                                EVENT_TYPE_COLOURS[entry.event_type] ??
                                  "border-border text-muted-foreground",
                              )}
                            >
                              {entry.event_type}
                            </Badge>
                            {entry.agent_id && (
                              <span className="text-xs text-muted-foreground truncate">
                                by {entry.agent_id}
                              </span>
                            )}
                          </div>
                          <span
                            className="text-[11px] text-muted-foreground tabular-nums shrink-0"
                            title={format(new Date(entry.timestamp), "PPpp")}
                          >
                            {formatDistanceToNow(new Date(entry.timestamp), {
                              addSuffix: true,
                            })}
                          </span>
                        </div>

                        {/* Payload preview */}
                        {Object.keys(entry.payload).length > 0 && (
                          <pre className="mt-1 text-[11px] text-muted-foreground/70 font-mono truncate">
                            {JSON.stringify(entry.payload).slice(0, 200)}
                            {JSON.stringify(entry.payload).length > 200 &&
                              "..."}
                          </pre>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              </ScrollArea>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
