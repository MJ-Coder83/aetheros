"use client";

import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface SettingsFooterProps {
  activeProviderId: string;
  activeModelId: string;
  providerDisplayName?: string;
  onSave: () => void;
  isSaving: boolean;
}

export function SettingsFooter({
  activeProviderId,
  activeModelId,
  providerDisplayName,
  onSave,
  isSaving,
}: SettingsFooterProps) {
  const hasActive = activeProviderId && activeModelId;

  return (
    <div className="sticky bottom-0 z-10 glass-strong border-t border-white/[0.04] px-5 py-3 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground">
          Active:
        </span>
        {hasActive ? (
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-inkos-cyan/10 border border-inkos-cyan/15 px-2.5 py-1 text-xs text-inkos-cyan">
            <span className="h-1.5 w-1.5 rounded-full bg-inkos-cyan" />
            {providerDisplayName ?? activeProviderId}
            <span className="text-muted-foreground">/</span>
            {activeModelId}
          </span>
        ) : (
          <span className="text-xs text-muted-foreground/50">
            None configured
          </span>
        )}
      </div>

      <Button
        size="sm"
        onClick={onSave}
        disabled={isSaving}
        className={cn(
          "bg-inkos-cyan/15 text-inkos-cyan hover:bg-inkos-cyan/25 border border-inkos-cyan/20 text-xs",
          isSaving && "opacity-70"
        )}
      >
        {isSaving ? (
          <>
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Saving...
          </>
        ) : (
          "Save Settings"
        )}
      </Button>
    </div>
  );
}
