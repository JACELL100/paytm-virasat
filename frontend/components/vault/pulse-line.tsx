"use client";

import * as React from "react";
import { motion, useReducedMotion, type Transition } from "motion/react";
import { cn } from "@/lib/utils";

export type PulseLineStatus = "active" | "challenge" | "released";

export interface PulseLineProps {
  status: PulseLineStatus;
  className?: string;
  /** 0–1 fraction of the challenge window remaining. Only used when status === "challenge". */
  challengeProgress?: number;
  /** Initials shown on the branch avatars when status === "released". */
  nomineeInitials?: string[];
  height?: number;
}

// A gentle ECG-style zigzag path across a 0-400 viewbox.
const LINE_PATH =
  "M0,40 L110,40 L128,40 L138,14 L150,64 L162,40 L182,40 L400,40";
const RELEASE_TRUNK_END_X = 260;

const STATUS_COLOR: Record<PulseLineStatus, string> = {
  active: "var(--brand-cyan)",
  challenge: "var(--warning)",
  released: "var(--gold)",
};

export function PulseLine({
  status,
  className,
  challengeProgress = 0.6,
  nomineeInitials = ["S", "A"],
  height = 96,
}: PulseLineProps) {
  const reduceMotion = useReducedMotion();
  const color = STATUS_COLOR[status];

  const pulseTransition: Transition = reduceMotion
    ? { duration: 0 }
    : {
        duration: status === "challenge" ? 3.2 : 2.1,
        repeat: Infinity,
        ease: "easeInOut",
      };

  return (
    <div className={cn("relative w-full", className)} style={{ height }}>
      <svg
        viewBox="0 0 400 80"
        className="h-full w-full overflow-visible"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="pulse-line-fade" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor={color} stopOpacity="0.15" />
            <stop offset="50%" stopColor={color} stopOpacity="1" />
            <stop offset="100%" stopColor={color} stopOpacity="0.35" />
          </linearGradient>
        </defs>

        {/* Base line */}
        <motion.path
          d={status === "released" ? `M0,40 L${RELEASE_TRUNK_END_X},40` : LINE_PATH}
          fill="none"
          stroke="url(#pulse-line-fade)"
          strokeWidth={status === "challenge" ? 1.75 : 2}
          strokeLinecap="round"
          strokeLinejoin="round"
          animate={{ opacity: status === "challenge" ? [0.55, 1, 0.55] : 1 }}
          transition={pulseTransition}
        />

        {/* Traveling pulse dot — only while active/challenge */}
        {status !== "released" && (
          <motion.circle
            r={status === "challenge" ? 3.5 : 4}
            fill={color}
            style={{ offsetPath: `path("${LINE_PATH}")` }}
            animate={
              reduceMotion
                ? { offsetDistance: "0%" }
                : { offsetDistance: ["0%", "100%"] }
            }
            transition={
              reduceMotion
                ? { duration: 0 }
                : {
                    duration: status === "challenge" ? 4.5 : 2.4,
                    repeat: Infinity,
                    ease: "linear",
                  }
            }
          />
        )}

        {/* Released: branch out to nominee avatars */}
        {status === "released" &&
          nomineeInitials.map((_, i) => {
            const count = nomineeInitials.length;
            const spread = 22;
            const yOffset = (i - (count - 1) / 2) * spread;
            const endX = 400 - 20;
            const endY = 40 + yOffset;
            return (
              <motion.path
                key={i}
                d={`M${RELEASE_TRUNK_END_X},40 Q${(RELEASE_TRUNK_END_X + endX) / 2},${40 + yOffset * 0.3} ${endX},${endY}`}
                fill="none"
                stroke={color}
                strokeWidth={1.5}
                strokeLinecap="round"
                strokeDasharray="1 1"
                pathLength={1}
                initial={reduceMotion ? undefined : { pathLength: 0, opacity: 0 }}
                animate={{ pathLength: 1, opacity: 0.9 }}
                transition={{ duration: 0.8, delay: reduceMotion ? 0 : 0.15 * i, ease: "easeOut" }}
              />
            );
          })}
      </svg>

      {/* Countdown ring for challenge state */}
      {status === "challenge" && (
        <div className="absolute -top-2 right-0 flex items-center">
          <CountdownRing progress={challengeProgress} reduceMotion={!!reduceMotion} />
        </div>
      )}

      {/* Nominee avatars for released state */}
      {status === "released" && (
        <div className="pointer-events-none absolute inset-0">
          {nomineeInitials.map((initial, i) => {
            const count = nomineeInitials.length;
            const spread = 22;
            const yOffset = (i - (count - 1) / 2) * spread;
            return (
              <motion.div
                key={i}
                className="absolute flex size-7 items-center justify-center rounded-full text-[11px] font-semibold text-white shadow-soft"
                style={{
                  left: "calc(100% - 34px)",
                  top: `calc(50% + ${yOffset}px - 14px)`,
                  background: "linear-gradient(135deg, var(--gold), #c9902f)",
                }}
                initial={reduceMotion ? undefined : { scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ duration: 0.4, delay: reduceMotion ? 0 : 0.4 + 0.15 * i }}
              >
                {initial}
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function CountdownRing({
  progress,
  reduceMotion,
}: {
  progress: number;
  reduceMotion: boolean;
}) {
  const r = 16;
  const c = 2 * Math.PI * r;
  const offset = c * (1 - Math.min(Math.max(progress, 0), 1));

  return (
    <svg width={40} height={40} viewBox="0 0 40 40" aria-hidden="true">
      <circle cx="20" cy="20" r={r} fill="none" stroke="var(--surface-2)" strokeWidth={3} />
      <motion.circle
        cx="20"
        cy="20"
        r={r}
        fill="none"
        stroke="var(--warning)"
        strokeWidth={3}
        strokeLinecap="round"
        strokeDasharray={c}
        strokeDashoffset={offset}
        transform="rotate(-90 20 20)"
        animate={reduceMotion ? undefined : { opacity: [1, 0.7, 1] }}
        transition={{ duration: 2, repeat: Infinity }}
      />
    </svg>
  );
}
