"use client";

import { useState, useEffect } from "react";
import {
  Settings as SettingsIcon,
  X,
  Server,
  RefreshCw,
  Keyboard,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";

const SHORTCUTS = [
  { keys: "⌘/Ctrl + K", action: "Open command palette" },
  { keys: "⌘/Ctrl + Shift + P", action: "Open Prime Console" },
  { keys: "?", action: "Show keyboard shortcuts" },
  { keys: "Esc", action: "Close dialog / palette" },
];

export function SettingsDialog() {
  const [open, setOpen] = useState(false);
  const [apiUrl, setApiUrl] = useState(
    process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  );
  const [refreshTape, setRefreshTape] = useState("10");
  const [refreshSnapshot, setRefreshSnapshot] = useState("30");

  // Listen for custom event from command palette
  useEffect(() => {
    function handleOpenSettings() {
      setOpen(true);
    }
    window.addEventListener("open-settings", handleOpenSettings);
    return () => window.removeEventListener("open-settings", handleOpenSettings);
  }, []);

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[90] bg-black/60 backdrop-blur-sm"
            onClick={() => setOpen(false)}
          />

          {/* Dialog */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="fixed left-1/2 top-1/2 z-[91] w-full max-w-md -translate-x-1/2 -translate-y-1/2"
          >
            <div className="glass-strong rounded-2xl border border-inkos-purple/30 overflow-hidden shadow-2xl">
              {/* Header */}
              <div className="flex items-center justify-between px-5 py-4 border-b border-inkos-purple/15">
                <div className="flex items-center gap-2.5">
                  <SettingsIcon className="h-5 w-5 text-inkos-purple-400" />
                  <h2 className="text-base font-semibold">Settings</h2>
                </div>
                <button
                  onClick={() => setOpen(false)}
                  className="h-7 w-7 rounded-md flex items-center justify-center hover:bg-inkos-purple/10 transition-colors"
                >
                  <X className="h-4 w-4 text-muted-foreground" />
                </button>
              </div>

              <div className="p-5 space-y-5">
                {/* Connection */}
                <section>
                  <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-1.5">
                    <Server className="h-3.5 w-3.5" /> Connection
                  </h3>
                  <div className="space-y-2">
                    <label className="text-xs text-muted-foreground">
                      Backend API URL
                    </label>
                    <Input
                      value={apiUrl}
                      onChange={(e) => setApiUrl(e.target.value)}
                      className="bg-inkos-navy-800/50 border-inkos-purple/20 text-sm font-mono"
                    />
                    <p className="text-[10px] text-muted-foreground/60">
                      Changes take effect after page reload. Current:{" "}
                      {process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}
                    </p>
                  </div>
                </section>

                <Separator className="bg-inkos-purple/15" />

                {/* Refresh intervals */}
                <section>
                  <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-1.5">
                    <RefreshCw className="h-3.5 w-3.5" /> Refresh Intervals
                  </h3>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs text-muted-foreground">
                        Tape (seconds)
                      </label>
                      <Input
                        type="number"
                        value={refreshTape}
                        onChange={(e) => setRefreshTape(e.target.value)}
                        className="bg-inkos-navy-800/50 border-inkos-purple/20 text-sm"
                        min={1}
                      />
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground">
                        Snapshot (seconds)
                      </label>
                      <Input
                        type="number"
                        value={refreshSnapshot}
                        onChange={(e) => setRefreshSnapshot(e.target.value)}
                        className="bg-inkos-navy-800/50 border-inkos-purple/20 text-sm"
                        min={1}
                      />
                    </div>
                  </div>
                </section>

                <Separator className="bg-inkos-purple/15" />

                {/* Keyboard shortcuts */}
                <section>
                  <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-1.5">
                    <Keyboard className="h-3.5 w-3.5" /> Keyboard Shortcuts
                  </h3>
                  <div className="space-y-2">
                    {SHORTCUTS.map((s) => (
                      <div
                        key={s.keys}
                        className="flex items-center justify-between text-xs"
                      >
                        <span className="text-muted-foreground">
                          {s.action}
                        </span>
                        <kbd className="font-mono text-[10px] bg-inkos-navy-800/60 px-2 py-1 rounded border border-inkos-purple/20 text-inkos-purple-400">
                          {s.keys}
                        </kbd>
                      </div>
                    ))}
                  </div>
                </section>
              </div>

              {/* Footer */}
              <div className="px-5 py-3 border-t border-inkos-purple/15 flex items-center justify-between">
                <p className="text-[10px] text-muted-foreground">
                  InkosAI v0.1.0
                </p>
                <Button
                  size="sm"
                  className="bg-inkos-purple hover:bg-inkos-purple-700 text-xs"
                  onClick={() => setOpen(false)}
                >
                  Done
                </Button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
