"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  CheckCircle2, XCircle, AlertTriangle, ClipboardCheck,
  Clock, ChevronDown, ChevronUp, User,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { CodeCard } from "@/components/shared/CodeCard"
import { ConfidenceBar } from "@/components/shared/ConfidenceBar"
import { formatDateTime } from "@/lib/utils"

const PENDING_REVIEWS = [
  {
    session_id: "sess_b2c31d45",
    specialty: "internal_medicine",
    document_type: "discharge_summary",
    clinical_text: "65-year-old male admitted for 3 days with community-acquired pneumonia. CXR shows right lower lobe infiltrate. BP 148/92 on admission. Started on azithromycin and ceftriaxone IV. Improved and discharged home with oral antibiotics.",
    codes: [
      { code: "J18.9", code_type: "ICD-10-CM", description: "Pneumonia, unspecified", confidence: 0.78, is_primary: true, evidence: "RLL infiltrate on CXR, clinical diagnosis", modifiers: [], hierarchy: "J18" },
      { code: "I10", code_type: "ICD-10-CM", description: "Essential hypertension", confidence: 0.82, is_primary: false, evidence: "BP 148/92 on admission", modifiers: [], hierarchy: "I10" },
    ],
    requires_human_review: true,
    review_reason: "Confidence below threshold for primary pneumonia code — pathogen not identified",
    processing_time_ms: 4200,
    created_at: new Date(Date.now() - 2 * 3600000).toISOString(),
    priority: "high",
  },
  {
    session_id: "sess_e9f01234",
    specialty: "neurology",
    document_type: "emergency_note",
    clinical_text: "28-year-old female with severe headache, photophobia, nausea for 6 hours. No fever. No meningeal signs. CT head negative. History of migraines, last episode 2 months ago. Given sumatriptan with partial relief.",
    codes: [
      { code: "G43.909", code_type: "ICD-10-CM", description: "Migraine, unspecified, not intractable, without status migrainosus", confidence: 0.65, is_primary: true, evidence: "Severe headache, photophobia, history of migraines", modifiers: [], hierarchy: "G43" },
    ],
    requires_human_review: true,
    review_reason: "Low confidence score (65%) — consider G43.909 vs G43.919",
    processing_time_ms: 5100,
    created_at: new Date(Date.now() - 8 * 3600000).toISOString(),
    priority: "medium",
  },
  {
    session_id: "sess_k3l45678",
    specialty: "gastroenterology",
    document_type: "consultation_note",
    clinical_text: "52-year-old female referred for upper GI bleed. Reports melena x3 days. Hgb 8.2. EGD performed showing gastric ulcer with active oozing. H. pylori testing sent. Treated with hemostatic clips.",
    codes: [
      { code: "K25.4", code_type: "ICD-10-CM", description: "Chronic or unspecified gastric ulcer with hemorrhage", confidence: 0.71, is_primary: true, evidence: "Gastric ulcer with active oozing on EGD", modifiers: [], hierarchy: "K25" },
      { code: "43239", code_type: "CPT", description: "Upper GI endoscopy with ablation", confidence: 0.68, is_primary: false, evidence: "EGD with hemostatic clips applied", modifiers: [], hierarchy: "43239" },
    ],
    requires_human_review: true,
    review_reason: "Multiple code options for hemorrhagic ulcer — verify chronicity and procedure code",
    processing_time_ms: 3800,
    created_at: new Date(Date.now() - 12 * 3600000).toISOString(),
    priority: "high",
  },
]

type ReviewAction = { sessionId: string; action: "approved" | "rejected" }

function PriorityBadge({ priority }: { priority: string }) {
  if (priority === "high") return <Badge variant="danger" className="text-[10px]">High Priority</Badge>
  if (priority === "medium") return <Badge variant="warning" className="text-[10px]">Medium</Badge>
  return <Badge variant="secondary" className="text-[10px]">Low</Badge>
}

function ReviewCard({ session, onAction }: {
  session: typeof PENDING_REVIEWS[0],
  onAction: (action: ReviewAction) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [acting, setActing] = useState(false)
  const avgConf = session.codes.reduce((s, c) => s + c.confidence, 0) / session.codes.length

  const handleAction = async (action: "approved" | "rejected") => {
    setActing(true)
    await new Promise(r => setTimeout(r, 600))
    onAction({ sessionId: session.session_id, action })
  }

  return (
    <Card className="overflow-hidden">
      <div className={`h-1 ${session.priority === "high" ? "bg-red-500" : session.priority === "medium" ? "bg-amber-500" : "bg-blue-500"}`} />
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
              <PriorityBadge priority={session.priority} />
            </div>
            <div className="flex items-center gap-3 mt-1">
              <span className="font-mono text-[10px] text-slate-500">{session.session_id}</span>
              <div className="flex items-center gap-1 text-[10px] text-slate-500">
                <Clock className="h-2.5 w-2.5" />
                {formatDateTime(session.created_at)}
              </div>
            </div>
          </div>
          <ConfidenceBar value={avgConf} size="sm" />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Review reason */}
        <div className="flex items-start gap-2.5 rounded-lg border border-amber-500/20 bg-amber-500/8 px-3 py-2.5">
          <AlertTriangle className="h-3.5 w-3.5 text-amber-400 flex-shrink-0 mt-0.5" />
          <p className="text-xs text-amber-300 leading-relaxed">{session.review_reason}</p>
        </div>

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
              <p className="text-xs text-slate-400 leading-relaxed">{session.clinical_text}</p>
            </div>
          )}
        </div>

        {/* Codes */}
        <div className="space-y-2">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Proposed Codes</p>
          {session.codes.map((code, i) => (
            <CodeCard key={code.code} code={code as Parameters<typeof CodeCard>[0]["code"]} index={i} />
          ))}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3 pt-1">
          <Button
            variant="default"
            size="sm"
            className="flex-1 bg-emerald-600 hover:bg-emerald-500"
            onClick={() => handleAction("approved")}
            disabled={acting}
          >
            <CheckCircle2 className="h-3.5 w-3.5" />
            Approve
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="flex-1 border-red-500/30 text-red-400 hover:bg-red-500/10 hover:text-red-300"
            onClick={() => handleAction("rejected")}
            disabled={acting}
          >
            <XCircle className="h-3.5 w-3.5" />
            Reject
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export default function ReviewPage() {
  const [sessions, setSessions] = useState(PENDING_REVIEWS)
  const [completed, setCompleted] = useState<ReviewAction[]>([])

  const handleAction = (action: ReviewAction) => {
    setSessions((prev) => prev.filter((s) => s.session_id !== action.sessionId))
    setCompleted((prev) => [...prev, action])
  }

  return (
    <div className="p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-100">Review Queue</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            {sessions.length} session{sessions.length !== 1 ? "s" : ""} pending human review
          </p>
        </div>
        {completed.length > 0 && (
          <Badge variant="success" className="text-xs">
            <CheckCircle2 className="h-3 w-3 mr-1" />
            {completed.length} reviewed today
          </Badge>
        )}
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Pending", value: sessions.length, color: "text-amber-400", bg: "bg-amber-500/10 border-amber-500/20" },
          { label: "Approved today", value: completed.filter(c => c.action === "approved").length, color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/20" },
          { label: "Rejected today", value: completed.filter(c => c.action === "rejected").length, color: "text-red-400", bg: "bg-red-500/10 border-red-500/20" },
        ].map(({ label, value, color, bg }) => (
          <div key={label} className={`rounded-xl border p-4 ${bg}`}>
            <p className="text-xs text-slate-500">{label}</p>
            <p className={`text-2xl font-bold tabular-nums mt-1 ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Queue */}
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
            <p className="text-sm text-slate-500 mt-1">No sessions pending review</p>
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
    </div>
  )
}
