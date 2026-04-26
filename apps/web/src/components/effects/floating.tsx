"use client";

import { motion, type HTMLMotionProps } from "framer-motion";
import * as React from "react";

/**
 * Floating Animation Component
 *
 * Framer Motion-powered floating animation with multiple variants.
 * Use for holographic UI elements that need to appear suspended.
 */

interface FloatingProps extends HTMLMotionProps<"div"> {
  children: React.ReactNode;
  variant?: "vertical" | "diagonal" | "orbital";
  amplitude?: number;
  duration?: number;
  delay?: number;
}

const floatVariants = {
  vertical: {
    y: [-2, 2, -2],
  },
  diagonal: {
    x: [0, 2, -2, 2, 0],
    y: [0, -3, -4, -2, 0],
  },
  orbital: {
    y: [0, -3, -5, -3, 0],
    rotate: [0, 1, 0, -1, 0],
  },
};

export function Floating({
  children,
  variant = "vertical",
  amplitude = 4,
  duration = 4,
  delay = 0,
  ...props
}: FloatingProps) {
  const variants = floatVariants[variant];

  return (
    <motion.div
      animate={variants}
      transition={{
        duration,
        delay,
        repeat: Infinity,
        ease: "easeInOut",
      }}
      {...props}
    >
      {children}
    </motion.div>
  );
}

/**
 * Pulse Glow Component
 * Animated glow effect for status indicators and accents
 */
interface PulseGlowProps {
  children: React.ReactNode;
  color?: "cyan" | "emerald" | "amber" | "purple" | "red";
  intensity?: "soft" | "normal" | "intense";
}

const glowColors = {
  cyan: "rgba(34, 211, 238, 0.4)",
  emerald: "rgba(16, 185, 129, 0.4)",
  amber: "rgba(245, 158, 11, 0.4)",
  purple: "rgba(124, 122, 237, 0.4)",
  red: "rgba(239, 68, 68, 0.4)",
};

const glowIntensity = {
  soft: { scale: [1, 1.05, 1], opacity: [0.3, 0.5, 0.3] },
  normal: { scale: [1, 1.1, 1], opacity: [0.4, 0.7, 0.4] },
  intense: { scale: [1, 1.2, 1], opacity: [0.5, 0.9, 0.5] },
};

export function PulseGlow({
  children,
  color = "cyan",
  intensity = "normal",
}: PulseGlowProps) {
  const glowColor = glowColors[color];
  const intensityVars = glowIntensity[intensity];

  return (
    <motion.div
      animate={{
        scale: intensityVars.scale,
        opacity: intensityVars.opacity,
        boxShadow: [
          `0 0 12px ${glowColor}`,
          `0 0 24px ${glowColor}`,
          `0 0 12px ${glowColor}`,
        ],
      }}
      transition={{
        duration: 2,
        repeat: Infinity,
        ease: "easeInOut",
      }}
    >
      {children}
    </motion.div>
  );
}

/**
 * Stagger Container
 * Animates children with staggered entrance
 */
interface StaggerContainerProps {
  children: React.ReactNode;
  staggerDelay?: number;
  animation?: "fade-up" | "slide-right" | "scale-in";
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05,
    },
  },
};

const itemVariants = {
  "fade-up": {
    hidden: { opacity: 0, y: 12 },
    visible: { opacity: 1, y: 0 },
  },
  "slide-right": {
    hidden: { opacity: 0, x: -16 },
    visible: { opacity: 1, x: 0 },
  },
  "scale-in": {
    hidden: { opacity: 0, scale: 0.95 },
    visible: { opacity: 1, scale: 1 },
  },
};

export function StaggerContainer({
  children,
  staggerDelay = 0.05,
  animation = "fade-up",
}: StaggerContainerProps) {
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      transition={{
        staggerChildren: staggerDelay,
      }}
    >
      {React.Children.map(children, (child, index) => (
        <motion.div
          key={index}
          variants={itemVariants[animation]}
          transition={{
            duration: 0.4,
            ease: [0.4, 0, 0.2, 1],
          }}
        >
          {child}
        </motion.div>
      ))}
    </motion.div>
  );
}

/**
 * Terminal Text Reveal
 * Typewriter-style text reveal effect
 */
interface TerminalTextProps {
  text: string;
  delay?: number;
  className?: string;
}

export function TerminalText({
  text,
  delay = 0,
  className = "",
}: TerminalTextProps) {
  return (
    <motion.span
      className={className}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{
        duration: 0.1,
        delay,
      }}
    >
      {text}
    </motion.span>
  );
}
