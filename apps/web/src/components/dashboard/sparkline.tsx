interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: "cyan" | "emerald" | "amber" | "violet";
  strokeWidth?: number;
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
        stroke={colorMap[color]}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}