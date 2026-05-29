# API Documentation — AI Medical Coding Agent
**Version:** 1.0.0
**Base URL:** `http://localhost:8000`
**API Prefix:** `/api/v1`
**Interactive Docs:** `http://localhost:8000/docs` (Swagger UI), `http://localhost:8000/redoc` (ReDoc)

---

## Authentication

All endpoints (except `/health` and `/`) require an API key.

**Header:** `X-API-Key: your-api-key-here`

**Development mode:** If `ALLOWED_API_KEYS` is empty in `.env`, all requests are accepted without an API key.

**Generating an API key:**
```bash
openssl rand -hex 32
```

**Configure in `.env`:**
```
ALLOWED_API_KEYS=your-key-here,optional-second-key
```

**Authentication error response:**
```json
{
  "detail": "Invalid or missing API key"
}
```
Status: `401 Unauthorized`

---

## Enumerations

### CodeType
| Value | Description |
|-------|-------------|
| `ICD-10-CM` | ICD-10 Clinical Modification (diagnosis codes) |
| `ICD-10-PCS` | ICD-10 Procedure Coding System (inpatient procedures) |
| `CPT` | Current Procedural Terminology |
| `HCPCS` | HCPCS Level II (equipment, drugs, supplies) |

### CodingStatus
| Value | Description |
|-------|-------------|
| `pending` | Request received, not yet processed |
| `processing` | Currently being processed |
| `completed` | Codes assigned, confidence above threshold |
| `needs_review` | Flagged for human review |
| `approved` | Human reviewer approved codes |
| `rejected` | Human reviewer rejected codes |
| `error` | Processing failed |

### Specialty
| Value | Description |
|-------|-------------|
| `general` | General practice / primary care |
| `cardiology` | Cardiology |
| `orthopedics` | Orthopedics |
| `oncology` | Oncology |
| `neurology` | Neurology |
| `psychiatry` | Psychiatry |
| `radiology` | Radiology |
| `surgery` | Surgery |
| `emergency` | Emergency medicine |
| `internal_medicine` | Internal medicine |
| `pediatrics` | Pediatrics |
| `obstetrics` | Obstetrics & gynecology |
| `dermatology` | Dermatology |
| `urology` | Urology |
| `pulmonology` | Pulmonology |
| `gastroenterology` | Gastroenterology |

### DocumentType
| Value | Description |
|-------|-------------|
| `clinical_note` | General clinical note |
| `soap_note` | SOAP format note |
| `discharge_summary` | Hospital discharge summary |
| `operative_note` | Operative/surgical note |
| `radiology_report` | Radiology report |
| `lab_report` | Laboratory report |
| `progress_note` | Progress note |
| `consultation_note` | Consultation note |

---

## Endpoints

---

### GET /health

System health check. No authentication required.

**Request:** None

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "llm_available": true,
  "knowledge_base_loaded": true,
  "nlp_loaded": true,
  "components": {
    "llm": "openai/gpt-4o - ok",
    "knowledge_base": "ICD-10: 74260 codes, CPT: 46 codes",
    "nlp": "model: en_core_web_sm - loaded"
  }
}
```

**Notes:**
- `status` is always `"healthy"` in current implementation (logic bug — always healthy regardless of component states)
- `knowledge_base_loaded` is true if any codes are indexed

---

### GET /

Root endpoint. Returns application information.

**Request:** None

**Response:** `200 OK`
```json
{
  "name": "AI Medical Coder",
  "version": "1.0.0",
  "docs": "/docs",
  "health": "/health"
}
```

---

### POST /api/v1/coding/code

Submit clinical text for AI-powered medical coding.

**Authentication:** Required

**Request Body:** `application/json`

```json
{
  "text": "string (required, min 10 chars)",
  "document_type": "soap_note",
  "specialty": "cardiology",
  "patient_id": "ANON-12345",
  "encounter_id": "ENC-67890",
  "include_cpt": true,
  "include_hcpcs": false,
  "max_codes": 10,
  "require_review": false,
  "metadata": {}
}
```

**Field Descriptions:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `text` | string | Yes | — | Clinical note text. Minimum 10 characters. |
| `document_type` | DocumentType enum | No | `clinical_note` | Type of clinical document |
| `specialty` | Specialty enum | No | `general` | Clinical specialty (guides coding hints) |
| `patient_id` | string | No | null | De-identified patient reference. Do NOT include real PHI. |
| `encounter_id` | string | No | null | Encounter reference ID |
| `include_cpt` | boolean | No | true | Whether to include CPT procedure codes |
| `include_hcpcs` | boolean | No | false | Whether to include HCPCS codes |
| `max_codes` | integer 1-20 | No | 10 | Maximum number of codes to return |
| `require_review` | boolean | No | false | Force human review regardless of confidence |
| `metadata` | object | No | {} | Arbitrary metadata to store with session |

**Example Request:**
```json
{
  "text": "S: 65-year-old male with 3-day history of worsening shortness of breath and productive cough with yellow sputum. History of COPD and hypertension.\n\nO: Vitals BP 148/92, HR 98, RR 22, Temp 38.2°C, O2 Sat 91% on room air. CXR: right lower lobe infiltrate consistent with pneumonia.\n\nA: 1. COPD exacerbation with acute lower respiratory infection\n   2. Community-acquired pneumonia, right lower lobe\n   3. Hypertension, not well controlled\n\nP: Admit for IV antibiotics. Nebulized albuterol q4h. Prednisone 40mg x5 days.",
  "document_type": "soap_note",
  "specialty": "internal_medicine",
  "patient_id": "ANON-001",
  "include_cpt": true,
  "include_hcpcs": false,
  "max_codes": 8
}
```

**Response:** `200 OK`

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "codes": [
    {
      "code": "J44.0",
      "code_type": "ICD-10-CM",
      "description": "Chronic obstructive pulmonary disease with acute lower respiratory infection",
      "confidence": 0.92,
      "evidence": "COPD exacerbation with acute lower respiratory infection",
      "is_primary": true,
      "modifiers": [],
      "hierarchy": "J44"
    },
    {
      "code": "J18.9",
      "code_type": "ICD-10-CM",
      "description": "Pneumonia, unspecified organism",
      "confidence": 0.88,
      "evidence": "Community-acquired pneumonia, right lower lobe",
      "is_primary": false,
      "modifiers": [],
      "hierarchy": "J18"
    },
    {
      "code": "I10",
      "code_type": "ICD-10-CM",
      "description": "Essential (primary) hypertension",
      "confidence": 0.85,
      "evidence": "Hypertension, not well controlled",
      "is_primary": false,
      "modifiers": [],
      "hierarchy": "I10"
    },
    {
      "code": "99222",
      "code_type": "CPT",
      "description": "Initial hospital inpatient or observation care, moderate medical decision making",
      "confidence": 0.78,
      "evidence": "Admit for IV antibiotics",
      "is_primary": false,
      "modifiers": [],
      "hierarchy": null
    }
  ],
  "extracted_entities": [
    {
      "text": "shortness of breath",
      "entity_type": "SYMPTOM",
      "umls_cui": null,
      "umls_name": null,
      "icd10_candidates": [],
      "start_char": 52,
      "end_char": 71,
      "confidence": 0.85
    }
  ],
  "soap_sections": {
    "subjective": "65-year-old male with 3-day history...",
    "objective": "Vitals BP 148/92...",
    "assessment": "1. COPD exacerbation...",
    "plan": "Admit for IV antibiotics...",
    "raw_text": "..."
  },
  "specialty": "internal_medicine",
  "document_type": "soap_note",
  "summary": "Primary coding rationale: COPD exacerbation with pneumonia...",
  "requires_human_review": false,
  "review_reason": null,
  "processing_time_ms": 4231,
  "model_used": "openai/gpt-4o",
  "created_at": "2026-05-28T10:30:00.000Z",
  "metadata": {
    "icd10_candidates_count": 18,
    "cpt_candidates_count": 12,
    "entities_extracted": 7,
    "sequencing_warnings": []
  }
}
```

**Error Responses:**

| Status | Scenario |
|--------|---------|
| `400 Bad Request` | Invalid request body (validation failure) |
| `401 Unauthorized` | Missing or invalid API key |
| `422 Unprocessable Entity` | Pydantic validation error (field constraints) |
| `500 Internal Server Error` | Processing failure (returns CodingResult with status=error) |

**Notes:**
- Processing time varies significantly: 3-10 seconds (cloud LLM), 8-35 seconds (local Ollama)
- If `status` is `"needs_review"`, the session is added to the review queue
- `confidence` is 0.0-1.0 where 1.0 is certain and 0.0 is no evidence
- `evidence` is a direct quote from the clinical note supporting each code

---

### GET /api/v1/coding/session/{session_id}

Retrieve a previously coded session by its ID.

**Authentication:** Required

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | UUID string | Session ID returned from `/code` endpoint |

**Example Request:**
```
GET /api/v1/coding/session/550e8400-e29b-41d4-a716-446655440000
X-API-Key: your-api-key
```

**Response:** `200 OK`
Returns a `CodingResult` object (same schema as `/code` response).

**Error Responses:**
| Status | Scenario |
|--------|---------|
| `404 Not Found` | Session ID does not exist |
| `401 Unauthorized` | Missing or invalid API key |

---

### GET /api/v1/coding/lookup/{code_type}/{code}

Look up a specific medical code in the knowledge base.

**Authentication:** Required

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `code_type` | string | One of: `ICD-10-CM`, `CPT`, `HCPCS` |
| `code` | string | The code to look up (e.g., `J18.9`, `99213`, `A4253`) |

**Example Request:**
```
GET /api/v1/coding/lookup/ICD-10-CM/J18.9
X-API-Key: your-api-key
```

**Response:** `200 OK`
```json
{
  "code": "J18.9",
  "code_type": "ICD-10-CM",
  "description": "Pneumonia, unspecified organism",
  "long_description": "Pneumonia, unspecified organism",
  "category": "J18",
  "chapter": "Respiratory system",
  "is_valid": true,
  "effective_date": null,
  "related_codes": []
}
```

**Error Responses:**
| Status | Scenario |
|--------|---------|
| `404 Not Found` | Code not found in knowledge base |
| `401 Unauthorized` | Missing or invalid API key |

**Notes:**
- Both period format (`J18.9`) and no-period format (`J189`) are supported for ICD-10-CM
- Code lookups are case-insensitive

---

### GET /api/v1/coding/search

Semantic search for medical codes matching a clinical query.

**Authentication:** Required

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `q` | string | Yes | — | Clinical query (min 3 characters) |
| `code_type` | string | No | null (all) | Filter: `ICD-10-CM`, `CPT`, `HCPCS` |
| `top_k` | integer 1-50 | No | 10 | Number of results per code type |

**Example Request:**
```
GET /api/v1/coding/search?q=community+acquired+pneumonia&code_type=ICD-10-CM&top_k=5
X-API-Key: your-api-key
```

**Response:** `200 OK`
```json
{
  "icd10": [
    {
      "code": "J18.9",
      "code_type": "ICD-10-CM",
      "description": "Pneumonia, unspecified organism",
      "long_description": "Pneumonia, unspecified organism",
      "category": "J18",
      "chapter": "Respiratory system",
      "similarity": 0.8934,
      "document": "J18.9: Pneumonia, unspecified organism. Pneumonia, unspecified organism"
    },
    {
      "code": "J15.9",
      "code_type": "ICD-10-CM",
      "description": "Unspecified bacterial pneumonia",
      "similarity": 0.8421
    }
  ],
  "cpt": [...],
  "hcpcs": [...]
}
```

**Notes:**
- Results are sorted by semantic similarity (descending)
- Similarity is 0.0-1.0 (cosine similarity converted from distance)
- Results below `RAG_SIMILARITY_THRESHOLD` (default 0.30) are filtered out
- If `code_type` is null, returns all three code type sections

---

### POST /api/v1/coding/review/{session_id}

Submit a human reviewer decision for a flagged session.

**Authentication:** Required

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | UUID string | Session ID to review |

**Request Body:** `application/json`
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "approved_codes": ["J44.0", "J18.9", "I10"],
  "rejected_codes": ["99222"],
  "reviewer_notes": "CPT E/M level adjusted based on complexity review",
  "reviewer_id": "coder-jane-doe"
}
```

**Field Descriptions:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_id` | string | Yes | Must match path parameter |
| `approved_codes` | string[] | Yes | Code strings (e.g., "J44.0") to approve |
| `rejected_codes` | string[] | No | Code strings to reject |
| `reviewer_notes` | string | No | Free-text reviewer notes |
| `reviewer_id` | string | No | Reviewer identifier |

**Response:** `200 OK`
Returns the updated `CodingResult` with status `"approved"` or `"rejected"`.

**Error Responses:**
| Status | Scenario |
|--------|---------|
| `404 Not Found` | Session not found |
| `401 Unauthorized` | Missing or invalid API key |

**Notes:**
- If `approved_codes` is non-empty, session status becomes `"approved"`
- If `approved_codes` is empty, session status becomes `"rejected"`
- Individual `AssignedCode` records are updated with `"approved"` or `"rejected"` status

---

### GET /api/v1/coding/review/queue

Retrieve the paginated list of sessions pending human review.

**Authentication:** Required

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `page` | integer ≥1 | No | 1 | Page number |
| `page_size` | integer 1-100 | No | 20 | Items per page |
| `specialty` | string | No | null | Filter by specialty value |

**Example Request:**
```
GET /api/v1/coding/review/queue?page=1&page_size=10&specialty=cardiology
X-API-Key: your-api-key
```

**Response:** `200 OK`
```json
{
  "items": [
    {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "needs_review",
      "codes": [
        {
          "code": "I21.9",
          "code_type": "ICD-10-CM",
          "description": "Acute myocardial infarction, unspecified",
          "confidence": 0.65,
          "evidence": "...",
          "is_primary": true,
          "modifiers": []
        }
      ],
      "clinical_text_preview": "65-year-old male presenting with crushing chest pain...",
      "specialty": "cardiology",
      "created_at": "2026-05-28T09:15:00.000Z",
      "expires_at": null
    }
  ],
  "total": 47,
  "page": 1,
  "page_size": 10,
  "pages": 5
}
```

**Notes:**
- `clinical_text_preview` is truncated to 300 characters
- Returns only sessions with `status = "needs_review"`
- `expires_at` is currently null (queue expiration not yet implemented)

---

### POST /api/v1/documents/upload

Upload and extract text from a medical document.

**Authentication:** Required

**Request Body:** `multipart/form-data`
| Field | Type | Description |
|-------|------|-------------|
| `file` | file | Document to upload |

**Supported formats:** `pdf`, `txt`, `docx`, `png`, `jpg`, `jpeg`, `tiff`

**Maximum file size:** 50MB (configurable via `MAX_DOCUMENT_SIZE_MB`)

**Example Request (curl):**
```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "X-API-Key: your-api-key" \
  -F "file=@patient_note.pdf"
```

**Response:** `200 OK`
```json
{
  "document_id": "7f3a0c1b-4e2d-4a8f-b5c9-012e456789ab",
  "filename": "patient_note.pdf",
  "extracted_text": "SOAP Note\n\nS: Patient presents with...\n\nO: Vital signs...",
  "page_count": 3,
  "ocr_used": false,
  "status": "success"
}
```

**Field Descriptions:**
| Field | Description |
|-------|-------------|
| `document_id` | UUID for this extraction (not persisted — for client reference only) |
| `filename` | Original filename |
| `extracted_text` | Full extracted text content |
| `page_count` | Number of pages (PDF only; 1 for other formats) |
| `ocr_used` | `true` if Tesseract OCR was applied (scanned PDF or image) |
| `status` | Always `"success"` on 200 response |

**Error Responses:**
| Status | Scenario |
|--------|---------|
| `413 Request Entity Too Large` | File exceeds `MAX_DOCUMENT_SIZE_MB` |
| `415 Unsupported Media Type` | File format not in supported list |
| `422 Unprocessable Entity` | Document processing failed or no meaningful text extracted |
| `401 Unauthorized` | Missing or invalid API key |

**Workflow Note:** 
The `extracted_text` from this endpoint should be passed as the `text` field in a subsequent `/api/v1/coding/code` request.

---

## Common Workflows

### Workflow 1: Code a Text Note

```bash
# Step 1: Submit text for coding
curl -X POST http://localhost:8000/api/v1/coding/code \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Patient has type 2 diabetes mellitus, uncontrolled, HbA1c 9.2%. Essential hypertension with BP 165/95. Started metformin 1000mg BID.",
    "specialty": "internal_medicine",
    "document_type": "soap_note"
  }'

# Response includes session_id
# If status = "completed" → codes are ready
# If status = "needs_review" → submit to review queue
```

### Workflow 2: Code a PDF Document

```bash
# Step 1: Upload PDF and get extracted text
RESPONSE=$(curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "X-API-Key: your-key" \
  -F "file=@clinic_note.pdf")

TEXT=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['extracted_text'])")

# Step 2: Submit extracted text for coding
curl -X POST http://localhost:8000/api/v1/coding/code \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"$TEXT\", \"specialty\": \"general\"}"
```

### Workflow 3: Review Queue Processing

```python
import httpx

base_url = "http://localhost:8000/api/v1"
headers = {"X-API-Key": "your-key"}

# 1. Fetch pending reviews
queue = httpx.get(f"{base_url}/coding/review/queue", headers=headers).json()

# 2. Process each item
for item in queue["items"]:
    session_id = item["session_id"]
    
    # Coder reviews codes manually...
    
    # 3. Submit decision
    decision = {
        "session_id": session_id,
        "approved_codes": ["J44.0", "J18.9"],  # codes coder approves
        "rejected_codes": ["99222"],              # codes coder rejects
        "reviewer_notes": "E/M level adjusted",
        "reviewer_id": "coder@hospital.org"
    }
    
    result = httpx.post(
        f"{base_url}/coding/review/{session_id}",
        json=decision,
        headers=headers
    ).json()
```

---

## Error Code Reference

| HTTP Status | Error Type | Description |
|-------------|-----------|-------------|
| 400 | Bad Request | Malformed JSON body |
| 401 | Unauthorized | Missing or invalid X-API-Key |
| 404 | Not Found | Session ID or code not found |
| 413 | Request Entity Too Large | Document exceeds size limit |
| 415 | Unsupported Media Type | Unsupported file format |
| 422 | Unprocessable Entity | Validation error on request fields |
| 500 | Internal Server Error | Unhandled exception — check server logs |

**Validation Error Response (422):**
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "text"],
      "msg": "String should have at least 10 characters",
      "input": "Short",
      "ctx": {"min_length": 10}
    }
  ]
}
```

**Server Error Response (500):**
```json
{
  "detail": "Internal server error",
  "type": "ExceptionClassName"
}
```

---

## Rate Limits

**Current status:** No rate limiting is implemented.

**Recommended limits for production:**
- `POST /api/v1/coding/code`: 10 requests/minute per API key
- `POST /api/v1/documents/upload`: 5 requests/minute per API key
- `GET /api/v1/coding/search`: 30 requests/minute per API key
- All other GET endpoints: 60 requests/minute per API key

---

## Performance Characteristics

| Endpoint | Typical Latency | P99 Latency |
|----------|----------------|-------------|
| `GET /health` | <10ms | <50ms |
| `POST /code` (OpenAI GPT-4o) | 3-8 seconds | 15 seconds |
| `POST /code` (Ollama local) | 8-35 seconds | 60 seconds |
| `POST /documents/upload` (PDF text) | 200-800ms | 3 seconds |
| `POST /documents/upload` (OCR) | 2-10 seconds | 30 seconds |
| `GET /session/{id}` | 30-100ms | 200ms |
| `GET /search` | 200-500ms | 1 second |
| `GET /review/queue` | 50-200ms | 500ms |

**Note:** All LLM-dependent endpoints are significantly slower under concurrent load due to blocking async calls (see ARCHITECTURE_AUDIT.md).

---

## SDK / Client Examples

### Python
```python
import httpx
from typing import Optional

class MedicalCoderClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"X-API-Key": api_key},
            timeout=60.0  # LLM calls can take 30+ seconds
        )
    
    async def code_note(self, text: str, specialty: str = "general") -> dict:
        response = await self.client.post("/api/v1/coding/code", json={
            "text": text,
            "specialty": specialty,
            "document_type": "clinical_note",
            "include_cpt": True
        })
        response.raise_for_status()
        return response.json()
    
    async def get_session(self, session_id: str) -> dict:
        response = await self.client.get(f"/api/v1/coding/session/{session_id}")
        response.raise_for_status()
        return response.json()
```

### JavaScript / TypeScript
```typescript
const API_BASE = "http://localhost:8000/api/v1";
const API_KEY = "your-api-key";

async function codeClinicalNote(text: string, specialty: string = "general") {
  const response = await fetch(`${API_BASE}/coding/code`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify({ text, specialty, document_type: "clinical_note" }),
  });
  
  if (!response.ok) {
    throw new Error(`Coding failed: ${response.status}`);
  }
  
  return response.json();
}
```
