"use client"

import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import Link from "next/link"
import {
  Brain, Clock, TrendingUp, ClipboardCheck, ArrowRight,
  Activity, CheckCircle2, AlertCircle, Zap,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { useAuthStore } from "@/store/auth"
import { formatDateTime, formatConfidence } from "@/lib/utils"

// Static mock data — no Date.now() to avoid hydration mismatch
const MOCK_SESSIONS = [
  { id: "sess_001", specialty: "Cardiology", status: "completed", codes: ["I21.9", "E11.9"], confidence: 0.94, created_at: "2026-05-29T10:30:00.000Z" },
  { id: "sess_002", specialty: "Internal Medicine", status: "needs_review", codes: ["J18.9", "I10"], confidence: 0.72, created_at: "2026-05-29T08:45:00.000Z" },
  { id: "sess_003", specialty: "Pulmonology", status: "completed", codes: ["J44.1", "J45.41"], confidence: 0.88, created_at: "2026-05-29T07:00:00.000Z" },
  { id: "sess_004", specialty: "Endocrinology", status: "completed", codes: ["E11.65", "E78.5"], confidence: 0.91, created_at: "2026-05-29T05:15:00.000Z" },
  { id: "sess_005", specialty: "Neurology", status: "needs_review", codes: ["G43.909"], confidence: 0.65, created_at: "2026-05-29T03:00:00.000Z" },
]

const STATS = [
  { label: "Total Sessions", value: "1,247", trend: "+12%", icon: Activity, color: "text-blue-400", bg: "bg-blue-500/10 border-blue-500/20" },
  { label: "Avg Confidence", value: "87.3%", trend: "+2.1%", icon: TrendingUp, color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/20" },
  { label: "Pending Reviews", value: "14", trend: "-3", icon: ClipboardCheck, color: "text-amber-400", bg: "bg-amber-500/10 border-amber-500/20" },
  { label: "Codes This Month", value: "3,891", trend: "+8%", icon: Zap, color: "text-purple-400", bg: "bg-purple-500/10 border-purple-500/20" },
]

function getStatusBadge(status: string) {
  if (status === "completed") return <Badge variant="success">Completed</Badge>
  if (status === "needs_review") return <Badge variant="warning">Needs Review</Badge>
  return <Badge variant="danger">Failed</Badge>
}

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.07 } } }
const item = { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" as const } } }

// Separate client-only component to avoid SSR hydration mismatch on dynamic date/time
function WelcomeHeader() {
  const { user } = useAuthStore()
  const [mounted, setMounted] = useState(false)
  const [greeting, setGreeting] = useState("Welcome")
  const [dateStr, setDateStr] = useState("")

  useEffect(() => {
    setMounted(true)
    const hour = new Date().getHours()
    setGreeting(hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening")
    setDateStr(new Date().toLocaleDateString("en-US", {
      weekday: "long", month: "long", day: "numeric", year: "numeric"
    }))
  }, [])

  const displayName = user?.email?.split("@")[0] ?? "there"

  if (!mounted) {
    // Static placeholder that matches what SSR would render — prevents mismatch
    return (
      <div>
        <h2 className="text-xl font-semibold text-slate-100">
          Welcome, <span className="gradient-text capitalize">{displayName}</span>
        </h2>
        <p className="text-sm text-slate-500 mt-0.5 h-5" />
      </div>
    )
  }

  return (
    <div>
      <h2 className="text-xl font-semibold text-slate-100">
        {greeting}, <span className="gradient-text capitalize">{displayName}</span> 👋
      </h2>
      <p className="text-sm text-slate-500 mt-0.5">{dateStr}</p>
    </div>
  )
}

export default function DashboardPage() {
  return (
    <div className="p-6 space-y-6">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        <WelcomeHeader />
      </motion.div>

      <motion.div variants={container} initial="hidden" animate="show" className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {STATS.map(({ label, value, trend, icon: Icon, color, bg }) => (
          <motion.div key={label} variants={item}>
            <Card className="card-hover cursor-default">
              <CardContent className="p-5">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">{label}</p>
                  <div className={`rounded-lg p-2 border ${bg}`}>
                    <Icon className={`h-4 w-4 ${color}`} />
                  </div>
                </div>
                <p className="text-2xl font-bold text-slate-100 tabular-nums">{value}</p>
                <p className="text-xs text-slate-500 mt-1"><span className="text-emerald-400">{trend}</span> vs last month</p>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </motion.div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2, duration: 0.4 }} className="xl:col-span-2">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">Recent Sessions</CardTitle>
                <Link href="/dashboard/history">
                  <Button variant="ghost" size="sm" className="text-xs">View all <ArrowRight className="h-3 w-3 ml-1" /></Button>
                </Link>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-[#1e2d4d]">
                {MOCK_SESSIONS.map((session) => (
                  <div key={session.id} className="flex items-center gap-4 px-6 py-3.5 hover:bg-[#141e35] transition-colors">
                    <div className="flex-shrink-0">
                      {session.status === "completed"
                        ? <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                        : <AlertCircle className="h-4 w-4 text-amber-400" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-slate-200">{session.specialty}</span>
                        {getStatusBadge(session.status)}
                      </div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-xs text-slate-500 font-mono">{session.codes.slice(0, 2).join(", ")}</span>
                        <span className="text-[10px] text-slate-600">•</span>
                        <span className="text-xs text-slate-600">{formatDateTime(session.created_at)}</span>
                      </div>
                    </div>
                    <div className="flex-shrink-0 text-xs font-mono font-semibold tabular-nums text-emerald-400">
                      {formatConfidence(session.confidence)}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3, duration: 0.4 }} className="space-y-4">
          <Card className="overflow-hidden">
            <div className="h-1 bg-gradient-to-r from-blue-600 to-indigo-600" />
            <CardContent className="p-5">
              <div className="mb-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/10 border border-blue-500/20 mb-3">
                  <Brain className="h-5 w-5 text-blue-400" />
                </div>
                <h3 className="text-sm font-semibold text-slate-100">Start AI Coding</h3>
                <p className="text-xs text-slate-500 mt-1">Submit a clinical note for automated coding</p>
              </div>
              <Link href="/dashboard/coding">
                <Button variant="gradient" size="sm" className="w-full">New Session <ArrowRight className="h-3.5 w-3.5" /></Button>
              </Link>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3"><CardTitle className="text-sm">System Status</CardTitle></CardHeader>
            <CardContent className="pt-0 space-y-2.5">
              {[
                { label: "AI Engine (GPT-4o)", status: "online" },
                { label: "Knowledge Base", status: "online" },
                { label: "NLP Pipeline", status: "online" },
                { label: "Database", status: "online" },
              ].map(({ label, status }) => (
                <div key={label} className="flex items-center justify-between">
                  <span className="text-xs text-slate-400">{label}</span>
                  <div className="flex items-center gap-1.5">
                    <span className="status-dot online" />
                    <span className="text-xs text-emerald-400 capitalize">{status}</span>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
            <div className="flex items-start gap-3">
              <Clock className="h-4 w-4 text-amber-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-amber-300">14 sessions pending</p>
                <p className="text-xs text-slate-500 mt-0.5">Require human review</p>
                <Link href="/dashboard/review">
                  <button className="text-xs text-amber-400 hover:text-amber-300 mt-2 transition-colors cursor-pointer">Review now →</button>
                </Link>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
