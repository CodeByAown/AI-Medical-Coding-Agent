import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "bg-blue-500/15 text-blue-400 border border-blue-500/25",
        success: "bg-emerald-500/15 text-emerald-400 border border-emerald-500/25",
        warning: "bg-amber-500/15 text-amber-400 border border-amber-500/25",
        danger: "bg-red-500/15 text-red-400 border border-red-500/25",
        outline: "border border-[#1e2d4d] text-slate-400",
        secondary: "bg-[#141e35] text-slate-300 border border-[#1e2d4d]",
        icd: "bg-blue-500/15 text-blue-300 border border-blue-500/20 font-mono",
        cpt: "bg-emerald-500/15 text-emerald-300 border border-emerald-500/20 font-mono",
        hcpcs: "bg-purple-500/15 text-purple-300 border border-purple-500/20 font-mono",
        primary: "bg-gradient-to-r from-blue-600 to-indigo-600 text-white",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
