"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  Brain, Sparkles, Loader2, ChevronDown, ChevronUp,
  Copy, AlertTriangle, CheckCircle2, Clock, Cpu, FileText,
  User, Hash,
} from "lucide-react"
import { codingAPI } from "@/lib/api"
import type { CodingResult, DocumentType, Specialty } from "@/types"
import { DOCUMENT_TYPE_LABELS, SPECIALTY_LABELS } from "@/types"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { CodeCard } from "@/components/shared/CodeCard"
import { ConfidenceBar } from "@/components/shared/ConfidenceBar"

const SAMPLE_NOTE = `S: 58-year-old male with a 10-year history of type 2 diabetes mellitus presents with 2-week history of worsening shortness of breath and bilateral leg swelling. Also reports chest tightness on exertion. Current medications: metformin 1000mg BID, lisinopril 10mg daily.

O: BP 158/96, HR 88, RR 18, O2 Sat 94% on room air, Weight 102kg.
Cardiovascular: JVD present, bilateral pitting edema 2+ to knees.
Chest: Bilateral basilar crackles.
ECG: Normal sinus rhythm with left ventricular hypertrophy pattern.
BNP: 850 pg/mL (elevated).
Echo: EF 35%, dilated left ventricle.

A: 1. Congestive heart failure with reduced ejection fraction (HFrEF)
   2. Type 2 diabetes mellitus, uncontrolled
   3. Essential hypertension, not adequately controlled
   4. Bilateral lower extremity edema secondary to CHF

P: 1. Initiate furosemide 40mg daily for diuresis
   2. Add carvedilol 3.125mg BID for CHF management
   3. Cardiology consult requested
   4. Adjust lisinopril to 20mg daily
   5. Continue metformin, add HbA1c check in 3 months
   6. Daily weight monitoring, restrict fluid intake to 1.5L/day
   7. Follow-up in 2 weeks`

function ProcessingAnimation() {
  return (
    <div className="flex flex-col items-center justify-center py-16 space-y-6">
      <div className="relative">
        <div className="h-20 w-20 rounded-full border-2 border-[#1e2d4d]" />
        <div className="absolute inset-0 h-20 w-20 rounded-full border-2 border-t-blue-500 border-r-indigo-500 animate-spin" />
        <div className="absolute inset-3 flex items-center justify-center">
          <Brain className="h-8 w-8 text-blue-400" />
        </div>
      </div>
      <div className="text-center space-y-1">
        <p className="text-base font-semibold text-slate-200">AI is analyzing your note</p>
        <p className="text-sm text-slate-500 loading-dots">Processing</p>
      </div>
      <div className="flex flex-col gap-2 w-64">
        {["Extracting clinical entities", "Searching 74,260 ICD-10 codes", "Applying coding rules", "Validating assignments"].map((step, i) => (
          <motion.div
            key={step}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.4, duration: 0.3 }}
            className="flex items-center gap-2"
          >
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: i * 0.4 + 0.1 }}
              className="h-1.5 w-1.5 rounded-full bg-blue-500"
            />
            <span className="text-xs text-slate-400">{step}</span>
          </motion.div>
        ))}
      </div>
    </div>
  )
}

function ResultsPanel({ result }: { result: CodingResult }) {
  const icd10 = result.codes.filter(c => c.code_type.toUpperCase().includes("ICD"))
  const cpt = result.codes.filter(c => c.code_type.toUpperCase().includes("CPT"))
  const hcpcs = result.codes.filter(c => c.code_type.toUpperCase().includes("HCPCS"))
  const avgConf = result.codes.length > 0
    ? result.codes.reduce((s, c) => s + c.confidence, 0) / result.codes.length
    : 0

  const copyToClipboard = () => {
    const text = result.codes.map(c => `${c.code} - ${c.description}`).join("\n")
    navigator.clipboard.writeText(text)
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="flex flex-col h-full"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-5 w-5 text-emerald-400" />
          <h3 className="text-sm font-semibold text-slate-100">Coding Results</h3>
        </div>
        <Button variant="outline" size="sm" onClick={copyToClipboard} className="text-xs">
          <Copy className="h-3 w-3" /> Copy codes
        </Button>
      </div>

      {/* Meta row */}
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <div className="flex items-center gap-1.5 rounded-lg bg-[#0a0f1e] border border-[#1e2d4d] px-2.5 py-1.5">
          <Badge variant={result.status === "completed" ? "success" : "warning"} className="text-[10px]">
            {result.status === "completed" ? "Completed" : "Needs Review"}
          </Badge>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <Clock className="h-3 w-3" />
          {(result.processing_time_ms / 1000).toFixed(1)}s
        </div>
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <Cpu className="h-3 w-3" />
          {result.model_used?.split("/").pop()}
        </div>
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          Avg confidence:
          <ConfidenceBar value={avgConf} size="sm" showLabel />
        </div>
      </div>

      {/* Requires review warning */}
      {result.requires_human_review && (
        <div className="mb-4 flex items-start gap-2.5 rounded-xl border border-amber-500/25 bg-amber-500/8 px-4 py-3">
          <AlertTriangle className="h-4 w-4 text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-amber-300">Human review required</p>
            {result.review_reason && <p className="text-xs text-slate-400 mt-0.5">{result.review_reason}</p>}
          </div>
        </div>
      )}

      {/* Tabs */}
      <Tabs defaultValue="icd10" className="flex-1 flex flex-col min-h-0">
        <TabsList className="flex-shrink-0">
          <TabsTrigger value="icd10">
            ICD-10
            {icd10.length > 0 && <span className="ml-1.5 rounded bg-blue-500/20 px-1.5 py-0.5 text-[10px] text-blue-400">{icd10.length}</span>}
          </TabsTrigger>
          <TabsTrigger value="cpt">
            CPT
            {cpt.length > 0 && <span className="ml-1.5 rounded bg-emerald-500/20 px-1.5 py-0.5 text-[10px] text-emerald-400">{cpt.length}</span>}
          </TabsTrigger>
          <TabsTrigger value="hcpcs">
            HCPCS
            {hcpcs.length > 0 && <span className="ml-1.5 rounded bg-purple-500/20 px-1.5 py-0.5 text-[10px] text-purple-400">{hcpcs.length}</span>}
          </TabsTrigger>
          <TabsTrigger value="soap">SOAP</TabsTrigger>
          <TabsTrigger value="summary">Summary</TabsTrigger>
        </TabsList>

        <div className="flex-1 overflow-y-auto mt-3 space-y-2 pr-1">
          <TabsContent value="icd10" className="m-0 space-y-2">
            {icd10.length === 0
              ? <p className="text-sm text-slate-500 py-8 text-center">No ICD-10 codes assigned</p>
              : icd10.map((code, i) => <CodeCard key={code.code} code={code} index={i} />)}
          </TabsContent>

          <TabsContent value="cpt" className="m-0 space-y-2">
            {cpt.length === 0
              ? <p className="text-sm text-slate-500 py-8 text-center">No CPT codes assigned</p>
              : cpt.map((code, i) => <CodeCard key={code.code} code={code} index={i} />)}
          </TabsContent>

          <TabsContent value="hcpcs" className="m-0 space-y-2">
            {hcpcs.length === 0
              ? <p className="text-sm text-slate-500 py-8 text-center">No HCPCS codes assigned</p>
              : hcpcs.map((code, i) => <CodeCard key={code.code} code={code} index={i} />)}
          </TabsContent>

          <TabsContent value="soap" className="m-0">
            {result.soap_sections ? (
              <div className="space-y-3">
                {(["subjective", "objective", "assessment", "plan"] as const).map((section) => {
                  const text = result.soap_sections?.[section]
                  if (!text) return null
                  return (
                    <div key={section} className="rounded-xl border border-[#1e2d4d] bg-[#0a0f1e] p-4">
                      <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-500 mb-2">
                        {section}
                      </p>
                      <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">{text}</p>
                    </div>
                  )
                })}
              </div>
            ) : (
              <p className="text-sm text-slate-500 py-8 text-center">No SOAP sections detected</p>
            )}
          </TabsContent>

          <TabsContent value="summary" className="m-0">
            <div className="rounded-xl border border-[#1e2d4d] bg-[#0a0f1e] p-4">
              <p className="text-sm text-slate-300 leading-relaxed">{result.summary || "No summary available."}</p>
              <div className="mt-4 pt-4 border-t border-[#1e2d4d] grid grid-cols-2 gap-3 text-xs text-slate-500">
                <div><span className="text-slate-400">Session ID</span><p className="font-mono text-[10px] mt-0.5 truncate">{result.session_id}</p></div>
                <div><span className="text-slate-400">Specialty</span><p className="capitalize mt-0.5">{result.specialty.replace(/_/g, " ")}</p></div>
                <div><span className="text-slate-400">Document Type</span><p className="capitalize mt-0.5">{result.document_type.replace(/_/g, " ")}</p></div>
                <div><span className="text-slate-400">Total Codes</span><p className="mt-0.5">{result.codes.length}</p></div>
              </div>
            </div>
          </TabsContent>
        </div>
      </Tabs>
    </motion.div>
  )
}

export default function CodingPage() {
  const [text, setText] = useState("")
  const [documentType, setDocumentType] = useState<DocumentType>("progress_note")
  const [specialty, setSpecialty] = useState<Specialty>("internal_medicine")
  const [patientId, setPatientId] = useState("")
  const [encounterId, setEncounterId] = useState("")
  const [showOptional, setShowOptional] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [result, setResult] = useState<CodingResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async () => {
    if (!text.trim()) return
    setIsProcessing(true)
    setError(null)
    setResult(null)
    try {
      const res = await codingAPI.submitNote(text, documentType, specialty, patientId || undefined, encounterId || undefined)
      setResult(res)
    } catch (err: unknown) {
      setError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Coding failed. Please check that the backend is running."
      )
    } finally {
      setIsProcessing(false)
    }
  }

  return (
    <div className="flex h-full">
      {/* Left: Editor panel */}
      <div className={`flex flex-col border-r border-[#1e2d4d] transition-all duration-300 ${result || isProcessing ? "w-1/2" : "w-full max-w-3xl mx-auto"}`}>
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* Header */}
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Brain className="h-5 w-5 text-blue-400" />
              <h2 className="text-base font-semibold text-slate-100">AI Coding Workspace</h2>
            </div>
            <p className="text-xs text-slate-500">Paste a clinical note to generate ICD-10, CPT, and HCPCS codes automatically</p>
          </div>

          {/* Selectors row */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Document Type</Label>
              <Select value={documentType} onValueChange={(v) => setDocumentType(v as DocumentType)}>
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(Object.entries(DOCUMENT_TYPE_LABELS) as [DocumentType, string][]).map(([value, label]) => (
                    <SelectItem key={value} value={value} className="text-xs">{label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Specialty</Label>
              <Select value={specialty} onValueChange={(v) => setSpecialty(v as Specialty)}>
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(Object.entries(SPECIALTY_LABELS) as [Specialty, string][]).map(([value, label]) => (
                    <SelectItem key={value} value={value} className="text-xs">{label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Optional fields */}
          <div>
            <button
              onClick={() => setShowOptional(!showOptional)}
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors cursor-pointer"
            >
              {showOptional ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              Optional identifiers
            </button>
            {showOptional && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                className="mt-3 grid grid-cols-2 gap-3"
              >
                <div className="space-y-1.5">
                  <Label className="text-xs flex items-center gap-1"><User className="h-3 w-3" />Patient ID</Label>
                  <Input className="h-8 text-xs" placeholder="PT-001234" value={patientId} onChange={(e) => setPatientId(e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs flex items-center gap-1"><Hash className="h-3 w-3" />Encounter ID</Label>
                  <Input className="h-8 text-xs" placeholder="ENC-567890" value={encounterId} onChange={(e) => setEncounterId(e.target.value)} />
                </div>
              </motion.div>
            )}
          </div>

          {/* Clinical note editor */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <Label className="flex items-center gap-1.5"><FileText className="h-3.5 w-3.5" />Clinical Note</Label>
              {!text && (
                <button
                  onClick={() => setText(SAMPLE_NOTE)}
                  className="text-xs text-blue-400 hover:text-blue-300 transition-colors cursor-pointer"
                >
                  Load sample note
                </button>
              )}
            </div>
            <Textarea
              placeholder="Paste your SOAP note, discharge summary, or clinical note here..."
              value={text}
              onChange={(e) => setText(e.target.value)}
              className="min-h-[320px] font-mono text-xs leading-relaxed resize-none"
            />
            <p className="text-[10px] text-slate-600 text-right">{text.length} characters</p>
          </div>

          {error && (
            <div className="flex items-center gap-2 rounded-xl border border-red-500/25 bg-red-500/10 px-4 py-3">
              <AlertTriangle className="h-4 w-4 text-red-400 flex-shrink-0" />
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}
        </div>

        {/* Submit button */}
        <div className="flex-shrink-0 border-t border-[#1e2d4d] p-4">
          <Button
            variant="gradient"
            size="lg"
            className="w-full relative overflow-hidden group"
            onClick={handleSubmit}
            disabled={isProcessing || !text.trim()}
          >
            {isProcessing ? (
              <><Loader2 className="h-4 w-4 animate-spin" />Processing...</>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Run AI Coding
                <span className="ml-auto opacity-60 text-xs group-hover:opacity-100 transition-opacity">→</span>
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Right: Results panel */}
      <AnimatePresence>
        {(result || isProcessing) && (
          <motion.div
            initial={{ opacity: 0, width: 0 }}
            animate={{ opacity: 1, width: "50%" }}
            exit={{ opacity: 0, width: 0 }}
            className="flex flex-col overflow-hidden"
          >
            <div className="flex-1 overflow-hidden p-6">
              {isProcessing ? (
                <ProcessingAnimation />
              ) : result ? (
                <ResultsPanel result={result} />
              ) : null}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
