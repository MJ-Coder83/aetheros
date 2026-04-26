"use client";

import { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Settings2 } from "lucide-react";
import { useProviders, useSettings, useSaveSettings, useTestConnection } from "@/hooks/use-api";
import type { ConnectionTestResult } from "@/types";
import { ProviderCard } from "@/components/provider-card";
import { ProviderDetail } from "@/components/provider-detail";
import { SettingsFooter } from "@/components/settings-footer";

const STAGGER = {
  container: { transition: { staggerChildren: 0.04 } },
  item: {
    initial: { opacity: 0, y: 8 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.15, ease: [0.25, 0.46, 0.45, 0.94] as const },
  },
};

export default function SettingsPage() {
  const { data: providersData, isLoading: providersLoading } = useProviders();
  const { data: settings } = useSettings();
  const saveSettings = useSaveSettings();
  const testConnection = useTestConnection();

  const providers = providersData?.providers ?? [];

  const [selectedProviderId, setSelectedProviderId] = useState<string | null>(
    settings?.active_provider_id ?? null
  );
  const [pendingKeys, setPendingKeys] = useState<Record<string, string>>({});
  const [pendingModels, setPendingModels] = useState<Record<string, string>>({});
  const [testResults, setTestResults] = useState<Record<string, ConnectionTestResult | null>>({});

  const selectedProvider = providers.find((p) => p.provider_id === selectedProviderId) ?? null;

  const activeProviderId = settings?.active_provider_id ?? "";
  const activeModelId = settings?.active_model_id ?? "";
  const activeProvider = providers.find((p) => p.provider_id === activeProviderId);

  const handleSaveKey = useCallback((key: string) => {
    if (!selectedProviderId) return;
    setPendingKeys((prev) => ({ ...prev, [selectedProviderId]: key }));
  }, [selectedProviderId]);

  const handleSelectModel = useCallback((model: string) => {
    if (!selectedProviderId) return;
    setPendingModels((prev) => ({ ...prev, [selectedProviderId]: model }));
  }, [selectedProviderId]);

  const handleTestConnection = useCallback((apiKey: string) => {
    if (!selectedProviderId) return;
    setTestResults((prev) => ({ ...prev, [selectedProviderId]: null }));
    testConnection.mutate(
      { providerId: selectedProviderId, apiKey },
      {
        onSuccess: (result) => {
          setTestResults((prev) => ({ ...prev, [selectedProviderId]: result }));
        },
      }
    );
  }, [selectedProviderId, testConnection]);

  const handleSave = useCallback(() => {
    const data: Parameters<typeof saveSettings.mutate>[0] = {};

    if (Object.keys(pendingKeys).length > 0) {
      data.provider_keys = pendingKeys;
    }
    if (Object.keys(pendingModels).length > 0) {
      data.default_models = pendingModels;
    }

    const newActiveProviderId = selectedProviderId ?? activeProviderId;
    const newActiveModelId =
      (selectedProviderId ? pendingModels[selectedProviderId] : undefined) ??
      activeModelId;

    if (newActiveProviderId) {
      data.active_provider_id = newActiveProviderId;
    }
    if (newActiveModelId) {
      data.active_model_id = newActiveModelId;
    }

    saveSettings.mutate(data, {
      onSuccess: () => {
        setPendingKeys({});
        setPendingModels({});
      },
    });
  }, [pendingKeys, pendingModels, selectedProviderId, activeProviderId, activeModelId, saveSettings]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 min-h-0 overflow-y-auto">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 py-8">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, ease: [0.25, 0.46, 0.45, 0.94] }}
          >
            <div className="flex items-center gap-2.5 mb-1">
              <Settings2 className="h-5 w-5 text-inkos-cyan" />
              <h1 className="text-xl font-semibold">Provider Settings</h1>
            </div>
            <p className="text-sm text-muted-foreground mb-8">
              Configure AI providers, manage API keys, and select default models.
            </p>
          </motion.div>

          {providersLoading ? (
            <div className="flex items-center justify-center py-20">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-inkos-cyan/30 border-t-inkos-cyan" />
            </div>
          ) : providers.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
              <Settings2 className="h-10 w-10 mb-3 opacity-30" />
              <p className="text-sm">No providers available</p>
              <p className="text-xs text-muted-foreground/50 mt-1">
                Start the backend to load provider configurations.
              </p>
            </div>
          ) : (
            <div className="flex flex-col lg:flex-row gap-6">
              <motion.div
                variants={STAGGER.container}
                initial="initial"
                animate="animate"
                className="flex-1 min-w-0"
              >
                <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
                  {providers.map((provider) => (
                    <motion.div key={provider.provider_id} variants={STAGGER.item}>
                      <ProviderCard
                        provider={provider}
                        isActive={provider.provider_id === selectedProviderId}
                        onClick={() => setSelectedProviderId(provider.provider_id)}
                      />
                    </motion.div>
                  ))}
                </div>
              </motion.div>

              <div className="lg:w-[380px] shrink-0">
                {selectedProvider ? (
                  <ProviderDetail
                    provider={selectedProvider}
                    settings={settings}
                    onSaveKey={handleSaveKey}
                    onSelectModel={handleSelectModel}
                    onTestConnection={handleTestConnection}
                    isTesting={
                      testConnection.isPending &&
                      testConnection.variables?.providerId === selectedProviderId
                    }
                    testResult={testResults[selectedProviderId] ?? null}
                  />
                ) : (
                  <div className="rounded-xl border border-white/[0.04] bg-white/[0.02] p-8 flex flex-col items-center justify-center text-center">
                    <Settings2 className="h-8 w-8 text-muted-foreground/20 mb-3" />
                    <p className="text-sm text-muted-foreground/60">
                      Select a provider to configure
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      <SettingsFooter
        activeProviderId={activeProviderId}
        activeModelId={activeModelId}
        providerDisplayName={activeProvider?.display_name}
        onSave={handleSave}
        isSaving={saveSettings.isPending}
      />
    </div>
  );
}
