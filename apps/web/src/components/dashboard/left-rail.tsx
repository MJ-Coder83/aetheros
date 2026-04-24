"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Cpu,
  ScrollText,
  FileCheck,
  FlaskConical,
  MessageSquare,
  GitBranch,
  User,
  BookOpen,
  Globe,
  Settings,
} from "lucide-react";

const navItems = [
  { href: "/", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/prime", icon: Cpu, label: "Prime" },
  { href: "/tape", icon: ScrollText, label: "Tape" },
  { href: "/proposals", icon: FileCheck, label: "Proposals" },
  { href: "/simulations", icon: FlaskConical, label: "Simulations" },
  { href: "/explain", icon: MessageSquare, label: "Explain" },
  { href: "/planning", icon: GitBranch, label: "Planning" },
  { href: "/profile", icon: User, label: "Profile" },
  { href: "/knowledge", icon: BookOpen, label: "Knowledge" },
  { href: "/domains", icon: Globe, label: "Domains" },
];

function openSettings() {
  window.dispatchEvent(new CustomEvent("open-settings"));
}

export function LeftRail() {
  const pathname = usePathname();

  return (
    <aside className="w-16 h-full flex flex-col bg-card border-r border-border shrink-0">
      <div className="h-12 flex items-center justify-center border-b border-border">
        <svg
          width="28"
          height="28"
          viewBox="0 0 24 24"
          fill="none"
          stroke="#22D3EE"
          strokeWidth="1.5"
          aria-label="InkosAI Logo"
        >
          <path d="M12 2a7 7 0 0 1 7 7c0 2.38-1.19 4.47-3 5.74V17a2 2 0 0 1-2 2H10a2 2 0 0 1-2-2v-2.26C6.19 13.47 5 11.38 5 9a7 7 0 0 1 7-7z" />
          <path d="M9 21h6M12 17v4" />
          <circle cx="9" cy="9" r="1" fill="#22D3EE" />
          <circle cx="15" cy="9" r="1" fill="#22D3EE" />
        </svg>
      </div>

      <nav className="flex-1 py-3 flex flex-col gap-1 items-center">
        {navItems.map(({ href, icon: Icon, label }) => {
          const isActive = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              aria-label={label}
              data-tooltip={label}
              className={`tooltip-right w-10 h-10 flex items-center justify-center rounded relative ${
                isActive ? "" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {isActive && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-6 bg-inkos-cyan rounded-r" />
              )}
              <Icon
                className={`w-4 h-4 ${isActive ? "text-inkos-cyan" : ""}`}
              />
            </Link>
          );
        })}
      </nav>

      <div className="py-3 flex flex-col items-center gap-2 border-t border-border">
        <button
          aria-label="Settings"
          data-tooltip="Settings"
          onClick={openSettings}
          className="tooltip-right w-10 h-10 flex items-center justify-center rounded text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
        >
          <Settings className="w-4 h-4" />
        </button>
        <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center text-xs font-medium text-inkos-cyan">
          AK
        </div>
      </div>
    </aside>
  );
}