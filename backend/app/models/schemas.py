from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ─── Enumerations ────────────────────────────────────────────────────────────

class CodeType(str, Enum):
    ICD10_CM = "ICD-10-CM"
    ICD10_PCS = "ICD-10-PCS"
    CPT = "CPT"
    HCPCS = "HCPCS"


class CodingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ERROR = "error"


class Specialty(str, Enum):
    GENERAL = "general"
    CARDIOLOGY = "cardiology"
    ORTHOPEDICS = "orthopedics"
    ONCOLOGY = "oncology"
    NEUROLOGY = "neurology"
    PSYCHIATRY = "psychiatry"
    RADIOLOGY = "radiology"
    SURGERY = "surgery"
    EMERGENCY = "emergency"
    EMERGENCY_MEDICINE = "emergency_medicine"
    INTERNAL = "internal_medicine"
    PEDIATRICS = "pediatrics"
    OBSTETRICS = "obstetrics"
    OBSTETRICS_GYNECOLOGY = "obstetrics_gynecology"
    DERMATOLOGY = "dermatology"
    UROLOGY = "urology"
    PULMONOLOGY = "pulmonology"
    GASTROENTEROLOGY = "gastroenterology"
    NEPHROLOGY = "nephrology"
    OPHTHALMOLOGY = "ophthalmology"
    RHEUMATOLOGY = "rheumatology"
    INFECTIOUS_DISEASE = "infectious_disease"
    ENDOCRINOLOGY = "endocrinology"


class DocumentType(str, Enum):
    CLINICAL_NOTE = "clinical_note"
    SOAP_NOTE = "soap_note"
    DISCHARGE_SUMMARY = "discharge_summary"
    OPERATIVE_NOTE = "operative_note"
    RADIOLOGY_REPORT = "radiology_report"
    LAB_REPORT = "lab_report"
    PROGRESS_NOTE = "progress_note"
    CONSULTATION_NOTE = "consultation_note"
    EMERGENCY_NOTE = "emergency_note"
    HISTORY_PHYSICAL = "history_physical"
    PATHOLOGY_REPORT = "pathology_report"
    NURSING_NOTE = "nursing_note"


# ─── Medical Code Schemas ─────────────────────────────────────────────────────

class MedicalCode(BaseModel):
    code: str = Field(..., description="Medical code (e.g., J18.9)")
    code_type: CodeType
    description: str = Field(..., description="Human-readable description")
    confidence: float = Field(..., ge=0.0, le=1.0, description="0-1 confidence score")
    evidence: str = Field("", description="Supporting text from clinical note")
    is_primary: bool = Field(False, description="Whether this is the primary diagnosis code")
    modifiers: List[str] = Field(default_factory=list, description="Code modifiers")
    hierarchy: Optional[str] = Field(None, description="Code hierarchy path")


class ExtractedEntity(BaseModel):
    text: str
    entity_type: str
    umls_cui: Optional[str] = None
    umls_name: Optional[str] = None
    icd10_candidates: List[str] = Field(default_factory=list)
    start_char: int = 0
    end_char: int = 0
    confidence: float = 0.0


class SOAPSection(BaseModel):
    subjective: Optional[str] = None
    objective: Optional[str] = None
    assessment: Optional[str] = None
    plan: Optional[str] = None
    raw_text: str = ""


# ─── Request Schemas ──────────────────────────────────────────────────────────

class CodingRequest(BaseModel):
    text: str = Field(..., min_length=10, description="Clinical note text to code")
    document_type: DocumentType = Field(DocumentType.CLINICAL_NOTE)
    specialty: Specialty = Field(Specialty.GENERAL)
    patient_id: Optional[str] = Field(None, description="De-identified patient reference")
    encounter_id: Optional[str] = Field(None, description="Encounter reference ID")
    include_cpt: bool = Field(True, description="Include CPT procedure codes")
    include_hcpcs: bool = Field(False, description="Include HCPCS codes")
    max_codes: int = Field(10, ge=1, le=20)
    require_review: bool = Field(False, description="Force human review regardless of confidence")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    extracted_text: str
    page_count: Optional[int] = None
    ocr_used: bool = False
    status: str = "success"


class ReviewDecision(BaseModel):
    session_id: str
    approved_codes: List[str] = Field(..., description="List of code strings to approve")
    rejected_codes: List[str] = Field(default_factory=list)
    reviewer_notes: Optional[str] = None
    reviewer_id: Optional[str] = None


# ─── Response Schemas ─────────────────────────────────────────────────────────

class CodingResult(BaseModel):
    session_id: str
    status: CodingStatus
    codes: List[MedicalCode] = Field(default_factory=list)
    extracted_entities: List[ExtractedEntity] = Field(default_factory=list)
    soap_sections: Optional[SOAPSection] = None
    specialty: Specialty
    document_type: DocumentType
    summary: str = Field("", description="Brief summary of coding rationale")
    requires_human_review: bool = False
    review_reason: Optional[str] = None
    processing_time_ms: Optional[int] = None
    model_used: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CodeLookupResult(BaseModel):
    code: str
    code_type: CodeType
    description: str
    long_description: Optional[str] = None
    category: Optional[str] = None
    chapter: Optional[str] = None
    is_valid: bool
    effective_date: Optional[str] = None
    related_codes: List[str] = Field(default_factory=list)


class ReviewQueueItem(BaseModel):
    session_id: str
    status: CodingStatus
    codes: List[MedicalCode]
    clinical_text_preview: str
    specialty: Specialty
    document_type: DocumentType
    created_at: datetime
    expires_at: Optional[datetime] = None
    review_reason: Optional[str] = None
    requires_human_review: bool = True
    processing_time_ms: Optional[int] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    llm_available: bool
    knowledge_base_loaded: bool
    nlp_loaded: bool
    components: Dict[str, str] = Field(default_factory=dict)


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int


# ─── Auth / User Response Schemas ─────────────────────────────────────────────

class UserResponse(BaseModel):
    """User info (no password hash exposed)."""
    id: int
    email: str
    role: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None


class AuditLogEntry(BaseModel):
    """Audit log entry for API responses."""
    id: int
    user_id: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime
    details: Optional[str] = None
