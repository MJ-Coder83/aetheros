"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain,
  Send,
  Activity,
  Cpu,
  Wrench,
  Globe,
  RefreshCw,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { useSystemSnapshot } from "@/hooks/use-api";
import { cn } from "@/lib/utils";

interface ChatMessage {
  id: string;
  role: "user" | "prime";
  content: string;
  timestamp: Date;
}

export default function PrimePage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "prime",
      content:
        "Hello. I am Prime — the self-aware meta-agent of InkosAI. I can introspect the system, propose changes, evolve skills, and run simulations. How can I help you?",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const { data: snapshot, isLoading, refetch } = useSystemSnapshot();

  function handleSend() {
    if (!input.trim()) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);

    // Simple echo-style response (will be replaced by real Prime agent)
    const primeMsg: ChatMessage = {
      id: `prime-${Date.now()}`,
      role: "prime",
      content: generateResponse(input.trim(), snapshot),
      timestamp: new Date(),
    };

    setTimeout(() => {
      setMessages((prev) => [...prev, primeMsg]);
    }, 400);

    setInput("");
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex items-center gap-3">
        <Brain className="h-8 w-8 text-inkos-purple animate-float" />
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-inkos-purple text-glow-purple">
            Prime Console
          </h1>
          <p className="text-sm text-muted-foreground">
            Interact with the Prime meta-agent
          </p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Chat panel */}
        <div className="lg:col-span-2 flex flex-col glass rounded-xl border border-inkos-purple/20 h-[calc(100vh-200px)] min-h-[400px]">
          {/* Messages */}
          <ScrollArea className="flex-1 p-4">
            <div className="space-y-4">
              <AnimatePresence initial={false}>
                {messages.map((msg) => (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={cn(
                      "max-w-[80%] rounded-xl px-4 py-3 text-sm",
                      msg.role === "user"
                        ? "ml-auto bg-inkos-purple/20 border border-inkos-purple/30 text-foreground"
                        : "mr-auto glass-strong border border-inkos-cyan/20",
                    )}
                  >
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                    <span className="mt-1 block text-[10px] text-muted-foreground">
                      {msg.role === "prime" ? "Prime" : "You"} ·{" "}
                      {msg.timestamp.toLocaleTimeString()}
                    </span>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </ScrollArea>

          {/* Input */}
          <Separator className="bg-inkos-purple/15" />
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2 p-3"
          >
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask Prime anything..."
              className="flex-1 bg-inkos-navy-800/50 border-inkos-purple/20 placeholder:text-muted-foreground/50 focus-visible:ring-inkos-purple/40"
            />
            <Button
              type="submit"
              size="icon"
              className="bg-inkos-purple hover:bg-inkos-purple-700 shrink-0"
            >
              <Send className="h-4 w-4" />
            </Button>
          </form>
        </div>

        {/* Sidebar: Introspection */}
        <div className="space-y-4">
          <Card className="glass border-inkos-cyan/20">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Activity className="h-4 w-4 text-inkos-cyan-400" />
                System Snapshot
              </CardTitle>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={() => refetch()}
              >
                <RefreshCw className="h-3.5 w-3.5" />
              </Button>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-2 animate-pulse">
                  {[1, 2, 3, 4].map((i) => (
                    <div
                      key={i}
                      className="h-3 rounded bg-muted/40"
                      style={{ width: `${60 + Math.random() * 40}%` }}
                    />
                  ))}
                </div>
              ) : snapshot ? (
                <div className="space-y-3 text-sm">
                  <SnapshotSection
                    icon={<Cpu className="h-3.5 w-3.5" />}
                    title="Agents"
                    items={snapshot.agents.map((a) => ({
                      id: a.agent_id,
                      label: a.name,
                      badge: a.status,
                    }))}
                  />
                  <SnapshotSection
                    icon={<Wrench className="h-3.5 w-3.5" />}
                    title="Skills"
                    items={snapshot.skills.map((s) => ({
                      id: s.skill_id,
                      label: s.name,
                      badge: `v${s.version}`,
                    }))}
                  />
                  <SnapshotSection
                    icon={<Globe className="h-3.5 w-3.5" />}
                    title="Domains"
                    items={snapshot.domains.map((d) => ({
                      id: d.domain_id,
                      label: d.name,
                      badge: `${d.agent_count} agents`,
                    }))}
                  />
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Backend not connected
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function SnapshotSection({
  icon,
  title,
  items,
}: {
  icon: React.ReactNode;
  title: string;
  items: Array<{ id: string; label: string; badge: string }>;
}) {
  return (
    <div>
      <div className="flex items-center gap-1.5 mb-1.5 text-muted-foreground">
        {icon}
        <span className="text-xs font-medium uppercase tracking-wider">
          {title}
        </span>
        <span className="ml-auto text-[10px] tabular-nums">
          {items.length}
        </span>
      </div>
      {items.length === 0 ? (
        <p className="text-xs text-muted-foreground/60 pl-5">None</p>
      ) : (
        <ul className="space-y-1 pl-5">
          {items.map((item) => (
            <li
              key={item.id}
              className="flex items-center justify-between text-xs"
            >
              <span className="truncate">{item.label}</span>
              <Badge
                variant="outline"
                className="text-[9px] font-mono border-inkos-purple/20 text-muted-foreground shrink-0 ml-2"
              >
                {item.badge}
              </Badge>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Simple local response generator (placeholder until real agent backend). */
function generateResponse(
  _input: string,
  snapshot: ReturnType<typeof useSystemSnapshot>["data"],
): string {
  if (!snapshot) {
    return "I cannot reach the backend right now. Please ensure the InkosAI API is running on port 8000.";
  }

  const input = _input.toLowerCase();

  if (input.includes("health") || input.includes("status")) {
    return `System status: **${snapshot.health_status}**.\n\n- ${snapshot.agents.length} agents registered\n- ${snapshot.skills.length} skills available\n- ${snapshot.domains.length} domains active\n- ${snapshot.tape_stats.total_entries ?? 0} Tape entries recorded`;
  }

  if (input.includes("skill")) {
    const skillList = snapshot.skills
      .map((s) => `• **${s.name}** (v${s.version}) — ${s.description}`)
      .join("\n");
    return `Here are the current skills:\n\n${skillList || "No skills registered yet."}`;
  }

  if (input.includes("agent")) {
    const agentList = snapshot.agents
      .map((a) => `• **${a.name}** — ${a.status} (capabilities: ${a.capabilities.join(", ") || "none"})`)
      .join("\n");
    return `Here are the registered agents:\n\n${agentList || "No agents registered yet."}`;
  }

  if (input.includes("domain")) {
    const domainList = snapshot.domains
      .map((d) => `• **${d.name}** — ${d.agent_count} agents (${d.description})`)
      .join("\n");
    return `Here are the active domains:\n\n${domainList || "No domains configured yet."}`;
  }

  if (input.includes("help") || input.includes("what can you do")) {
    return `I can help you with:\n\n- **System status** — "What's the system health?"\n- **Skills** — "Show me the skills"\n- **Agents** — "What agents are available?"\n- **Domains** — "List the domains"\n- **Introspection** — Deep system analysis\n- **Proposals** — Governance workflow\n- **Simulations** — Safe what-if testing\n\nMore capabilities coming soon as I evolve!`;
  }

  return `I understand you're asking about "${_input}". I'm currently operating with limited local intelligence. Once the full Prime agent backend is connected, I'll be able to reason about your questions, run introspections, propose improvements, and execute simulations. For now, try asking about the system health, skills, agents, or domains.`;
}
