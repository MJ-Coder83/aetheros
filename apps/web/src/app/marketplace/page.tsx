"use client";

import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Store,
  Search,
  Download,
  Trash2,
  Star,
  Shield,
  CheckCircle2,
  XCircle,
  ExternalLink,
  ChevronDown,
  Plug,
  Loader2,
  AlertTriangle,
  Package,
  ToggleLeft,
  ToggleRight,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { SkeletonList, EmptyState } from "@/components/skeleton";
import {
  useMarketplacePlugins,
  useInstalledPlugins,
  useInstallPlugin,
  useUninstallPlugin,
} from "@/hooks/use-api";
import type { MarketplacePlugin, InstalledPlugin, PluginPermission } from "@/types";
import { cn } from "@/lib/utils";

const DEFAULT_USER_ID = "human-user";

const CATEGORIES = [
  "All",
  "Productivity",
  "Analytics",
  "Integration",
  "Automation",
  "Visualization",
  "Communication",
  "Security",
  "Development",
  "Education",
] as const;

const SORT_OPTIONS = [
  { value: "downloads", label: "Most Downloads" },
  { value: "rating", label: "Highest Rated" },
  { value: "newest", label: "Newest" },
  { value: "name", label: "Alphabetical" },
] as const;

const PERMISSION_LABELS: Record<PluginPermission, { label: string; risk: "low" | "medium" | "high" }> = {
  folder_tree_read: { label: "Read Folder Tree", risk: "low" },
  folder_tree_write: { label: "Write Folder Tree", risk: "high" },
  tape_read: { label: "Read Tape", risk: "low" },
  tape_write: { label: "Write Tape", risk: "medium" },
  agent_communicate: { label: "Communicate with Agents", risk: "medium" },
  canvas_read: { label: "Read Canvas", risk: "low" },
  canvas_write: { label: "Write Canvas", risk: "high" },
  domain_read: { label: "Read Domain Data", risk: "low" },
  network_access: { label: "Network Access", risk: "high" },
  system_config: { label: "System Configuration", risk: "high" },
};

const PERMISSION_RISK_COLORS = {
  low: "text-emerald-400 border-emerald-500/15",
  medium: "text-amber-400 border-amber-400/15",
  high: "text-red-400 border-red-400/15",
};

function renderStars(rating: number, count: number) {
  return (
    <div className="flex items-center gap-1">
      <div className="flex items-center">
        {Array.from({ length: 5 }).map((_, i) => (
          <Star
            key={i}
            className={cn(
              "h-3 w-3",
              i < Math.round(rating)
                ? "text-amber-400 fill-amber-400"
                : "text-white/10",
            )}
          />
        ))}
      </div>
      <span className="text-[10px] text-muted-foreground tabular-nums">
        {rating.toFixed(1)} ({count})
      </span>
    </div>
  );
}

export default function MarketplacePage() {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<string>("All");
  const [sortBy, setSortBy] = useState<"downloads" | "rating" | "newest" | "name">("downloads");
  const [installDialogPlugin, setInstallDialogPlugin] = useState<MarketplacePlugin | null>(null);
  const [grantedPermissions, setGrantedPermissions] = useState<PluginPermission[]>([]);
  const [uninstallDialogPlugin, setUninstallDialogPlugin] = useState<InstalledPlugin | null>(null);
  const [activeTab, setActiveTab] = useState("browse");

  const { data: plugins, isLoading: pluginsLoading } = useMarketplacePlugins({
    query: search || undefined,
    category: category !== "All" ? category : undefined,
    sort_by: sortBy,
  });

  const { data: installedPlugins, isLoading: installedLoading } = useInstalledPlugins();
  const installMutation = useInstallPlugin();
  const uninstallMutation = useUninstallPlugin();

  const installedIds = useMemo(
    () => new Set(installedPlugins?.map((p) => p.manifest.id) ?? []),
    [installedPlugins],
  );

  function openInstallDialog(plugin: MarketplacePlugin) {
    setGrantedPermissions([...plugin.manifest.permissions]);
    setInstallDialogPlugin(plugin);
  }

  function handleInstall() {
    if (!installDialogPlugin) return;
    installMutation.mutate(
      {
        pluginId: installDialogPlugin.id,
        version: installDialogPlugin.manifest.version,
        grantedPermissions,
        userId: DEFAULT_USER_ID,
      },
      {
        onSettled: () => setInstallDialogPlugin(null),
      },
    );
  }

  function handleUninstall() {
    if (!uninstallDialogPlugin) return;
    uninstallMutation.mutate(uninstallDialogPlugin.manifest.id, {
      onSettled: () => setUninstallDialogPlugin(null),
    });
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 space-y-6 page-transition">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="flex items-center gap-3"
      >
        <div className="h-9 w-9 rounded-lg bg-inkos-cyan/8 border border-inkos-cyan/15 flex items-center justify-center">
          <Store className="h-5 w-5 text-inkos-cyan" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            <span className="text-inkos-cyan">Plugin</span> Marketplace
          </h1>
          <p className="text-sm text-muted-foreground">
            Discover, install, and manage plugins for your InkosAI system
          </p>
        </div>
      </motion.div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-white/[0.02] border border-white/[0.06]">
          <TabsTrigger value="browse" className="data-[state=active]:bg-inkos-cyan/10 data-[state=active]:text-inkos-cyan">
            <Store className="h-3.5 w-3.5 mr-1.5" />
            Browse
          </TabsTrigger>
          <TabsTrigger value="installed" className="data-[state=active]:bg-inkos-cyan/10 data-[state=active]:text-inkos-cyan">
            <Package className="h-3.5 w-3.5 mr-1.5" />
            Installed
            {installedPlugins && installedPlugins.length > 0 && (
              <Badge variant="secondary" className="ml-1.5 text-[9px] h-4 min-w-[16px] px-1">
                {installedPlugins.length}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="browse" className="space-y-4 mt-4">
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.08, duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="space-y-3"
          >
            <div className="flex flex-wrap items-center gap-3">
              <div className="relative flex-1 min-w-[200px] max-w-sm">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search plugins..."
                  className="pl-9 bg-white/[0.02] border-white/[0.06] placeholder:text-muted-foreground/40 focus-visible:border-inkos-cyan/25 focus-visible:ring-inkos-cyan/15"
                />
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                {CATEGORIES.map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setCategory(cat)}
                    className={cn(
                      "text-xs px-2.5 py-1 rounded-full border transition-all duration-200",
                      category === cat
                        ? "bg-inkos-cyan/10 border-inkos-cyan/25 text-inkos-cyan"
                        : "border-white/[0.06] text-muted-foreground hover:border-inkos-cyan/20",
                    )}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Sort:</span>
              {SORT_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setSortBy(opt.value)}
                  className={cn(
                    "text-xs px-2 py-0.5 rounded border transition-all duration-200",
                    sortBy === opt.value
                      ? "bg-inkos-cyan/10 border-inkos-cyan/25 text-inkos-cyan"
                      : "border-white/[0.06] text-muted-foreground hover:border-inkos-cyan/20",
                  )}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.12, duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
          >
            {pluginsLoading ? (
              <div className="p-6">
                <SkeletonList rows={6} />
              </div>
            ) : !plugins || plugins.length === 0 ? (
              <EmptyState
                icon={Store}
                title="No plugins found"
                description={
                  search || category !== "All"
                    ? "Try adjusting your search or category filter."
                    : "The marketplace is empty. Check back soon for new plugins!"
                }
              />
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {plugins.map((plugin) => (
                  <PluginCard
                    key={plugin.id}
                    plugin={plugin}
                    isInstalled={installedIds.has(plugin.id)}
                    onInstall={() => openInstallDialog(plugin)}
                    onUninstall={() => {
                      const installed = installedPlugins?.find(
                        (ip) => ip.manifest.id === plugin.id,
                      );
                      if (installed) setUninstallDialogPlugin(installed);
                    }}
                  />
                ))}
              </div>
            )}
          </motion.div>
        </TabsContent>

        <TabsContent value="installed" className="space-y-4 mt-4">
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
          >
            {installedLoading ? (
              <div className="p-6">
                <SkeletonList rows={4} />
              </div>
            ) : !installedPlugins || installedPlugins.length === 0 ? (
              <EmptyState
                icon={Package}
                title="No plugins installed"
                description="Browse the marketplace to discover and install plugins for your system."
              />
            ) : (
              <div className="space-y-3">
                {installedPlugins.map((ip) => (
                  <Card key={ip.id} className="glass glass-hover border-inkos-cyan/8">
                    <CardContent className="flex items-center gap-4 py-4">
                      <div className="h-10 w-10 rounded-lg bg-inkos-cyan/8 border border-inkos-cyan/15 flex items-center justify-center shrink-0">
                        <Plug className="h-5 w-5 text-inkos-cyan" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-sm truncate">
                            {ip.manifest.name}
                          </span>
                          <Badge variant="outline" className="text-[9px] font-mono shrink-0 border-white/[0.06]">
                            v{ip.manifest.version}
                          </Badge>
                          <Badge
                            variant="outline"
                            className={cn(
                              "text-[9px] shrink-0",
                              ip.enabled
                                ? "text-emerald-400 border-emerald-500/15"
                                : "text-muted-foreground border-white/[0.06]",
                            )}
                          >
                            {ip.enabled ? "Enabled" : "Disabled"}
                          </Badge>
                          {ip.status === "error" && (
                            <Badge variant="destructive" className="text-[9px] shrink-0">
                              Error
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground mt-0.5 truncate">
                          {ip.manifest.description}
                        </p>
                        <div className="flex items-center gap-3 mt-1">
                          <span className="text-[10px] text-muted-foreground/60">
                            by {ip.manifest.author}
                          </span>
                          <span className="text-[10px] text-muted-foreground/60">
                            Installed {new Date(ip.installed_at).toLocaleDateString()}
                          </span>
                        </div>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        className="shrink-0 border-red-400/20 text-red-400 hover:bg-red-400/10 hover:text-red-400 hover:border-red-400/30"
                        onClick={() => setUninstallDialogPlugin(ip)}
                      >
                        <Trash2 className="h-3.5 w-3.5 mr-1" />
                        Uninstall
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </motion.div>
        </TabsContent>
      </Tabs>

      {/* Install Permission Dialog */}
      <AnimatePresence>
        {installDialogPlugin && (
          <Dialog open={true} onOpenChange={(open) => !open && setInstallDialogPlugin(null)}>
            <DialogContent className="glass-strong border-inkos-cyan/12 max-w-md">
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5 text-inkos-cyan" />
                  Install {installDialogPlugin.manifest.name}
                </DialogTitle>
                <DialogDescription className="text-sm text-muted-foreground">
                  This plugin requires the following permissions. Review each permission and toggle on/off before installing.
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-3 py-2">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
                  <span>High-risk permissions are highlighted in red</span>
                </div>
                <Separator className="bg-white/[0.04]" />

                {installDialogPlugin.manifest.permissions.map((perm) => {
                  const info = PERMISSION_LABELS[perm];
                  const isGranted = grantedPermissions.includes(perm);
                  return (
                    <div
                      key={perm}
                      className={cn(
                        "flex items-center justify-between rounded-lg px-3 py-2.5 border transition-colors duration-200",
                        isGranted
                          ? "bg-white/[0.02] border-white/[0.06]"
                          : "bg-transparent border-white/[0.03] opacity-50",
                      )}
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-[9px] shrink-0",
                            PERMISSION_RISK_COLORS[info.risk],
                          )}
                        >
                          {info.risk}
                        </Badge>
                        <span className="text-sm truncate">{info.label}</span>
                      </div>
                      <button
                        onClick={() => {
                          setGrantedPermissions((prev) =>
                            isGranted
                              ? prev.filter((p) => p !== perm)
                              : [...prev, perm],
                          );
                        }}
                        className="shrink-0 ml-2"
                      >
                        {isGranted ? (
                          <ToggleRight className="h-5 w-5 text-inkos-cyan" />
                        ) : (
                          <ToggleLeft className="h-5 w-5 text-muted-foreground" />
                        )}
                      </button>
                    </div>
                  );
                })}
              </div>

              <div className="text-xs text-muted-foreground pt-1">
                v{installDialogPlugin.manifest.version} · by {installDialogPlugin.manifest.author}
              </div>

              <DialogFooter className="gap-2">
                <Button
                  variant="outline"
                  onClick={() => setInstallDialogPlugin(null)}
                  className="border-white/[0.06]"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleInstall}
                  disabled={grantedPermissions.length === 0 || installMutation.isPending}
                  className="bg-inkos-cyan/15 text-inkos-cyan hover:bg-inkos-cyan/25 border border-inkos-cyan/20"
                >
                  {installMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-1.5" />
                  ) : (
                    <Download className="h-4 w-4 mr-1.5" />
                  )}
                  Install with {grantedPermissions.length} permission{grantedPermissions.length !== 1 ? "s" : ""}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </AnimatePresence>

      {/* Uninstall Confirmation Dialog */}
      <AnimatePresence>
        {uninstallDialogPlugin && (
          <Dialog open={true} onOpenChange={(open) => !open && setUninstallDialogPlugin(null)}>
            <DialogContent className="glass-strong border-inkos-cyan/12 max-w-sm">
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <Trash2 className="h-5 w-5 text-red-400" />
                  Uninstall Plugin
                </DialogTitle>
                <DialogDescription className="text-sm text-muted-foreground">
                  Are you sure you want to uninstall <strong>{uninstallDialogPlugin.manifest.name}</strong>?
                  This will remove the plugin and all its permissions from your system.
                </DialogDescription>
              </DialogHeader>

              <DialogFooter className="gap-2">
                <Button
                  variant="outline"
                  onClick={() => setUninstallDialogPlugin(null)}
                  className="border-white/[0.06]"
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleUninstall}
                  disabled={uninstallMutation.isPending}
                >
                  {uninstallMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-1.5" />
                  ) : (
                    <Trash2 className="h-4 w-4 mr-1.5" />
                  )}
                  Uninstall
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </AnimatePresence>
    </div>
  );
}

function PluginCard({
  plugin,
  isInstalled,
  onInstall,
  onUninstall,
}: {
  plugin: MarketplacePlugin;
  isInstalled: boolean;
  onInstall: () => void;
  onUninstall: () => void;
}) {
  const highRiskPerms = plugin.manifest.permissions.filter(
    (p) => PERMISSION_LABELS[p]?.risk === "high",
  );

  return (
    <Card className="glass glass-hover border-inkos-cyan/8 flex flex-col">
      <CardHeader className="pb-2">
        <div className="flex items-start gap-3">
          <div className="h-10 w-10 rounded-lg bg-inkos-cyan/8 border border-inkos-cyan/15 flex items-center justify-center shrink-0">
            {plugin.manifest.icon ? (
              <span className="text-lg">{plugin.manifest.icon}</span>
            ) : (
              <Plug className="h-5 w-5 text-inkos-cyan" />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <span className="truncate">{plugin.manifest.name}</span>
              {plugin.verified && (
                <CheckCircle2 className="h-3.5 w-3.5 text-inkos-cyan shrink-0" />
              )}
              {plugin.featured && (
                <Badge className="text-[8px] h-4 px-1 bg-amber-400/10 text-amber-400 border-amber-400/15">
                  Featured
                </Badge>
              )}
            </CardTitle>
            <CardDescription className="text-xs mt-0.5">
              by {plugin.manifest.author} · v{plugin.manifest.version}
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex-1 pb-2">
        <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
          {plugin.manifest.description}
        </p>

        <div className="mt-2">
          {renderStars(plugin.rating_avg, plugin.rating_count)}
        </div>

        <div className="mt-2 flex flex-wrap gap-1">
          <Badge variant="outline" className="text-[9px] border-white/[0.06] text-muted-foreground">
            {plugin.downloads.toLocaleString()} downloads
          </Badge>
          <Badge variant="outline" className="text-[9px] border-white/[0.06] text-muted-foreground">
            {plugin.manifest.category}
          </Badge>
          {highRiskPerms.length > 0 && (
            <Badge variant="outline" className="text-[9px] text-amber-400 border-amber-400/15">
              <AlertTriangle className="h-2.5 w-2.5 mr-0.5" />
              {highRiskPerms.length} high-risk
            </Badge>
          )}
        </div>
      </CardContent>
      <CardFooter className="pt-0">
        {isInstalled ? (
          <Button
            variant="outline"
            size="sm"
            className="w-full border-red-400/20 text-red-400 hover:bg-red-400/10 hover:text-red-400 hover:border-red-400/30"
            onClick={onUninstall}
          >
            <Trash2 className="h-3.5 w-3.5 mr-1.5" />
            Uninstall
          </Button>
        ) : (
          <Button
            size="sm"
            className="w-full bg-inkos-cyan/15 text-inkos-cyan hover:bg-inkos-cyan/25 border border-inkos-cyan/20"
            onClick={onInstall}
          >
            <Download className="h-3.5 w-3.5 mr-1.5" />
            Install
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
