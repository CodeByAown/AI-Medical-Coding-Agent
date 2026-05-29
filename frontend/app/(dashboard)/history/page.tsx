"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import {
  Search, Filter, ChevronDown, ExternalLink,
  CheckCircle2, AlertCircle, XCircle, Calendar, Hash,
} from "lucide-react"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { ConfidenceBar } from "@/components/shared/ConfidenceBar"
import { CodeCard } from "@/components/shared/CodeCard"
import { formatDateTime, formatConfidence } from "@/lib/utils"
import type { CodingResult, MedicalCode } from "@/types"

// Rich mock data
const MOCK_HISTORY: (CodingResult & { id: string })[] = [
  {
    id: "1", session_id: "sess_9a998d90", status: "completed", specialty: "cardiology", document_type: "progress_note",
    codes: [
      { code: "I50.22", code_type: "ICD-10-CM", description: "Chronic systolic HF, acute-on-chronic", confidence: 0.95, is_primary: true, evidence: "EF 35%, dilated LV", modifiers: [], hierarchy: "I50" },
      { code: "E11.9", code_type: "ICD-10-CM", description: "Type 2 diabetes without complications", confidence: 0.91, is_primary: false, evidence: "10-year DM2 history", modifiers: [], hierarchy: "E11" },
    ],
    extracted_entities: [], soap_sections: null, summary: "HFrEF with comorbid DM2 and HTN", requires_human_review: false, review_reason: null,
    processing_time_ms: 3976, model_used: "openai/gpt-4o", created_at: new Date(Date.now() - 25 * 60000).toISOString(),
  },
  {
    id: "2", session_id: "sess_b2c31d45", status: "needs_review", specialty: "internal_medicine", document_type: "discharge_summary",
    codes: [
      { code: "J18.9", code_type: "ICD-10-CM", description: "Pneumonia, unspecified", confidence: 0.78, is_primary: true, evidence: "RLL infiltrate on CXR", modifiers: [], hierarchy: "J18" },
      { code: "I10", code_type: "ICD-10-CM", description: "Essential hypertension", confidence: 0.82, is_primary: false, evidence: "BP 148/92", modifiers: [], hierarchy: "I10" },
    ],
    extracted_entities: [], soap_sections: null, summary: "CAP with comorbid hypertension", requires_human_review: true, review_reason: "Confidence below threshold for primary code",
    processing_time_ms: 4200, model_used: "openai/gpt-4o", created_at: new Date(Date.now() - 2 * 3600000).toISOString(),
  },
  {
    id: "3", session_id: "sess_c4f56e78", status: "completed", specialty: "pulmonology", document_type: "progress_note",
    codes: [
      { code: "J44.1", code_type: "ICD-10-CM", description: "COPD with acute exacerbation", confidence: 0.92, is_primary: true, evidence: "COPD exacerbation, wheezing", modifiers: [], hierarchy: "J44" },
      { code: "J45.41", code_type: "ICD-10-CM", description: "Moderate persistent asthma", confidence: 0.86, is_primary: false, evidence: "History of asthma", modifiers: [], hierarchy: "J45" },
    ],
    extracted_entities: [], soap_sections: null, summary: "COPD exacerbation with asthma", requires_human_review: false, review_reason: null,
    processing_time_ms: 3100, model_used: "openai/gpt-4o", created_at: new Date(Date.now() - 4 * 3600000).toISOString(),
  },
  {
    id: "4", session_id: "sess_d7e89012", status: "completed", specialty: "endocrinology", document_type: "consultation_note",
    codes: [
      { code: "E11.65", code_type: "ICD-10-CM", description: "T2DM with hyperglycemia", confidence: 0.94, is_primary: true, evidence: "DM2, hyperglycemic", modifiers: [], hierarchy: "E11" },
      { code: "E78.5", code_type: "ICD-10-CM", description: "Hyperlipidemia, unspecified", confidence: 0.89, is_primary: false, evidence: "Elevated LDL on labs", modifiers: [], hierarchy: "E78" },
    ],
    extracted_entities: [], soap_sections: null, summary: "DM2 with hyperlipidemia", requires_human_review: false, review_reason: null,
    processing_time_ms: 2850, model_used: "openai/gpt-4o", created_at: new Date(Date.now() - 6 * 3600000).toISOString(),
  },
  {
    id: "5", session_id: "sess_e9f01234", status: "needs_review", specialty: "neurology", document_type: "emergency_note",
    codes: [
      { code: "G43.909", code_type: "ICD-10-CM", description: "Migraine, unspecified, not intractable", confidence: 0.65, is_primary: true, evidence: "Severe headache, photophobia", modifiers: [], hierarchy: "G43" },
    ],
    extracted_entities: [], soap_sections: null, summary: "Migraine without aura", requires_human_review: true, review_reason: "Low confidence score",
    processing_time_ms: 5100, model_used: "openai/gpt-4o", created_at: new Date(Date.now() - 8 * 3600000).toISOString(),
  },
  {
    id: "6", session_id: "sess_f1234567", status: "completed", specialty: "orthopedics", document_type: "operative_note",
    codes: [
      { code: "M17.11", code_type: "ICD-10-CM", description: "Primary osteoarthritis, right knee", confidence: 0.97, is_primary: true, evidence: "Severe OA, TKA performed", modifiers: [], hierarchy: "M17" },
      { code: "27447", code_type: "CPT", description: "Total knee arthroplasty", confidence: 0.96, is_primary: false, evidence: "TKA procedure performed", modifiers: [], hierarchy: "27447" },
    ],
    extracted_entities: [], soap_sections: null, summary: "TKA for right knee OA", requires_human_review: false, review_reason: null,
    processing_time_ms: 3300, model_used: "openai/gpt-4o", created_at: new Date(Date.now() - 24 * 3600000).toISOString(),
  },
]

function StatusIcon({ status }: { status: string }) {
  if (status === "completed") return <CheckCircle2 className="h-4 w-4 text-emerald-400" />
  if (status === "needs_review") return <AlertCircle className="h-4 w-4 text-amber-400" />
  return <XCircle className="h-4 w-4 text-red-400" />
}

export default function HistoryPage() {
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState("all")
  const [specialtyFilter, setSpecialtyFilter] = useState("all")
  const [selectedSession, setSelectedSession] = useState<(typeof MOCK_HISTORY)[0] | null>(null)

  const filtered = MOCK_HISTORY.filter((s) => {
    const matchSearch =
      !search ||
      s.session_id.includes(search) ||
      s.specialty.includes(search.toLowerCase()) ||
      s.codes.some((c) => c.code.toLowerCase().includes(search.toLowerCase()))
    const matchStatus = statusFilter === "all" || s.status === statusFilter
    const matchSpecialty = specialtyFilter === "all" || s.specialty === specialtyFilter
    return matchSearch && matchStatus && matchSpecialty
  })

  const specialties = [...new Set(MOCK_HISTORY.map((s) => s.specialty))]

  return (
    <div className="p-6 space-y-5">
      {/* Header */}
      <div>
        <h2 className="text-lg font-semibold text-slate-100">Coding History</h2>
        <p className="text-sm text-slate-500 mt-0.5">{MOCK_HISTORY.length} total sessions</p>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500 pointer-events-none" />
          <Input
            placeholder="Search sessions, codes..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 h-9"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-40 h-9">
            <Filter className="h-3.5 w-3.5 mr-1.5 text-slate-400" />
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="completed">Completed</SelectItem>
            <SelectItem value="needs_review">Needs Review</SelectItem>
            <SelectItem value="failed">Failed</SelectItem>
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
            {filtered.map((session, i) => {
              const avgConf = session.codes.reduce((s, c) => s + c.confidence, 0) / (session.codes.length || 1)
              return (
                <motion.tr
                  key={session.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.04 }}
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
                    </div>
                  </td>
                  <td className="px-4 py-3.5">
                    <ConfidenceBar value={avgConf} size="sm" />
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
            })}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="py-16 text-center text-sm text-slate-500">No sessions match your filters</div>
        )}
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
                <Badge variant={selectedSession.status === "completed" ? "success" : "warning"}>
                  {selectedSession.status.replace(/_/g, " ")}
                </Badge>
                <span className="text-xs text-slate-400 capitalize">{selectedSession.specialty.replace(/_/g, " ")}</span>
                <span className="text-xs text-slate-500">{formatDateTime(selectedSession.created_at)}</span>
              </div>
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Assigned Codes</p>
                {selectedSession.codes.map((code, i) => (
                  <CodeCard key={code.code} code={code} index={i} />
                ))}
              </div>
              {selectedSession.summary && (
                <div className="rounded-xl border border-[#1e2d4d] bg-[#0a0f1e] p-4">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Summary</p>
                  <p className="text-sm text-slate-300 leading-relaxed">{selectedSession.summary}</p>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
