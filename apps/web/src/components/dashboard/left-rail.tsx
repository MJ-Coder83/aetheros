"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
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
  type LucideIcon,
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
    <aside className="w-16 h-full flex flex-col shrink-0 relative">
      {/* Holographic surface background */}
      <div className="absolute inset-0 holo-surface border-r border-border" />

      {/* Subtle grid texture overlay */}
      <div className="absolute inset-0 grid-texture opacity-30 pointer-events-none" />

      {/* Content container */}
      <div className="relative z-10 flex flex-col h-full">
        {/* Logo section with pulse animation */}
        <div className="h-14 flex items-center justify-center border-b border-border/50 relative">
          {/* Animated glow behind logo */}
          <motion.div
            className="absolute inset-0 flex items-center justify-center"
            animate={{
              boxShadow: [
                "0 0 20px rgba(34, 211, 238, 0.1)",
                "0 0 32px rgba(34, 211, 238, 0.2)",
                "0 0 20px rgba(34, 211, 238, 0.1)",
              ],
            }}
            transition={{
              duration: 4,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />

          <svg
            width="28"
            height="28"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#22D3EE"
            strokeWidth="1.5"
            aria-label="InkosAI Logo"
            className="relative z-10"
          >
            <path d="M12 2a7 7 0 0 1 7 7c0 2.38-1.19 4.47-3 5.74V17a2 2 0 0 1-2 2H10a2 2 0 0 1-2-2v-2.26C6.19 13.47 5 11.38 5 9a7 7 0 0 1 7-7z" />
            <path d="M9 21h6M12 17v4" />
            <motion.circle
              cx="9"
              cy="9"
              r="1"
              fill="#22D3EE"
              animate={{
                opacity: [0.7, 1, 0.7],
                scale: [1, 1.2, 1],
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: "easeInOut",
              }}
            />
            <motion.circle
              cx="15"
              cy="9"
              r="1"
              fill="#22D3EE"
              animate={{
                opacity: [0.7, 1, 0.7],
                scale: [1, 1.2, 1],
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: "easeInOut",
                delay: 0.5,
              }}
            />
          </svg>
        </div>

        {/* Navigation items */}
        <nav className="flex-1 py-3 flex flex-col gap-1.5 items-center relative z-10">
          {navItems.map(({ href, icon: Icon, label }, index) => {
            const isActive = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                aria-label={label}
                data-tooltip={label}
                className={`tooltip-right tooltip-scan w-10 h-10 flex items-center justify-center rounded-lg relative group transition-all duration-300 ${
                  isActive
                    ? "text-inkos-cyan"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {/* Active state — holographic indicator */}
                {isActive && (
                  <>
                    {/* Animated glow bar */}
                    <motion.div
                      className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-6 rounded-r"
                      style={{
                        background: "linear-gradient(180deg, #22D3EE 0%, #67E8F9 100%)",
                      }}
                      initial={{ opacity: 0, x: -4 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.3 }}
                    />

                    {/* Holographic background glow */}
                    <motion.div
                      className="absolute inset-0 rounded-lg"
                      style={{
                        background: "rgba(34, 211, 238, 0.08)",
                        border: "1px solid rgba(34, 211, 238, 0.15)",
                      }}
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ duration: 0.2 }}
                    />
                  </>
                )}

                {/* Icon with floating effect on hover */}
                <motion.div
                  className="relative z-10"
                  whileHover={{
                    y: -2,
                    scale: 1.1,
                  }}
                  transition={{
                    duration: 0.2,
                    ease: "easeOut",
                  }}
                >
                  <Icon className="w-4 h-4" />
                </motion.div>

                {/* Hover scan line effect */}
                <motion.div
                  className="absolute inset-0 rounded-lg overflow-hidden pointer-events-none"
                  initial={{ opacity: 0 }}
                  whileHover={{ opacity: 1 }}
                  transition={{ duration: 0.15 }}
                >
                  <motion.div
                    className="absolute inset-0"
                    style={{
                      background: "linear-gradient(180deg, transparent 0%, rgba(34, 211, 238, 0.06) 50%, transparent 100%)",
                      backgroundSize: "100% 200%",
                    }}
                    animate={{
                      backgroundPosition: ["0% 0%", "0% 200%"],
                    }}
                    transition={{
                      duration: 0.6,
                      ease: "easeOut",
                    }}
                  />
                </motion.div>
              </Link>
            );
          })}
        </nav>

        {/* Bottom section — Settings + Avatar */}
        <div className="py-3 flex flex-col items-center gap-2 border-t border-border/50 relative z-10">
          <motion.button
            aria-label="Settings"
            data-tooltip="Settings"
            onClick={openSettings}
            className="tooltip-right w-10 h-10 flex items-center justify-center rounded-lg text-muted-foreground hover:text-foreground transition-all duration-300 cursor-pointer group relative"
            whileHover={{
              scale: 1.05,
              rotate: [0, -5, 5, 0],
            }}
            transition={{
              duration: 0.3,
              ease: "easeOut",
            }}
          >
            <Settings className="w-4 h-4" />
            {/* Hover glow */}
            <div className="absolute inset-0 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-300"
              style={{
                background: "rgba(34, 211, 238, 0.06)",
                border: "1px solid rgba(34, 211, 238, 0.1)",
              }}
            />
          </motion.button>

          {/* Avatar with holographic ring */}
          <motion.div
            className="w-8 h-8 rounded-full relative"
            style={{
              background: "linear-gradient(135deg, rgba(34, 211, 238, 0.15) 0%, rgba(103, 232, 249, 0.1) 100%)",
              border: "1px solid rgba(34, 211, 238, 0.2)",
            }}
            whileHover={{
              scale: 1.05,
              boxShadow: "0 0 20px rgba(34, 211, 238, 0.3)",
            }}
          >
            <div className="absolute inset-0 flex items-center justify-center text-[10px] font-medium text-inkos-cyan">
              AK
            </div>
            {/* Animated orbital ring */}
            <motion.div
              className="absolute inset-0 rounded-full"
              style={{
                border: "1px solid rgba(34, 211, 238, 0.2)",
              }}
              animate={{
                rotate: 360,
                scale: [1, 1.05, 1],
              }}
              transition={{
                rotate: { duration: 8, repeat: Infinity, ease: "linear" },
                scale: { duration: 3, repeat: Infinity, ease: "easeInOut" },
              }}
            />
          </motion.div>
        </div>
      </div>
    </aside>
  );
}
