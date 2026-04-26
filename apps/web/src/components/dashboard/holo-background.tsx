"use client";

import { memo } from "react";

/**
 * Holographic Background Component
 *
 * Creates an animated cyber-futuristic background with:
 * - Gradient mesh nebula (cyan/purple/emerald)
 * - Neural network pattern overlay
 * - Subtle particle drift field
 * - Optional scan line effect
 *
 * Performance: Uses CSS-only animations (GPU-accelerated)
 * Layers are fixed position to avoid repaint on scroll
 */
export const HoloBackground = memo(function HoloBackground() {
  return (
    <>
      {/* Animated gradient mesh — deep space nebula */}
      <div className="gradient-mesh" aria-hidden="true" />

      {/* Neural network pattern — subtle tech texture */}
      <div className="neural-pattern" aria-hidden="true" />

      {/* Particle field — floating data points */}
      <div className="particle-field" aria-hidden="true" />

      {/* Holographic atmosphere — cyan/teal ambient glow */}
      <div className="holo-atmosphere" aria-hidden="true" />
    </>
  );
});

/**
 * Scan Line Overlay — CRT effect (optional, toggleable)
 * Add this component for authentic retro-futuristic scan lines
 * Use sparingly — can impact readability on some displays
 */
export function ScanLines({ enabled = true }: { enabled?: boolean }) {
  if (!enabled) return null;

  return (
    <div
      className="scan-lines"
      aria-hidden="true"
      style={{ pointerEvents: "none" }}
    />
  );
}

/**
 * Floating Animation Wrapper
 * Wraps children with holographic float animation
 */
interface FloatingProps {
  children: React.ReactNode;
  variant?: "vertical" | "diagonal" | "orbital";
  speed?: "slow" | "normal" | "fast";
}

export function Floating({
  children,
  variant = "vertical",
  speed = "normal"
}: FloatingProps) {
  const animationClass = {
    vertical: "animate-float",
    diagonal: "animate-float-diagonal",
    orbital: "animate-float-orbital",
  }[variant];

  const durationStyle = {
    slow: { animationDuration: "6s" },
    normal: {},
    fast: { animationDuration: "2s" },
  }[speed];

  return (
    <div
      className={animationClass}
      style={durationStyle}
    >
      {children}
    </div>
  );
}
