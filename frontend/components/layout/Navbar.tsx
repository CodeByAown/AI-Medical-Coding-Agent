"use client"

import { useEffect, useState } from "react"
import { usePathname } from "next/navigation"
import { useTheme } from "next-themes"
import { Sun, Moon, ChevronRight } from "lucide-react"
import { useAuthStore } from "@/store/auth"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { getInitials } from "@/lib/utils"

const PAGE_TITLES: Record<string, { title: string; subtitle: string }> = {
  "/dashboard": { title: "Dashboard", subtitle: "Overview & analytics" },
  "/dashboard/coding": { title: "AI Coding Workspace", subtitle: "Automated ICD-10, CPT & HCPCS coding" },
  "/dashboard/history": { title: "Coding History", subtitle: "Past sessions & results" },
  "/dashboard/review": { title: "Review Queue", subtitle: "Human review workflow" },
  "/dashboard/settings": { title: "Settings", subtitle: "Account & preferences" },
}

export function Navbar() {
  const pathname = usePathname()
  const { resolvedTheme, setTheme } = useTheme()
  const { user, logout } = useAuthStore()
  // Avoid hydration mismatch: next-themes returns undefined on server
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])

  const pageInfo = PAGE_TITLES[pathname] ?? { title: "Neural Hub", subtitle: "" }

  return (
    <header className="flex h-14 items-center justify-between border-b border-[#1e2d4d] bg-[#080d1a]/80 px-6 backdrop-blur-md">
      {/* Page title */}
      <div className="flex items-center gap-2">
        <h1 className="text-sm font-semibold text-slate-100">{pageInfo.title}</h1>
        {pageInfo.subtitle && (
          <>
            <ChevronRight className="h-3.5 w-3.5 text-slate-600" />
            <span className="text-sm text-slate-500">{pageInfo.subtitle}</span>
          </>
        )}
      </div>

      {/* Right actions */}
      <div className="flex items-center gap-2">
        {/* Theme toggle — render only after mount to prevent hydration mismatch */}
        {mounted && (
          <button
            onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
            className="rounded-lg p-2 text-slate-400 hover:text-slate-200 hover:bg-[#0f1629] transition-colors cursor-pointer"
            title={resolvedTheme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          >
            {resolvedTheme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
        )}

        {/* User dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex items-center gap-2 rounded-lg pl-2 pr-3 py-1.5 hover:bg-[#0f1629] transition-colors cursor-pointer">
              <Avatar className="h-7 w-7">
                <AvatarFallback className="text-xs">
                  {user ? getInitials(user.email) : "U"}
                </AvatarFallback>
              </Avatar>
              <span className="text-sm text-slate-300 hidden sm:block">
                {user?.email?.split("@")[0] ?? "User"}
              </span>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <p className="text-xs text-slate-200">{user?.email}</p>
              <p className="text-[10px] text-slate-500 capitalize mt-0.5">{user?.role}</p>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={logout} className="text-red-400 focus:text-red-300 focus:bg-red-500/10">
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
