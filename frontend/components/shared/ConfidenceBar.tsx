"use client"

import { cn, formatConfidence, getConfidenceBgColor } from "@/lib/utils"

interface ConfidenceBarProps {
  value: number
  showLabel?: boolean
  size?: "sm" | "md"
  className?: string
}

export function ConfidenceBar({ value, showLabel = true, size = "md", className }: ConfidenceBarProps) {
  const pct = Math.round(value * 100)
  const barColor = getConfidenceBgColor(value)
  const textColor =
    value >= 0.8 ? "text-emerald-400" : value >= 0.6 ? "text-amber-400" : "text-red-400"

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div
        className={cn(
          "relative overflow-hidden rounded-full bg-[#1e2d4d]",
          size === "sm" ? "h-1.5 w-16" : "h-2 w-24"
        )}
      >
        <div
          className={cn("h-full rounded-full transition-all duration-700 ease-out", barColor)}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showLabel && (
        <span className={cn("font-mono font-medium tabular-nums", textColor, size === "sm" ? "text-xs" : "text-sm")}>
          {formatConfidence(value)}
        </span>
      )}
    </div>
  )
}
