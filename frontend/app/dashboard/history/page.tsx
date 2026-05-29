"use client"

import { useState, useEffect, useCallback } from "react"
import { motion } from "framer-motion"
import {
  Search, Filter, ChevronDown, ExternalLink,
  CheckCircle2, AlertCircle, XCircle, Calendar, RefreshCw,
} from "lucide-react"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { ConfidenceBar } from "@/components/shared/ConfidenceBar"
import { CodeCard } from "@/components/shared/CodeCard"
import { formatDateTime } from "@/lib/utils"
import { codingAPI } from "@/lib/api"
import { extractErrorMessage } from "@/lib/errors"
import type { CodingResult } from "@/types"

function StatusIcon({ status }: { status: string }) {
  if (status === "completed" || status === "approved") return <CheckCircle2 className="h-4 w-4 text-emerald-400" />
  if (status === "needs_review") return <AlertCircle className="h-4 w-4 text-amber-400" />
  return <XCircle className="h-4 w-4 text-red-400" />
}

function StatusBadge({ status }: { status: string }) {
  if (status === "completed") return <Badge variant="success">Completed</Badge>
  if (status === "approved") return <Badge variant="success">Approved</Badge>
  if (status === "needs_review") return <Badge variant="warning">Needs Review</Badge>
  if (status === "rejected") return <Badge variant="danger">Rejected</Badge>
  return <Badge variant="secondary">{status}</Badge>
}

function RowSkeleton() {
  return (
    <tr className="border-b border-[#1e2d4d]">
      {[...Array(6)].map((_, i) => (
        <td key={i} className="px-4 py-3.5">
          <Skeleton className="h-4 w-full rounded" />
        </td>
      ))}
    </tr>
  )
}

export default function HistoryPage() {
  const [sessions, setSessions] = useState<CodingResult[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState("all")
  const [specialtyFilter, setSpecialtyFilter] = useState("all")
  const [selectedSession, setSelectedSession] = useState<CodingResult | null>(null)
  const [total, setTotal] = useState(0)

  const fetchSessions = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await codingAPI.getSessions(1, 100, statusFilter === "all" ? undefined : statusFilter)
      setSessions(res.items)
      setTotal(res.total)
    } catch (err) {
      setError(extractErrorMessage(err, "Failed to load sessions. Make sure the backend is running."))
    } finally {
      setLoading(false)
    }
  }, [statusFilter])

  useEffect(() => {
    fetchSessions()
  }, [fetchSessions])

  const filtered = sessions.filter((s) => {
    const matchSearch =
      !search ||
      s.session_id.toLowerCase().includes(search.toLowerCase()) ||
      s.specialty.includes(search.toLowerCase()) ||
      s.codes.some((c) => c.code.toLowerCase().includes(search.toLowerCase()))
    const matchSpecialty = specialtyFilter === "all" || s.specialty === specialtyFilter
    return matchSearch && matchSpecialty
  })

  const specialties = [...new Set(sessions.map((s) => s.specialty))]

  return (
    <div className="p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-100">Coding History</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            {loading ? "Loading..." : `${total} total session${total !== 1 ? "s" : ""} · ${filtered.length} shown`}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchSessions} disabled={loading} className="text-xs">
          <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-xl border border-red-500/25 bg-red-500/10 px-4 py-3">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500 pointer-events-none" />
          <Input
            placeholder="Search by session ID, specialty, or code..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 h-9"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-44 h-9">
            <Filter className="h-3.5 w-3.5 mr-1.5 text-slate-400" />
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="completed">Completed</SelectItem>
            <SelectItem value="needs_review">Needs Review</SelectItem>
            <SelectItem value="approved">Approved</SelectItem>
            <SelectItem value="rejected">Rejected</SelectItem>
          </SelectContent>
        </Select>
        <Select value={specialtyFilter} onValueChange={setSpecialtyFilter}>
          <SelectTrigger className="w-44 h-9">
            <SelectValue placeholder="Specialty" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All specialties</SelectItem>
            {specialties.map((s) => (
              <SelectItem key={s} value={s} className="capitalize">{s.replace(/_/g, " ")}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-[#1e2d4d] overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[#1e2d4d] bg-[#080d1a]">
              <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">Status</th>
              <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">Specialty</th>
              <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">Codes</th>
              <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">Confidence</th>
              <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500">Date</th>
              <th className="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1e2d4d]">
            {loading ? (
              [...Array(5)].map((_, i) => <RowSkeleton key={i} />)
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-16 text-center text-sm text-slate-500">
                  {sessions.length === 0
                    ? "No coding sessions found. Run your first coding session above."
                    : "No sessions match your filters"}
                </td>
              </tr>
            ) : (
              filtered.map((session, i) => {
                const avgConf = session.codes.length > 0
                  ? session.codes.reduce((s, c) => s + c.confidence, 0) / session.codes.length
                  : 0
                return (
                  <motion.tr
                    key={session.session_id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.03 }}
                    className="group hover:bg-[#0f1629] transition-colors cursor-pointer"
                    onClick={() => setSelectedSession(session)}
                  >
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-2">
                        <StatusIcon status={session.status} />
                        <span className="text-xs text-slate-400 capitalize">{session.status.replace(/_/g, " ")}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className="text-sm text-slate-200 capitalize">{session.specialty.replace(/_/g, " ")}</span>
                      <p className="text-[10px] text-slate-500 mt-0.5 capitalize">{session.document_type.replace(/_/g, " ")}</p>
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="flex gap-1 flex-wrap">
                        {session.codes.slice(0, 3).map((c) => (
                          <span key={c.code} className="font-mono text-[10px] rounded bg-[#141e35] border border-[#1e2d4d] px-1.5 py-0.5 text-slate-300">
                            {c.code}
                          </span>
                        ))}
                        {session.codes.length > 3 && (
                          <span className="text-[10px] text-slate-500">+{session.codes.length - 3}</span>
                        )}
                        {session.codes.length === 0 && (
                          <span className="text-[10px] text-slate-600 italic">none</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3.5">
                      {session.codes.length > 0 ? (
                        <ConfidenceBar value={avgConf} size="sm" />
                      ) : (
                        <span className="text-[10px] text-slate-600">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-1.5 text-xs text-slate-400">
                        <Calendar className="h-3 w-3" />
                        {formatDateTime(session.created_at)}
                      </div>
                    </td>
                    <td className="px-4 py-3.5">
                      <ExternalLink className="h-3.5 w-3.5 text-slate-600 group-hover:text-blue-400 transition-colors" />
                    </td>
                  </motion.tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Detail Dialog */}
      <Dialog open={!!selectedSession} onOpenChange={(open) => !open && setSelectedSession(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Session Detail</DialogTitle>
            <DialogDescription className="font-mono text-[11px]">{selectedSession?.session_id}</DialogDescription>
          </DialogHeader>
          {selectedSession && (
            <div className="mt-4 space-y-4">
              <div className="flex items-center gap-3 flex-wrap">
                <StatusBadge status={selectedSession.status} />
                <span className="text-xs text-slate-400 capitalize">{selectedSession.specialty.replace(/_/g, " ")}</span>
                <span className="text-xs text-slate-500 capitalize">{selectedSession.document_type.replace(/_/g, " ")}</span>
                <span className="text-xs text-slate-500">{formatDateTime(selectedSession.created_at)}</span>
              </div>
              {selectedSession.requires_human_review && selectedSession.review_reason && (
                <div className="flex items-start gap-2 rounded-lg border border-amber-500/20 bg-amber-500/8 px-3 py-2.5">
                  <AlertCircle className="h-3.5 w-3.5 text-amber-400 flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-amber-300">{selectedSession.review_reason}</p>
                </div>
              )}
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Assigned Codes ({selectedSession.codes.length})
                </p>
                {selectedSession.codes.length === 0 ? (
                  <p className="text-sm text-slate-500 py-2">No codes were assigned to this session.</p>
                ) : (
                  selectedSession.codes.map((code, i) => (
                    <CodeCard key={code.code} code={code} index={i} />
                  ))
                )}
              </div>
              {selectedSession.summary && (
                <div className="rounded-xl border border-[#1e2d4d] bg-[#0a0f1e] p-4">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">AI Summary</p>
                  <p className="text-sm text-slate-300 leading-relaxed">{selectedSession.summary}</p>
                </div>
              )}
              <div className="rounded-xl border border-[#1e2d4d] bg-[#080d1a] p-4 grid grid-cols-2 gap-3 text-xs">
                <div><span className="text-slate-500">Model</span><p className="text-slate-300 font-mono text-[10px] mt-0.5">{selectedSession.model_used || "—"}</p></div>
                <div><span className="text-slate-500">Processing time</span><p className="text-slate-300 mt-0.5">{selectedSession.processing_time_ms != null ? `${(selectedSession.processing_time_ms / 1000).toFixed(1)}s` : "—"}</p></div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
