"use client";

import { useState } from "react";
import { Eye, EyeOff, Loader2, CheckCircle2, XCircle, Globe } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import type { ProviderInfo, Settings, ConnectionTestResult } from "@/types";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

interface ProviderDetailProps {
  provider: ProviderInfo;
  settings: Settings | undefined;
  onSaveKey: (key: string) => void;
  onSelectModel: (model: string) => void;
  onTestConnection: (key: string) => void;
  isTesting: boolean;
  testResult: ConnectionTestResult | null;
}

export function ProviderDetail({
  provider,
  settings,
  onSaveKey,
  onSelectModel,
  onTestConnection,
  isTesting,
  testResult,
}: ProviderDetailProps) {
  const [apiKey, setApiKey] = useState(settings?.provider_keys?.[provider.provider_id] ?? "");
  const [showKey, setShowKey] = useState(false);
  const currentModel =
    settings?.default_models?.[provider.provider_id] ?? provider.selected_model ?? "";

  const handleKeyChange = (value: string) => {
    setApiKey(value);
    onSaveKey(value);
  };

  const handleModelChange = (model: string) => {
    onSelectModel(model);
  };

  return (
    <motion.div
      key={provider.provider_id}
      initial={{ opacity: 0, x: 8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.15, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="rounded-xl border border-white/[0.04] bg-white/[0.02] overflow-hidden"
    >
      <div className="px-5 py-4 border-b border-white/[0.04]">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-inkos-cyan/10 text-inkos-cyan text-sm font-bold">
            {provider.display_name.charAt(0).toUpperCase()}
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="text-sm font-semibold truncate">
              {provider.display_name}
            </h3>
            <div className="flex items-center gap-1.5 mt-0.5">
              <Globe className="h-3 w-3 text-muted-foreground/50" />
              <span className="text-[11px] text-muted-foreground/50 truncate font-mono">
                {provider.base_url}
              </span>
            </div>
          </div>
          <span
            className={cn(
              "h-2 w-2 rounded-full",
              provider.has_key_configured ? "bg-emerald-400" : "bg-muted-foreground/30"
            )}
          />
        </div>
      </div>

      <div className="p-5 space-y-5">
        <div>
          <label className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground mb-2 block">
            API Key
          </label>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Input
                type={showKey ? "text" : "password"}
                value={apiKey}
                onChange={(e) => handleKeyChange(e.target.value)}
                placeholder="sk-..."
                className="bg-white/[0.02] border-white/[0.06] text-sm font-mono pr-9 focus-visible:border-inkos-cyan/30 focus-visible:ring-inkos-cyan/20"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground/50 hover:text-muted-foreground transition-colors"
              >
                {showKey ? (
                  <EyeOff className="h-3.5 w-3.5" />
                ) : (
                  <Eye className="h-3.5 w-3.5" />
                )}
              </button>
            </div>
            <Button
              size="sm"
              onClick={() => onTestConnection(apiKey)}
              disabled={!apiKey.trim() || isTesting}
              className="bg-inkos-cyan/15 text-inkos-cyan hover:bg-inkos-cyan/25 border border-inkos-cyan/20 text-xs shrink-0"
            >
              {isTesting ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                "Test"
              )}
            </Button>
          </div>

          <AnimatePresence>
            {testResult && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.15 }}
                className="overflow-hidden"
              >
                <div
                  className={cn(
                    "mt-2 flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs",
                    testResult.success
                      ? "bg-emerald-500/10 text-emerald-400"
                      : "bg-red-500/10 text-red-400"
                  )}
                >
                  {testResult.success ? (
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
                  ) : (
                    <XCircle className="h-3.5 w-3.5 shrink-0" />
                  )}
                  <span>
                    {testResult.success
                      ? `Connected — ${testResult.model_count ?? 0} models available`
                      : testResult.message}
                  </span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <Separator className="bg-white/[0.04]" />

        <div>
          <label className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground mb-2 block">
            Default Model
          </label>
          <select
            value={currentModel}
            onChange={(e) => handleModelChange(e.target.value)}
            className="w-full h-8 rounded-lg border border-white/[0.06] bg-white/[0.02] px-2.5 text-sm text-foreground outline-none focus:border-inkos-cyan/30 focus:ring-2 focus:ring-inkos-cyan/20 transition-colors appearance-none cursor-pointer"
          >
            {!currentModel && (
              <option value="" className="bg-inkos-navy-900">
                Select a model...
              </option>
            )}
            {provider.models.map((model) => (
              <option key={model} value={model} className="bg-inkos-navy-900">
                {model}
              </option>
            ))}
          </select>
          {provider.models.length === 0 && (
            <p className="mt-1.5 text-[10px] text-muted-foreground/50">
              Configure an API key and test connection to load available models.
            </p>
          )}
        </div>
      </div>
    </motion.div>
  );
}
