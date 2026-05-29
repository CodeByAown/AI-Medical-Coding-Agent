// ============================================================
// Neural Hub — TypeScript Type Definitions
// ============================================================

// Auth Types
export interface LoginResponse {
  access_token: string
  token_type: string
  refresh_token?: string
  user_id: string
  email: string
  role: string
}

export interface User {
  user_id: string
  email: string
  role: UserRole
  full_name?: string
}

export type UserRole = "coder" | "reviewer" | "auditor" | "admin"

export interface RegisterRequest {
  email: string
  password: string
  full_name: string
  role?: UserRole
}

// Medical Code Types
export type CodeType = "ICD-10" | "CPT" | "HCPCS" | "ICD-10-CM" | "ICD-10-PCS"

export interface MedicalCode {
  code: string
  code_type: CodeType
  description: string
  confidence: number
  is_primary: boolean
  evidence: string
  modifiers?: string[]
  hierarchy?: string
}

// Entity Types
export type EntityType =
  | "DIAGNOSIS"
  | "PROCEDURE"
  | "MEDICATION"
  | "ANATOMY"
  | "SYMPTOM"
  | "LAB_VALUE"
  | "VITAL_SIGN"
  | "CONDITION"

export interface ExtractedEntity {
  text: string
  entity_type: EntityType
  confidence: number
  umls_cui?: string
  umls_name?: string
}

// SOAP Sections
export interface SOAPSections {
  subjective?: string
  objective?: string
  assessment?: string
  plan?: string
  raw_text: string
}

// Coding Session Types
export type SessionStatus = "completed" | "needs_review" | "approved" | "rejected" | "failed" | "processing" | "error"

export interface CodingResult {
  session_id: string
  status: SessionStatus
  codes: MedicalCode[]
  extracted_entities: ExtractedEntity[]
  soap_sections: SOAPSections | null
  specialty: string
  document_type: string
  summary: string
  requires_human_review: boolean
  review_reason: string | null
  processing_time_ms: number
  model_used: string
  created_at: string
}

// Coding Request
export interface CodingRequest {
  text: string
  document_type: DocumentType
  specialty: Specialty
  patient_id?: string
  encounter_id?: string
  include_hcpcs?: boolean
}

// Document types — must exactly match backend DocumentType enum values
export type DocumentType =
  | "clinical_note"
  | "soap_note"
  | "progress_note"
  | "discharge_summary"
  | "operative_note"
  | "consultation_note"
  | "emergency_note"
  | "history_physical"
  | "radiology_report"
  | "pathology_report"
  | "lab_report"
  | "nursing_note"

// Specialties — must exactly match backend Specialty enum values
export type Specialty =
  | "general"
  | "internal_medicine"
  | "cardiology"
  | "pulmonology"
  | "neurology"
  | "orthopedics"
  | "gastroenterology"
  | "nephrology"
  | "endocrinology"
  | "oncology"
  | "psychiatry"
  | "emergency"
  | "emergency_medicine"
  | "surgery"
  | "obstetrics"
  | "obstetrics_gynecology"
  | "pediatrics"
  | "dermatology"
  | "ophthalmology"
  | "urology"
  | "rheumatology"
  | "infectious_disease"
  | "radiology"

// Review Types — what the UI uses
export type ReviewDecision = "approved" | "rejected"

export interface ReviewRequest {
  decision: ReviewDecision
  notes?: string
  modified_codes?: MedicalCode[]
}

// What the backend returns in the review queue
export interface BackendReviewQueueItem {
  session_id: string
  status: SessionStatus
  codes: MedicalCode[]
  clinical_text_preview: string
  specialty: string
  document_type: string
  created_at: string
  review_reason: string | null
  requires_human_review: boolean
  processing_time_ms: number | null
}

// Search Types
export interface CodeSearchResult {
  code: string
  code_type: CodeType
  description: string
  category?: string
  relevance_score?: number
}

// API Response Types
export interface ApiError {
  detail: string
  status_code?: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

// Health Check
export interface HealthStatus {
  status: "healthy" | "degraded" | "unhealthy"
  version?: string
  services?: {
    llm?: "up" | "down"
    knowledge_base?: "up" | "down"
    nlp?: "up" | "down"
    database?: "up" | "down"
  }
  timestamp?: string
}

// Dashboard Stats
export interface DashboardStats {
  total_sessions: number
  sessions_trend: number
  avg_confidence: number
  pending_reviews: number
  codes_this_month: number
  monthly_trend: number
}

// History Session (for display)
export interface HistorySession {
  session_id: string
  specialty: string
  document_type: DocumentType
  status: SessionStatus
  codes_count: number
  avg_confidence: number
  created_at: string
  primary_diagnosis?: string
}

// Document type display names — aligned with backend enum values
export const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  clinical_note: "Clinical Note",
  soap_note: "SOAP Note",
  progress_note: "Progress Note",
  discharge_summary: "Discharge Summary",
  operative_note: "Operative Note",
  consultation_note: "Consultation Note",
  emergency_note: "Emergency Note",
  history_physical: "History & Physical",
  radiology_report: "Radiology Report",
  pathology_report: "Pathology Report",
  lab_report: "Lab Report",
  nursing_note: "Nursing Note",
}

// Specialty display names — aligned with backend enum values
export const SPECIALTY_LABELS: Record<Specialty, string> = {
  general: "General",
  internal_medicine: "Internal Medicine",
  cardiology: "Cardiology",
  pulmonology: "Pulmonology",
  neurology: "Neurology",
  orthopedics: "Orthopedics",
  gastroenterology: "Gastroenterology",
  nephrology: "Nephrology",
  endocrinology: "Endocrinology",
  oncology: "Oncology",
  psychiatry: "Psychiatry",
  emergency: "Emergency",
  emergency_medicine: "Emergency Medicine",
  surgery: "Surgery",
  obstetrics: "Obstetrics",
  obstetrics_gynecology: "OB/GYN",
  pediatrics: "Pediatrics",
  dermatology: "Dermatology",
  ophthalmology: "Ophthalmology",
  urology: "Urology",
  rheumatology: "Rheumatology",
  infectious_disease: "Infectious Disease",
  radiology: "Radiology",
}
