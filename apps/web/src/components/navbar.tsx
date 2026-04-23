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
  User,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/prime", label: "Prime", icon: MessageSquare },
  { href: "/tape", label: "Tape", icon: ScrollText },
  { href: "/proposals", label: "Proposals", icon: Vote },
  { href: "/simulations", label: "Simulations", icon: FlaskConical },
];

export function Navbar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 glass-strong">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <Brain className="h-7 w-7 text-inkos-purple transition-colors group-hover:text-inkos-cyan" />
          <span className="text-lg font-bold tracking-tight">
            <span className="text-inkos-purple text-glow-purple">
              Inkos
            </span>
            <span className="text-inkos-cyan text-glow-cyan">AI</span>
          </span>
        </Link>

        {/* Navigation */}
        <nav className="hidden md:flex items-center gap-1">
          {NAV_ITEMS.map((item) => {
            const active =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-all",
                  active
                    ? "bg-inkos-purple/20 text-inkos-cyan"
                    : "text-muted-foreground hover:bg-inkos-purple/10 hover:text-foreground",
                )}
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* User avatar placeholder */}
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-full bg-inkos-purple/20 border border-inkos-purple/30 flex items-center justify-center">
            <User className="h-4 w-4 text-inkos-purple-400" />
          </div>
        </div>
      </div>

      {/* Mobile nav */}
      <nav className="md:hidden flex items-center gap-1 overflow-x-auto px-4 pb-2">
        {NAV_ITEMS.map((item) => {
          const active =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium whitespace-nowrap transition-all",
                active
                  ? "bg-inkos-purple/20 text-inkos-cyan"
                  : "text-muted-foreground hover:bg-inkos-purple/10 hover:text-foreground",
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
