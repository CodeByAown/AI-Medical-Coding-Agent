"use client"

import { useState, useEffect, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  CheckCircle2, XCircle, AlertTriangle, ClipboardCheck,
  Clock, ChevronDown, ChevronUp, RefreshCw, Loader2,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { CodeCard } from "@/components/shared/CodeCard"
import { ConfidenceBar } from "@/components/shared/ConfidenceBar"
import { formatDateTime } from "@/lib/utils"
import { codingAPI } from "@/lib/api"
import { extractErrorMessage } from "@/lib/errors"
import type { BackendReviewQueueItem } from "@/types"

type ReviewAction = { sessionId: string; action: "approved" | "rejected" }

function ReviewCard({
  session,
  onAction,
}: {
  session: BackendReviewQueueItem
  onAction: (action: ReviewAction) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [acting, setActing] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const avgConf = session.codes.length > 0
    ? session.codes.reduce((s, c) => s + c.confidence, 0) / session.codes.length
    : 0

  const handleAction = async (action: "approved" | "rejected") => {
    setActing(true)
    setActionError(null)
    try {
      const codesToAct = session.codes.map((c) => c.code)
      await codingAPI.submitReview(session.session_id, action, codesToAct)
      onAction({ sessionId: session.session_id, action })
    } catch (err) {
      setActionError(extractErrorMessage(err, "Failed to submit review. Please try again."))
      setActing(false)
    }
  }

  return (
    <Card className="overflow-hidden">
      <div className="h-1 bg-amber-500" />
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-semibold text-slate-200 capitalize">
                {session.specialty.replace(/_/g, " ")}
              </span>
              <span className="text-[10px] text-slate-500 capitalize">
                {session.document_type.replace(/_/g, " ")}
              </span>
              <Badge variant="warning" className="text-[10px]">Pending Review</Badge>
            </div>
            <div className="flex items-center gap-3 mt-1">
              <span className="font-mono text-[10px] text-slate-500 truncate max-w-[180px]">{session.session_id}</span>
              <div className="flex items-center gap-1 text-[10px] text-slate-500">
                <Clock className="h-2.5 w-2.5" />
                {formatDateTime(session.created_at)}
              </div>
            </div>
          </div>
          {session.codes.length > 0 && <ConfidenceBar value={avgConf} size="sm" />}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Review reason */}
        {session.review_reason && (
          <div className="flex items-start gap-2.5 rounded-lg border border-amber-500/20 bg-amber-500/8 px-3 py-2.5">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-400 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-amber-300 leading-relaxed">{session.review_reason}</p>
          </div>
        )}

        {/* Clinical text preview */}
        <div>
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors cursor-pointer mb-2"
          >
            {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            Clinical text preview
          </button>
          {expanded && (
            <div className="rounded-lg bg-[#080d1a] border border-[#1e2d4d] px-3 py-2.5">
              <p className="text-xs text-slate-400 leading-relaxed">{session.clinical_text_preview}</p>
            </div>
          )}
        </div>

        {/* Codes */}
        <div className="space-y-2">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            Proposed Codes ({session.codes.length})
          </p>
          {session.codes.length === 0 ? (
            <p className="text-xs text-slate-500 italic">No codes assigned — review required</p>
          ) : (
            session.codes.map((code, i) => (
              <CodeCard key={code.code} code={code} index={i} />
            ))
          )}
        </div>

        {/* Action error */}
        {actionError && (
          <p className="text-xs text-red-400 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2">{actionError}</p>
        )}

        {/* Actions */}
        <div className="flex items-center gap-3 pt-1">
          <Button
            variant="default"
            size="sm"
            className="flex-1 bg-emerald-600 hover:bg-emerald-500"
            onClick={() => handleAction("approved")}
            disabled={acting}
          >
            {acting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
            Approve All
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="flex-1 border-red-500/30 text-red-400 hover:bg-red-500/10 hover:text-red-300"
            onClick={() => handleAction("rejected")}
            disabled={acting}
          >
            {acting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <XCircle className="h-3.5 w-3.5" />}
            Reject
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

function CardSkeleton() {
  return (
    <Card className="overflow-hidden">
      <div className="h-1 bg-[#1e2d4d]" />
      <CardHeader className="pb-3">
        <Skeleton className="h-4 w-48 rounded" />
        <Skeleton className="h-3 w-32 rounded mt-2" />
      </CardHeader>
      <CardContent className="space-y-3">
        <Skeleton className="h-12 rounded-lg" />
        <Skeleton className="h-16 rounded-xl" />
        <div className="flex gap-3">
          <Skeleton className="h-8 flex-1 rounded-lg" />
          <Skeleton className="h-8 flex-1 rounded-lg" />
        </div>
      </CardContent>
    </Card>
  )
}

export default function ReviewPage() {
  const [sessions, setSessions] = useState<BackendReviewQueueItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [completed, setCompleted] = useState<ReviewAction[]>([])

  const fetchQueue = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await codingAPI.getReviewQueue(1, 50)
      setSessions(res.items)
    } catch (err) {
      setError(extractErrorMessage(err, "Failed to load review queue. Make sure the backend is running."))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchQueue()
  }, [fetchQueue])

  const handleAction = (action: ReviewAction) => {
    setSessions((prev) => prev.filter((s) => s.session_id !== action.sessionId))
    setCompleted((prev) => [...prev, action])
  }

  const pendingCount = sessions.length

  return (
    <div className="p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-100">Review Queue</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            {loading ? "Loading..." : `${pendingCount} session${pendingCount !== 1 ? "s" : ""} pending human review`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {completed.length > 0 && (
            <Badge variant="success" className="text-xs">
              <CheckCircle2 className="h-3 w-3 mr-1" />
              {completed.length} reviewed
            </Badge>
          )}
          <Button variant="outline" size="sm" onClick={fetchQueue} disabled={loading} className="text-xs">
            <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-xl border border-red-500/25 bg-red-500/10 px-4 py-3">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Pending", value: loading ? "…" : pendingCount, color: "text-amber-400", bg: "bg-amber-500/10 border-amber-500/20" },
          { label: "Approved", value: completed.filter(c => c.action === "approved").length, color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/20" },
          { label: "Rejected", value: completed.filter(c => c.action === "rejected").length, color: "text-red-400", bg: "bg-red-500/10 border-red-500/20" },
        ].map(({ label, value, color, bg }) => (
          <div key={label} className={`rounded-xl border p-4 ${bg}`}>
            <p className="text-xs text-slate-500">{label}</p>
            <p className={`text-2xl font-bold tabular-nums mt-1 ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Queue */}
      {loading ? (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
          {[...Array(2)].map((_, i) => <CardSkeleton key={i} />)}
        </div>
      ) : (
        <AnimatePresence mode="popLayout">
          {sessions.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex flex-col items-center justify-center py-20 text-center"
            >
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-500/10 border border-emerald-500/20 mb-4">
                <ClipboardCheck className="h-8 w-8 text-emerald-400" />
              </div>
              <h3 className="text-base font-semibold text-slate-200">All caught up!</h3>
              <p className="text-sm text-slate-500 mt-1">
                {completed.length > 0
                  ? `You reviewed ${completed.length} session${completed.length !== 1 ? "s" : ""} this session.`
                  : "No sessions currently pending review."}
              </p>
            </motion.div>
          ) : (
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
              {sessions.map((session) => (
                <motion.div
                  key={session.session_id}
                  layout
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.2 } }}
                >
                  <ReviewCard session={session} onAction={handleAction} />
                </motion.div>
              ))}
            </div>
          )}
        </AnimatePresence>
      )}
    </div>
  )
}
