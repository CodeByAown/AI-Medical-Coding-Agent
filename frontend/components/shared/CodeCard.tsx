"use client"

import { useState } from "react"
import { ChevronDown, ChevronUp, Star } from "lucide-react"
import type { MedicalCode } from "@/types"
import { Badge } from "@/components/ui/badge"
import { ConfidenceBar } from "@/components/shared/ConfidenceBar"
import { cn } from "@/lib/utils"

interface CodeCardProps {
  code: MedicalCode
  index?: number
}

function getCodeVariant(codeType: string): "icd" | "cpt" | "hcpcs" {
  const t = codeType.toUpperCase()
  if (t.includes("ICD")) return "icd"
  if (t.includes("CPT")) return "cpt"
  return "hcpcs"
}

export function CodeCard({ code, index = 0 }: CodeCardProps) {
  const [expanded, setExpanded] = useState(false)
  const variant = getCodeVariant(code.code_type)

  return (
    <div
      className={cn(
        "group rounded-xl border bg-[#0a0f1e] p-4 transition-all duration-200",
        "border-[#1e2d4d] hover:border-[#263754]",
        code.is_primary && "border-blue-500/30 bg-blue-500/5"
      )}
      style={{ animationDelay: `${index * 60}ms` }}
    >
      <div className="flex items-start gap-3">
        {/* Code badge */}
        <div className="flex-shrink-0">
          <Badge variant={variant} className="text-sm font-mono px-2.5 py-1">
            {code.code}
          </Badge>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-medium text-slate-200 leading-snug">
                  {code.description}
                </span>
                {code.is_primary && (
                  <span className="inline-flex items-center gap-1 rounded-md bg-blue-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-blue-400 border border-blue-500/25 uppercase tracking-wider">
                    <Star className="h-2.5 w-2.5 fill-current" />
                    Primary
                  </span>
                )}
              </div>

              {code.hierarchy && (
                <p className="mt-0.5 text-xs text-slate-500 font-mono">{code.hierarchy}</p>
              )}
            </div>

            <ConfidenceBar value={code.confidence} size="sm" className="flex-shrink-0 mt-0.5" />
          </div>

          {/* Evidence (expandable) */}
          {code.evidence && (
            <div className="mt-2">
              <button
                onClick={() => setExpanded(!expanded)}
                className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 transition-colors cursor-pointer"
              >
                {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                Evidence
              </button>
              {expanded && (
                <p className="mt-1.5 text-xs text-slate-400 bg-[#080d1a] rounded-lg px-3 py-2 border border-[#1e2d4d] leading-relaxed italic">
                  "{code.evidence}"
                </p>
              )}
            </div>
          )}

          {/* Modifiers */}
          {code.modifiers && code.modifiers.length > 0 && (
            <div className="mt-2 flex gap-1 flex-wrap">
              {code.modifiers.map((mod) => (
                <span key={mod} className="rounded bg-[#141e35] px-1.5 py-0.5 text-xs font-mono text-slate-400 border border-[#1e2d4d]">
                  -{mod}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
