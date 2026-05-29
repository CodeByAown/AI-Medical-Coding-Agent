// ============================================================
// Neural Hub — Axios API Client
// ============================================================
import axios, { type AxiosInstance } from "axios"
import { getToken, clearAuth } from "@/lib/auth"
import type {
  LoginResponse,
  CodingResult,
  CodingRequest,
  CodeSearchResult,
  BackendReviewQueueItem,
  HealthStatus,
  RegisterRequest,
  DocumentType,
  Specialty,
  PaginatedResponse,
} from "@/types"

// ── Axios instance ─────────────────────────────────────────
// NEXT_PUBLIC_API_URL is set at build time for Railway/production.
// Falls back to localhost:8000 for local development.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 60000,
})

// Request interceptor: attach Bearer token
api.interceptors.request.use(
  (config) => {
    const token = getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor: handle 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearAuth()
      if (typeof window !== "undefined") {
        window.location.href = "/login"
      }
    }
    return Promise.reject(error)
  }
)

// ── Auth API ───────────────────────────────────────────────
export const authAPI = {
  async login(email: string, password: string): Promise<LoginResponse> {
    const formData = new URLSearchParams()
    formData.append("username", email)
    formData.append("password", password)
    const response = await api.post<LoginResponse>("/api/v1/auth/token", formData, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    })
    return response.data
  },

  async register(
    email: string,
    password: string,
    fullName: string,
    role: string = "coder"
  ): Promise<{ id: string; email: string; role: string }> {
    const payload: RegisterRequest = { email, password, full_name: fullName, role: role as RegisterRequest["role"] }
    const response = await api.post("/api/v1/auth/users", payload)
    return response.data
  },
}

// ── Coding API ─────────────────────────────────────────────
export const codingAPI = {
  async submitNote(
    text: string,
    documentType: DocumentType,
    specialty: Specialty,
    patientId?: string,
    encounterId?: string
  ): Promise<CodingResult> {
    const payload: CodingRequest & { patient_id?: string; encounter_id?: string } = {
      text,
      document_type: documentType,
      specialty,
      include_hcpcs: true,
      ...(patientId && { patient_id: patientId }),
      ...(encounterId && { encounter_id: encounterId }),
    }
    const response = await api.post<CodingResult>("/api/v1/coding/code", payload)
    return response.data
  },

  async getSession(id: string): Promise<CodingResult> {
    const response = await api.get<CodingResult>(`/api/v1/coding/session/${id}`)
    return response.data
  },

  async getSessions(
    page = 1,
    pageSize = 20,
    status?: string,
    specialty?: string
  ): Promise<PaginatedResponse<CodingResult>> {
    const params: Record<string, string | number> = { page, page_size: pageSize }
    if (status) params.status = status
    if (specialty) params.specialty = specialty
    const response = await api.get<PaginatedResponse<CodingResult>>("/api/v1/coding/sessions", { params })
    return response.data
  },

  async searchCodes(q: string, codeType?: string): Promise<CodeSearchResult[]> {
    const params: Record<string, string> = { q }
    if (codeType) params.code_type = codeType
    const response = await api.get<CodeSearchResult[]>("/api/v1/coding/search", { params })
    return response.data
  },

  async getReviewQueue(page = 1, pageSize = 20): Promise<PaginatedResponse<BackendReviewQueueItem>> {
    const response = await api.get<PaginatedResponse<BackendReviewQueueItem>>("/api/v1/coding/review/queue", {
      params: { page, page_size: pageSize },
    })
    return response.data
  },

  async submitReview(
    sessionId: string,
    action: "approved" | "rejected",
    codes: string[],
    notes?: string
  ): Promise<void> {
    const payload = {
      session_id: sessionId,
      approved_codes: action === "approved" ? codes : [],
      rejected_codes: action === "rejected" ? codes : [],
      reviewer_notes: notes || null,
    }
    await api.post(`/api/v1/coding/review/${sessionId}`, payload)
  },
}

// ── Health API ─────────────────────────────────────────────
export const healthAPI = {
  async check(): Promise<HealthStatus> {
    const response = await api.get<HealthStatus>("/health")
    return response.data
  },
}

export default api
