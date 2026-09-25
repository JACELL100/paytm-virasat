"use client";

import * as React from "react";
import { motion, useReducedMotion, AnimatePresence } from "motion/react";
import { cn } from "@/lib/utils";
import { truncateMiddle } from "@/lib/format";

export type VaultSealState = "idle" | "sealing" | "sealed";

export interface VaultSealProps {
  state: VaultSealState;
  txHash?: string | null;
  className?: string;
  caption?: string;
}

const SPRING = { type: "spring" as const, stiffness: 260, damping: 30 };

export function VaultSeal({ state, txHash, className, caption }: VaultSealProps) {
  const reduceMotion = useReducedMotion();
  const closed = state === "sealing" || state === "sealed";

  return (
    <div className={cn("flex flex-col items-center gap-5", className)}>
      <div className="relative">
        <motion.div
          className="absolute -inset-6 rounded-full opacity-60 blur-2xl"
          style={{
            background:
              state === "sealed"
                ? "radial-gradient(circle, var(--brand-cyan) 0%, transparent 70%)"
                : "radial-gradient(circle, var(--brand-navy) 0%, transparent 70%)",
          }}
          animate={reduceMotion ? undefined : { opacity: [0.35, 0.6, 0.35] }}
          transition={{ duration: 3, repeat: Infinity }}
        />
        <svg width={120} height={132} viewBox="0 0 120 132" className="relative">
          {/* Shackle */}
          <motion.path
            d="M38 56 V40 a22 22 0 0 1 44 0 V56"
            fill="none"
            stroke="var(--brand-navy)"
            strokeWidth={10}
            strokeLinecap="round"
            initial={false}
            animate={
              reduceMotion
                ? { y: closed ? 0 : -6, rotate: 0 }
                : closed
                  ? { y: 0, rotate: 0 }
                  : { y: -14, rotate: -6 }
            }
            transition={SPRING}
            style={{ transformOrigin: "38px 56px" }}
          />
          {/* Body */}
          <motion.rect
            x={16}
            y={52}
            width={88}
            height={68}
            rx={16}
            fill="var(--brand-navy)"
            animate={reduceMotion ? undefined : { scale: closed ? [1, 1.04, 1] : 1 }}
            transition={{ duration: 0.5 }}
          />
          <rect x={16} y={52} width={88} height={68} rx={16} fill="url(#seal-gloss)" opacity={0.5} />
          <defs>
            <linearGradient id="seal-gloss" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#ffffff" stopOpacity="0.25" />
              <stop offset="40%" stopColor="#ffffff" stopOpacity="0" />
            </linearGradient>
          </defs>
          {/* Keyhole */}
          <AnimatePresence>
            {closed && (
              <motion.g
                initial={reduceMotion ? { opacity: 1 } : { opacity: 0, scale: 0 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ ...SPRING, delay: reduceMotion ? 0 : 0.15 }}
                style={{ transformOrigin: "60px 86px" }}
              >
                <circle cx={60} cy="82" r={7} fill="var(--brand-cyan)" />
                <rect x={56.5} y={82} width={7} height={16} rx={2} fill="var(--brand-cyan)" />
              </motion.g>
            )}
          </AnimatePresence>
        </svg>
      </div>

      {caption && <p className="text-sm text-muted text-center">{caption}</p>}

      <AnimatePresence mode="wait">
        {state === "sealed" && txHash && (
          <motion.div
            key="hash"
            initial={reduceMotion ? { opacity: 1 } : { opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="glass-surface rounded-full px-4 py-2"
          >
            <TypedHash value={truncateMiddle(txHash, 10, 8)} reduceMotion={!!reduceMotion} />
          </motion.div>
        )}
        {state === "sealing" && (
          <motion.p
            key="sealing"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="font-mono-tabular text-xs text-muted"
          >
            Confirming on Sepolia…
          </motion.p>
        )}
      </AnimatePresence>
    </div>
  );
}

function TypedHash({ value, reduceMotion }: { value: string; reduceMotion: boolean }) {
  return (
    <span className="font-mono-tabular text-sm text-brand-navy dark:text-brand-cyan">
      {value.split("").map((char, i) => (
        <motion.span
          key={`${char}-${i}`}
          initial={reduceMotion ? { opacity: 1 } : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: reduceMotion ? 0 : i * 0.04, duration: 0.15 }}
        >
          {char}
        </motion.span>
      ))}
    </span>
  );
}
