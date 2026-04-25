"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  LayoutDashboard,
  MessageSquare,
  ScrollText,
  Vote,
  FlaskConical,
  Settings,
  ArrowRight,
  Network,
  Brain,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

const COMMANDS = [
  { id: "dashboard", label: "Go to Dashboard", icon: LayoutDashboard, href: "/" },
  { id: "prime", label: "Open Prime Console", icon: MessageSquare, href: "/prime" },
  { id: "tape", label: "View Tape", icon: ScrollText, href: "/tape" },
  { id: "proposals", label: "Manage Proposals", icon: Vote, href: "/proposals" },
  { id: "simulations", label: "Run Simulations", icon: FlaskConical, href: "/simulations" },
  { id: "canvas", label: "Open Domain Canvas", icon: Network, href: "/canvas" },
  { id: "profile", label: "View Intelligence Profile", icon: Brain, href: "/profile" },
  { id: "settings", label: "Settings", icon: Settings, action: "settings" },
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  const filtered = COMMANDS.filter((c) =>
    c.label.toLowerCase().includes(query.toLowerCase()),
  );

  // Keyboard shortcut: Cmd+K / Ctrl+K
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
      if (e.key === "Escape") {
        setOpen(false);
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Reset query/selection and focus input when the palette opens.
  // The resets are deferred via setTimeout to avoid synchronous setState
  // inside an effect body (which can cause cascading renders).
  useEffect(() => {
    if (open) {
      setTimeout(() => {
        setQuery("");
        setSelected(0);
        inputRef.current?.focus();
      }, 0);
    }
  }, [open]);

  // Navigate with arrow keys
  useEffect(() => {
    if (!open) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelected((s) => Math.min(s + 1, filtered.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelected((s) => Math.max(s - 1, 0));
      } else if (e.key === "Enter" && filtered[selected]) {
        executeCommand(filtered[selected]);
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, selected, filtered]); // eslint-disable-line react-hooks/exhaustive-deps

  function executeCommand(cmd: (typeof COMMANDS)[number]) {
    setOpen(false);
    if (cmd.href) {
      router.push(cmd.href);
    } else if (cmd.action === "settings") {
      window.dispatchEvent(new CustomEvent("open-settings"));
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] bg-black/50 backdrop-blur-sm"
            onClick={() => setOpen(false)}
          />

          {/* Palette */}
          <motion.div
            initial={{ opacity: 0, scale: 0.97, y: -8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: -8 }}
            transition={{ duration: 0.15, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="fixed left-1/2 top-[18%] z-[101] w-full max-w-lg -translate-x-1/2"
          >
            <div className="glass-strong rounded-2xl border border-inkos-cyan/12 overflow-hidden shadow-2xl glow-cyan">
              {/* Input */}
              <div className="flex items-center gap-3 px-4 py-3 border-b border-white/[0.04]">
                <Search className="h-5 w-5 text-muted-foreground shrink-0" />
                <input
                  ref={inputRef}
                  value={query}
                  onChange={(e) => {
                    setQuery(e.target.value);
                    setSelected(0);
                  }}
                  placeholder="Type a command or search..."
                  className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground/40 outline-none"
                />
                <kbd className="text-[10px] font-mono text-muted-foreground bg-inkos-navy-800/60 px-1.5 py-0.5 rounded border border-white/[0.06]">
                  ESC
                </kbd>
              </div>

              {/* Results */}
              <div className="max-h-64 overflow-y-auto p-2">
                {filtered.length === 0 ? (
                  <p className="py-6 text-center text-sm text-muted-foreground">
                    No commands found
                  </p>
                ) : (
                  filtered.map((cmd, idx) => (
                    <button
                      key={cmd.id}
                      onClick={() => executeCommand(cmd)}
                      onMouseEnter={() => setSelected(idx)}
                      className={cn(
                        "w-full flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors duration-150",
                        idx === selected
                          ? "bg-inkos-cyan/10 text-foreground"
                          : "text-muted-foreground hover:bg-white/[0.03]",
                      )}
                    >
                      <cmd.icon className="h-4 w-4 shrink-0" />
                      <span className="flex-1 text-left">{cmd.label}</span>
                      {idx === selected && (
                        <ArrowRight className="h-3.5 w-3.5 text-inkos-cyan" />
                      )}
                    </button>
                  ))
                )}
              </div>

              {/* Footer hint */}
              <div className="px-4 py-2 border-t border-white/[0.04] flex items-center gap-4 text-[10px] text-muted-foreground">
                <span>
                  <kbd className="font-mono bg-inkos-navy-800/60 px-1 py-0.5 rounded border border-white/[0.06]">
                    ↑↓
                  </kbd>{" "}
                  navigate
                </span>
                <span>
                  <kbd className="font-mono bg-inkos-navy-800/60 px-1 py-0.5 rounded border border-white/[0.06]">
                    ↵
                  </kbd>{" "}
                  select
                </span>
                <span>
                  <kbd className="font-mono bg-inkos-navy-800/60 px-1 py-0.5 rounded border border-white/[0.06]">
                    ⌘K
                  </kbd>{" "}
                  toggle
                </span>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
