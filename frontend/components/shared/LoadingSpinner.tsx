import { cn } from "@/lib/utils"

interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg"
  className?: string
  label?: string
}

export function LoadingSpinner({ size = "md", className, label }: LoadingSpinnerProps) {
  const sizes = { sm: "h-4 w-4", md: "h-6 w-6", lg: "h-10 w-10" }

  return (
    <div className={cn("flex flex-col items-center justify-center gap-3", className)}>
      <div className="relative">
        <div
          className={cn(
            "rounded-full border-2 border-[#1e2d4d]",
            sizes[size]
          )}
        />
        <div
          className={cn(
            "absolute inset-0 rounded-full border-2 border-transparent border-t-blue-500 animate-spin",
            sizes[size]
          )}
        />
      </div>
      {label && <p className="text-sm text-slate-400 animate-pulse">{label}</p>}
    </div>
  )
}
