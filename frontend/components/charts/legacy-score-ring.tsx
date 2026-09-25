"use client";

import * as React from "react";
import { RadialBar, RadialBarChart, PolarAngleAxis } from "recharts";
import NumberFlow from "@number-flow/react";
import { cn } from "@/lib/utils";

function scoreColor(score: number) {
  if (score >= 75) return "var(--success)";
  if (score >= 45) return "var(--warning)";
  return "var(--danger)";
}

export function LegacyScoreRing({
  score,
  size = 176,
  className,
}: {
  score: number;
  size?: number;
  className?: string;
}) {
  const color = scoreColor(score);
  const data = [{ value: score, fill: color }];

  return (
    <div className={cn("relative", className)} style={{ width: size, height: size }}>
      <RadialBarChart
        width={size}
        height={size}
        cx="50%"
        cy="50%"
        innerRadius="78%"
        outerRadius="100%"
        barSize={12}
        data={data}
        startAngle={90}
        endAngle={-270}
      >
        <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
        <RadialBar
          background={{ fill: "var(--surface-2)" }}
          dataKey="value"
          cornerRadius={999}
          angleAxisId={0}
          isAnimationActive
          animationDuration={900}
        />
      </RadialBarChart>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <NumberFlow
          value={score}
          className="font-display text-3xl font-bold tabular-nums text-text"
        />
        <span className="text-xs text-muted">/ 100</span>
      </div>
    </div>
  );
}
