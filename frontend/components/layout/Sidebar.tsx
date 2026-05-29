"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  LayoutDashboard,
  Brain,
  History,
  ClipboardCheck,
  Settings,
  LogOut,
  Activity,
} from "lucide-react"
import { useAuthStore } from "@/store/auth"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { cn, getInitials } from "@/lib/utils"

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dashboard/coding", label: "AI Coding", icon: Brain },
  { href: "/dashboard/history", label: "History", icon: History },
  { href: "/dashboard/review", label: "Review Queue", icon: ClipboardCheck },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()
  const { user, logout } = useAuthStore()

  return (
    <aside className="flex h-full w-[260px] flex-shrink-0 flex-col border-r border-[#1e2d4d] bg-[#080d1a]">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-[#1e2d4d]">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 shadow-[0_0_12px_rgba(59,130,246,0.3)]">
          <Activity className="h-5 w-5 text-white" />
        </div>
        <div>
          <p className="text-sm font-bold text-slate-100 tracking-tight">Neural Hub</p>
          <p className="text-[10px] text-slate-500 uppercase tracking-widest">Medical AI</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-0.5">
        <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-600">
          Navigation
        </p>
        {navItems.map(({ href, label, icon: Icon }) => {
          const isActive = href === "/dashboard" ? pathname === "/dashboard" : pathname.startsWith(href)
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150",
                isActive
                  ? "bg-blue-500/10 text-blue-400"
                  : "text-slate-400 hover:bg-[#0f1629] hover:text-slate-200"
              )}
            >
              {isActive && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-blue-500 rounded-r-full shadow-[0_0_6px_rgba(59,130,246,0.6)]" />
              )}
              <Icon
                className={cn(
                  "h-4 w-4 flex-shrink-0 transition-colors",
                  isActive ? "text-blue-400" : "text-slate-500 group-hover:text-slate-300"
                )}
              />
              {label}
            </Link>
          )
        })}
      </nav>

      {/* User Profile */}
      <div className="border-t border-[#1e2d4d] p-4">
        <div className="flex items-center gap-3 rounded-xl bg-[#0f1629] border border-[#1e2d4d] p-3">
          <Avatar className="h-8 w-8 flex-shrink-0">
            <AvatarFallback className="text-xs">
              {user ? getInitials(user.email) : "U"}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-slate-200 truncate">
              {user?.email?.split("@")[0] ?? "User"}
            </p>
            <p className="text-[10px] text-slate-500 capitalize">{user?.role ?? "user"}</p>
          </div>
          <button
            onClick={logout}
            title="Sign out"
            className="flex-shrink-0 rounded-lg p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer"
          >
            <LogOut className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </aside>
  )
}
