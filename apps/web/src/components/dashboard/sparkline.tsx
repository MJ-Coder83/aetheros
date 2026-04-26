"use client";

import { motion } from "framer-motion";

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: "cyan" | "emerald" | "amber" | "violet";
  strokeWidth?: number;
  animated?: boolean;
}

const colorMap: Record<NonNullable<SparklineProps["color"]>, string> = {
  cyan: "#22D3EE",
  emerald: "#10B981",
  amber: "#F59E0B",
  violet: "#A78BFA",
};

export function Sparkline({
  data,
  width = 60,
  height = 16,
  color = "cyan",
  strokeWidth = 1.5,
  animated = false,
}: SparklineProps) {
  if (!data || data.length < 2) return null;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const points = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - ((v - min) / range) * (height - 2) - 1;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  const strokeColor = colorMap[color];

  if (animated) {
    return (
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        className="overflow-visible"
      >
        {/* Glow effect underneath */}
        <motion.polyline
          points={points}
          fill="none"
          stroke={strokeColor}
          strokeWidth={strokeWidth * 2}
          strokeLinecap="round"
          strokeLinejoin="round"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 0.3 }}
          transition={{
            duration: 1.5,
            ease: "easeOut",
            repeat: Infinity,
            repeatDelay: 0.5,
          }}
        />
        {/* Main line */}
        <motion.polyline
          points={points}
          fill="none"
          stroke={strokeColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeLinejoin="round"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{
            duration: 1,
            ease: "easeOut",
            repeat: Infinity,
            repeatDelay: 2,
          }}
        />
        {/* Data point highlights */}
        {data.map((_, index) => {
          const x = (index / (data.length - 1)) * width;
          const y = height - ((data[index] - min) / range) * (height - 2) - 1;
          return (
            <motion.circle
              key={index}
              cx={x}
              cy={y}
              r={2}
              fill={strokeColor}
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: [0, 1, 0], scale: [0, 1.5, 0] }}
              transition={{
                duration: 2,
                delay: index * 0.1,
                repeat: Infinity,
                repeatDelay: 1,
              }}
            />
          );
        })}
      </svg>
    );
  }

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="overflow-visible"
    >
      <polyline
        points={points}
        fill="none"
        stroke={strokeColor}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
