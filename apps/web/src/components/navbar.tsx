"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Brain,
  ScrollText,
  Vote,
  FlaskConical,
  LayoutDashboard,
  MessageSquare,
  Settings,
  Settings2,
  Search,
  Lightbulb,
  Layers,
  Route,
  ArrowRightLeft,
  Network,
  Store,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useSettings, useProviders } from "@/hooks/use-api";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/prime", label: "Prime", icon: MessageSquare },
  { href: "/tape", label: "Tape", icon: ScrollText },
  { href: "/proposals", label: "Proposals", icon: Vote },
  { href: "/simulations", label: "Simulations", icon: FlaskConical },
  { href: "/explain", label: "Explain", icon: Lightbulb },
  { href: "/planning", label: "Planning", icon: Route },
  { href: "/canvas", label: "Canvas", icon: Network },
  { href: "/profile", label: "Profile", icon: Brain },
  { href: "/knowledge", label: "Knowledge", icon: ArrowRightLeft },
  { href: "/domains", label: "Domains", icon: Layers },
  { href: "/marketplace", label: "Marketplace", icon: Store },
  { href: "/settings", label: "Settings", icon: Settings2 },
];

export function Navbar() {
  const pathname = usePathname();
  const { data: settings } = useSettings();
  const { data: providersData } = useProviders();

  const activeProvider = providersData?.providers.find(
    (p) => p.provider_id === settings?.active_provider_id
  );

  return (
    <header className="sticky top-0 z-50 glass-strong">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="relative">
            <Brain className="h-6 w-6 text-inkos-cyan transition-colors group-hover:text-inkos-teal-300" />
            <span className="absolute -top-0.5 -right-0.5 h-1.5 w-1.5 rounded-full bg-inkos-emerald opacity-70 group-hover:opacity-100 transition-opacity" />
          </div>
          <span className="text-lg font-bold tracking-tight">
            <span className="text-inkos-cyan text-glow-cyan">Inkos</span>
            <span className="text-inkos-teal-300 text-glow-teal">AI</span>
          </span>
        </Link>

        {/* Navigation */}
        <nav className="hidden md:flex items-center gap-0.5">
          {NAV_ITEMS.map((item) => {
            const active =
              item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-200",
                  active
                    ? "bg-inkos-cyan/10 text-inkos-cyan shadow-sm shadow-inkos-cyan/5"
                    : "text-muted-foreground hover:bg-white/[0.03] hover:text-foreground",
                )}
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Right side: search trigger + settings */}
        <div className="flex items-center gap-2">
          {/* Command palette trigger */}
          <button
            onClick={() =>
              document.dispatchEvent(
                new KeyboardEvent("keydown", {
                  key: "k",
                  metaKey: true,
                  ctrlKey: true,
                }),
              )
            }
            className="hidden sm:flex items-center gap-2 rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-1.5 text-xs text-muted-foreground hover:border-inkos-cyan/20 hover:text-foreground transition-all duration-200"
          >
            <Search className="h-3.5 w-3.5" />
            <span>Search</span>
            <kbd className="font-mono text-[9px] bg-inkos-navy-800/60 px-1.5 py-0.5 rounded border border-white/[0.06] ml-2">
              ⌘K
            </kbd>
        </button>

        {settings?.active_provider_id && settings?.active_model_id && (
          <Link
            href="/settings"
            className="hidden sm:flex items-center gap-1.5 rounded-lg border border-inkos-cyan/15 bg-inkos-cyan/5 px-2.5 py-1 text-[11px] text-inkos-cyan hover:bg-inkos-cyan/10 transition-all duration-200"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-inkos-cyan" />
            <span className="truncate max-w-[120px]">
              {activeProvider?.display_name ?? settings.active_provider_id}
            </span>
            <span className="text-inkos-cyan/40">/</span>
            <span className="truncate max-w-[80px]">
              {settings.active_model_id}
            </span>
          </Link>
        )}

        {/* Settings button */}
          <button
            onClick={() =>
              window.dispatchEvent(new CustomEvent("open-settings"))
            }
            className="h-8 w-8 rounded-lg flex items-center justify-center text-muted-foreground hover:bg-white/[0.04] hover:text-foreground transition-all duration-200 focus-ring"
          >
            <Settings className="h-4 w-4" />
          </button>

          {/* User avatar */}
          <div className="h-8 w-8 rounded-full bg-inkos-cyan/10 border border-inkos-cyan/15 flex items-center justify-center">
            <Brain className="h-3.5 w-3.5 text-inkos-cyan" />
          </div>
        </div>
      </div>

      {/* Mobile nav */}
      <nav className="md:hidden flex items-center gap-0.5 overflow-x-auto px-4 pb-2 scrollbar-none">
        {NAV_ITEMS.map((item) => {
          const active =
            item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-all duration-200",
                active
                  ? "bg-inkos-cyan/10 text-inkos-cyan"
                  : "text-muted-foreground hover:bg-white/[0.03] hover:text-foreground",
              )}
            >
              <item.icon className="h-3.5 w-3.5" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
