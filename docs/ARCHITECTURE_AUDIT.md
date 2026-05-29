# Architecture Audit — AI Medical Coding Agent
**Audit Date:** 2026-05-28
**Auditor:** Senior Healthcare AI Architect
**System Version:** 1.0.0
**Audit Scope:** Full backend codebase, knowledge base, infrastructure, AI/LLM pipeline

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Folder Structure](#folder-structure)
3. [System Architecture Diagram](#system-architecture-diagram)
4. [Data Flow Diagram](#data-flow-diagram)
5. [Request Lifecycle Walkthrough](#request-lifecycle-walkthrough)
6. [Component Analysis](#component-analysis)
   - [FastAPI Application Layer](#fastapi-application-layer)
   - [Configuration Management](#configuration-management)
   - [Database Layer](#database-layer)
   - [AI/LLM Pipeline](#aillm-pipeline)
   - [Clinical NLP Engine](#clinical-nlp-engine)
   - [RAG Knowledge Base](#rag-knowledge-base)
   - [Medical Code Validator](#medical-code-validator)
   - [Document Processing](#document-processing)
   - [Authentication & Security](#authentication--security)
7. [Dependency Analysis](#dependency-analysis)
8. [Async Processing Patterns](#async-processing-patterns)
9. [Session & State Management](#session--state-management)
10. [Knowledge Base Assessment](#knowledge-base-assessment)
11. [Specialty Support Analysis](#specialty-support-analysis)
12. [Critical Findings](#critical-findings)

---

## Executive Summary

The AI Medical Coder is a FastAPI-based backend system that implements a multi-stage clinical coding pipeline. It combines clinical NLP entity extraction, semantic RAG retrieval from a ChromaDB vector store, and an LLM-powered code assignment engine to produce ICD-10-CM, CPT, and HCPCS codes from clinical text.

The system is architecturally sound for a prototype. It demonstrates competent software engineering fundamentals: async SQLAlchemy with proper session lifecycle, pydantic schema validation throughout, structured LLM prompting, and a human review queue. However, it has critical gaps that prevent it from being used in any production medical billing environment.

**Strongest aspects:** Clean code architecture, proper async patterns, solid Pydantic schemas, thoughtful LLM prompting, ICD-10-CM knowledge base completeness (74,260 codes).

**Critical weaknesses:** No frontend exists; no authentication system beyond a static API key; CPT dataset is fatally limited to 46 built-in codes with no path to AMA-licensed data; HCPCS is 14 sample codes; the Ollama integration makes synchronous blocking calls inside async handlers; no HIPAA compliance infrastructure; an OpenAI API key is committed in plaintext to the `.env` file.

---

## Folder Structure

```
ai medical coding agent/
├── .env.example                        # Environment variable template (CONTAINS LIVE API KEY)
├── docs/                               # Audit documentation (this directory)
│
└── backend/
    ├── .env                            # Live config (CONTAINS EXPOSED OPENAI API KEY)
    ├── requirements.txt                # Python dependencies (67 packages)
    ├── pyproject.toml                  # pytest + coverage config
    │
    ├── app/
    │   ├── main.py                     # FastAPI app + lifespan startup/shutdown
    │   ├── config.py                   # Pydantic Settings (env-driven configuration)
    │   ├── __init__.py
    │   │
    │   ├── api/
    │   │   ├── __init__.py
    │   │   ├── dependencies.py         # API key auth dependency
    │   │   └── routes/
    │   │       ├── __init__.py
    │   │       ├── coding.py           # 5 endpoints: /code, /session, /lookup, /search, /review
    │   │       ├── documents.py        # 1 endpoint: /documents/upload
    │   │       └── health.py           # 2 endpoints: /health, /
    │   │
    │   ├── agents/
    │   │   ├── __init__.py
    │   │   └── medical_coder.py        # CORE: 8-step coding pipeline orchestration
    │   │
    │   ├── coding/
    │   │   ├── __init__.py
    │   │   └── validator.py            # Format validation + sequencing checks
    │   │
    │   ├── document/
    │   │   ├── __init__.py
    │   │   └── ocr.py                  # PDF/DOCX/image text extraction + OCR
    │   │
    │   ├── llm/
    │   │   ├── __init__.py
    │   │   ├── prompts.py              # SYSTEM_PROMPT, CODING_PROMPT_TEMPLATE, others
    │   │   └── provider.py             # Ollama / Anthropic / OpenAI abstraction
    │   │
    │   ├── models/
    │   │   ├── __init__.py
    │   │   ├── database.py             # SQLAlchemy ORM (CodingSession, AssignedCode, KBLog)
    │   │   └── schemas.py              # Pydantic v2 schemas (all request/response models)
    │   │
    │   ├── nlp/
    │   │   ├── __init__.py
    │   │   ├── entity_extractor.py     # scispaCy/spaCy NER + UMLS linking
    │   │   └── soap_parser.py          # Regex-based SOAP section extraction
    │   │
    │   ├── rag/
    │   │   ├── __init__.py
    │   │   ├── indexer.py              # ChromaDB ingestion + SentenceTransformer embedding
    │   │   └── retriever.py            # Semantic code search + code lookup
    │   │
    │   └── utils/
    │       └── __init__.py             # EMPTY — no utility functions implemented
    │
    ├── knowledge_base/
    │   ├── data/
    │   │   ├── icd10/
    │   │   │   └── icd10cm_codes.json  # 74,260 ICD-10-CM FY2026 codes (GOOD)
    │   │   ├── cpt/
    │   │   │   └── (empty — no cpt_codes.json exists)  # CRITICAL GAP
    │   │   └── hcpcs/
    │   │       └── hcpcs_codes.json    # 14 sample codes only  (CRITICAL GAP)
    │   ├── indices/
    │   │   └── (ChromaDB HNSW index files — 3 collections persisted)
    │   └── scripts/
    │       └── build_knowledge_base.py  # KB builder / downloader
    │
    ├── tests/
    │   ├── __init__.py
    │   ├── test_coding.py              # Unit + integration tests
    │   └── test_nlp.py                 # NLP component tests
    │
    └── venv/                           # Python virtual environment (should be gitignored)
        └── Lib/site-packages/          # Installed dependencies
```

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AI MEDICAL CODER SYSTEM v1.0.0                      │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      HTTP CLIENT (No Frontend)                       │   │
│  │           curl / Postman / API consumer / future web app            │   │
│  └──────────────────────────┬──────────────────────────────────────────┘   │
│                             │  HTTP (port 8000)                            │
│  ┌──────────────────────────▼──────────────────────────────────────────┐   │
│  │                    FastAPI Application Layer                         │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  CORS Middleware (origins: localhost:3000, localhost:8080)   │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  Global Exception Handler                                    │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                     │   │
│  │  ┌──────────────┐  ┌──────────────────┐  ┌─────────────────────┐  │   │
│  │  │  /health     │  │  /api/v1/coding   │  │ /api/v1/documents   │  │   │
│  │  │  / (root)    │  │  /code           │  │ /upload             │  │   │
│  │  │              │  │  /session/{id}   │  └─────────────────────┘  │   │
│  │  └──────────────┘  │  /lookup/{t}/{c} │                            │   │
│  │                    │  /search         │                            │   │
│  │                    │  /review/{id}    │                            │   │
│  │                    │  /review/queue   │                            │   │
│  │                    └──────────────────┘                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                             │                                               │
│  ┌──────────────────────────▼──────────────────────────────────────────┐   │
│  │                   API Key Authentication Layer                       │   │
│  │         (dev mode: open access; prod: X-API-Key header)             │   │
│  └──────────────────────────┬──────────────────────────────────────────┘   │
│                             │                                               │
│  ┌──────────────────────────▼──────────────────────────────────────────┐   │
│  │                  MedicalCoderAgent (Orchestrator)                    │   │
│  │  ┌──────────┐ ┌───────────┐ ┌───────────┐ ┌────────┐ ┌─────────┐ │   │
│  │  │  SOAP    │ │  Entity   │ │   RAG     │ │  LLM   │ │Validator│ │   │
│  │  │  Parser  │ │ Extractor │ │ Retriever │ │ Engine │ │         │ │   │
│  │  └──────────┘ └───────────┘ └───────────┘ └────────┘ └─────────┘ │   │
│  └──────────────────────────┬──────────────────────────────────────────┘   │
│                 ┌───────────┼──────────────────┐                           │
│                 │           │                  │                           │
│  ┌──────────────▼───┐ ┌────▼───────────┐ ┌───▼───────────────────────┐   │
│  │   SQLite DB      │ │  ChromaDB      │ │  LLM Provider              │   │
│  │  (aiosqlite)     │ │  (Persistent)  │ │  ┌─────────────────────┐  │   │
│  │                  │ │                │ │  │ Ollama (local)       │  │   │
│  │  coding_sessions │ │  icd10_codes   │ │  │ Anthropic Claude     │  │   │
│  │  assigned_codes  │ │  cpt_codes     │ │  │ OpenAI GPT-4o        │  │   │
│  │  knowledge_base  │ │  hcpcs_codes   │ │  └─────────────────────┘  │   │
│  │  _log            │ │                │ └───────────────────────────┘   │
│  └──────────────────┘ └────────────────┘                                   │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     Document Processing Layer                         │  │
│  │    PyMuPDF → pdfplumber (fallback) → Tesseract OCR (image fallback)  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     Clinical NLP Layer                                │  │
│  │    scispaCy en_core_sci_lg (preferred) → en_core_web_sm (fallback)   │  │
│  │    UMLS Entity Linking (optional, disabled in current .env)           │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
CLINICAL TEXT INPUT
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  Step 1: Preprocessing (entity_extractor.preprocess)    │
│  - Expand clinical abbreviations (HTN→hypertension, etc)│
│  - 40+ abbreviation mappings                           │
│  Output: expanded_text                                  │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Step 2: SOAP Parsing (soap_parser.parse_soap_note)     │
│  - Regex-based section detection (S/O/A/P headers)     │
│  - Discharge summary patterns (secondary patterns)      │
│  - Fallback: full text → assessment section             │
│  Output: SOAPSection {subjective, objective,            │
│          assessment, plan, raw_text}                    │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Step 3: Clinical NER (entity_extractor.extract)        │
│  - spaCy/scispaCy model inference                       │
│  - Named entity recognition (DISEASE, PROCEDURE, etc)  │
│  - UMLS linking (if en_core_sci_lg + umls linker)      │
│  - Confidence scores from UMLS similarity               │
│  Output: List[ExtractedEntity]                          │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Step 4: Search Query Building                          │
│  - Entity texts + UMLS canonical names (up to 10)      │
│  - Extracted diagnoses from Assessment (up to 5)        │
│  - Extracted procedures from Plan (up to 3)             │
│  - Fallback: first 500 chars of text                   │
│  Output: List[str] unique queries (up to 18 queries)   │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Step 5: RAG Retrieval (retriever._search)              │
│  - SentenceTransformer embedding per query              │
│  - ChromaDB cosine similarity search                    │
│  - Similarity threshold filtering (≥ 0.30 default)     │
│  - Top-5 queries × 8 ICD-10 + 5 CPT results            │
│  - Deduplication: keep highest similarity per code      │
│  - Truncate: top 20 ICD-10, top 15 CPT candidates       │
│  Output: icd10_candidates[], cpt_candidates[]           │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Step 6: LLM Code Assignment                            │
│  - Build structured prompt with:                        │
│    · SYSTEM_PROMPT (CPC persona, 6 coding rules)       │
│    · CODING_PROMPT_TEMPLATE (document, specialty,       │
│      clinical text ≤3000 chars, entities, candidates)  │
│  - LLM call (Ollama/Anthropic/OpenAI)                  │
│  - temperature=0.05 (near-deterministic)                │
│  - JSON response parsing (markdown extraction fallback) │
│  Output: {primary_diagnosis, secondary_diagnoses[],     │
│          procedure_codes[], coding_notes,               │
│          requires_review, overall_confidence}           │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Step 7: Code Object Construction                       │
│  - Map LLM code references back to candidate metadata   │
│  - Handle both period (I21.9) and no-period (I219) fmts │
│  - Infer CodeType from code format if not in candidates │
│  - Apply confidence scores from LLM output              │
│  Output: List[MedicalCode]                              │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Step 8: Validation (validator.validate_codes)          │
│  - Regex format validation (ICD-10/CPT/HCPCS patterns)  │
│  - Knowledge base lookup (confirms code exists in KB)   │
│  - Confidence penalty (-0.10) if not in KB             │
│  - Sequencing checks:                                   │
│    · Single primary diagnosis rule                      │
│    · Symptom codes alongside specific dx codes         │
│    · ICD-10 code count limit (>25 = warning)           │
│  Output: validated_codes[], sequencing_warnings[]       │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Step 9: Review Determination                           │
│  - overall_confidence < 0.70 → needs_review             │
│  - LLM sets requires_review=true → needs_review         │
│  - Sequencing warnings present → needs_review           │
│  - No codes produced → needs_review                     │
│  - request.require_review=true → needs_review           │
│  Output: CodingStatus (COMPLETED | NEEDS_REVIEW | ERROR)│
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Step 10: Database Persistence                          │
│  - INSERT coding_sessions (full note, SOAP, entities)   │
│  - INSERT assigned_codes (one row per code)             │
│  - Async commit via SQLAlchemy AsyncSession             │
│  Output: CodingResult (persisted, returned to client)   │
└─────────────────────────────────────────────────────────┘
```

---

## Request Lifecycle Walkthrough

### POST /api/v1/coding/code

**1. HTTP Request arrives**
- FastAPI parses JSON body against `CodingRequest` Pydantic schema
- Field validation: `text` min_length=10, `max_codes` 1-20, enum fields validated
- CORS headers checked (origins whitelist)

**2. Authentication**
- `get_current_api_key` dependency runs
- Reads `X-API-Key` header
- If `ALLOWED_API_KEYS` is empty (current state): returns "dev", all requests pass
- If keys configured: validates against comma-separated list

**3. Agent invocation**
- `get_medical_coder()` returns module-level singleton `MedicalCoderAgent`
- `await agent.code_clinical_note(request)` begins the 8-step pipeline (described above)

**4. Database write**
- `CodingSession` ORM object constructed from result
- `AssignedCode` ORM objects constructed for each code
- `db.add()` called for each object
- `await db.commit()` persists atomically
- Session auto-rollback on exception via `get_db()` context manager

**5. Response serialization**
- `CodingResult` Pydantic model serialized to JSON
- Response returned with HTTP 200

**Estimated latency breakdown:**
- spaCy NER: 50-200ms (text-dependent)
- ChromaDB embedding (per query): 20-100ms × 5 queries = 100-500ms
- LLM call (OpenAI GPT-4o): 2,000-8,000ms typical
- LLM call (Ollama local): 5,000-30,000ms depending on hardware
- DB write: 10-50ms
- Total typical range: 3-10 seconds (cloud LLM) / 8-35 seconds (local Ollama)

---

## Component Analysis

### FastAPI Application Layer

**File:** `backend/app/main.py`

The application uses a lifespan context manager (proper FastAPI v0.93+ pattern) for startup/shutdown. Startup sequence:
1. Configure structured logging
2. Create `./data` directory
3. Initialize SQLite database (create tables)
4. Index ICD-10/CPT/HCPCS into ChromaDB (skip if already indexed)
5. Pre-load spaCy NLP model

CORS is configured with wildcard methods and headers. Origins are limited but accept credentials — this is a misconfiguration for HIPAA-adjacent systems (credentials with wildcard CORS is dangerous).

The global exception handler returns a 500 with `type(exc).__name__` exposed — this leaks internal implementation details in production.

**Missing from app layer:**
- Request ID injection for distributed tracing
- Request/response logging middleware
- Rate limiting middleware
- Body size limits (beyond document upload)
- Compression middleware
- Request timeout enforcement
- Health check granularity (readiness vs liveness)

---

### Configuration Management

**File:** `backend/app/config.py`

Uses `pydantic-settings` with `.env` file loading. The `@lru_cache()` singleton pattern is correct. All settings have sane defaults. Properties for list parsing (`api_keys_list`, `cors_origins_list`) are well-designed.

**Critical issue:** The `.env` file contains a live OpenAI API key (`sk-proj-vfuPcoNt...`). This key is committed to version control in both `backend/.env` AND `.env.example`. This is an immediate credential leak.

**Configuration gaps:**
- No validation of `database_url` format
- No validation of `llm_provider` against allowed values
- `secret_key` defaults to `"change-this-secret-key-in-production"` — not enforced to be changed
- `ENABLE_UMLS_LINKING=false` in `.env` but `enable_umls_linking: bool = True` in config default — `.env` wins, but this inconsistency is confusing
- No environment-specific config profiles (dev/staging/prod)

---

### Database Layer

**File:** `backend/app/models/database.py`

**Positive aspects:**
- Async SQLAlchemy 2.0 with `aiosqlite` (proper async pattern)
- `async_sessionmaker` with `expire_on_commit=False` (correct for async)
- Composite indexes on high-query columns: `(status, created_at)`, `(code_type)`, `(code)`
- Relationships with cascade delete (correct for referential integrity)
- `get_db()` async generator handles commit/rollback correctly

**Schema assessment:**
- `CodingSession`: stores full clinical text in plaintext — PHI exposure risk
- `AssignedCode`: complete code record with status tracking
- `KnowledgeBaseEntry`: knowledge base version log (good idea, barely used)
- No `User` or `Provider` table — no multi-tenancy possible
- No `Audit` table — no immutable audit trail
- No `Organization` / `Practice` table
- `clinical_text` stored unencrypted — HIPAA violation in production

**SQLite limitations for production:**
- No concurrent writes
- File-based — no network access for horizontal scaling
- No connection pooling meaningful at scale
- No built-in encryption
- `.env` has PostgreSQL instructions commented out but not implemented

---

### AI/LLM Pipeline

**File:** `backend/app/agents/medical_coder.py`
**File:** `backend/app/llm/provider.py`
**File:** `backend/app/llm/prompts.py`

**LLM Provider Abstraction:**
The `LLMProvider` class supports three backends with clean conditional dispatch. The Anthropic and OpenAI clients are lazily initialized and cached as instance variables (correct pattern). OpenAI uses `AsyncOpenAI` (truly async); Anthropic uses the synchronous `anthropic.Anthropic` client (blocking — will block the event loop); Ollama uses the synchronous `ollama_lib.chat()` (also blocking).

**Critical async bug:** Both Ollama and Anthropic calls are synchronous operations executed inside `async def` methods. They block the entire FastAPI event loop while the LLM processes the request. Under concurrent load, this will cause all other requests to queue behind a single LLM call. The fix requires `asyncio.get_event_loop().run_in_executor()` or switching to async client variants.

**Prompt Engineering Assessment:**

The `SYSTEM_PROMPT` is well-crafted:
- Establishes CPC/CCS persona with experience
- References specific coding guidelines (ICD-10-CM Official Guidelines, CPT Codebook, HCPCS Level II, CMS NCDs)
- Lists 6 core coding principles correctly
- Critical instruction: "Only assign codes from candidate list" — prevents hallucination
- Instructs flagging uncertain cases — good safety measure

The `CODING_PROMPT_TEMPLATE` is competent:
- Document type and specialty context injected
- Specialty-specific hints (8 specialties with specific guidance)
- Clinical text truncated to 3,000 chars — loses context for long notes
- Structured JSON output format specified exactly
- Requires evidence citation from clinical text
- Confidence thresholds clearly defined

**Prompt weaknesses:**
- No few-shot examples for different specialties
- 3,000 character truncation loses critical information for complex notes
- No chain-of-thought reasoning enforced
- No differential diagnosis prompting
- No explicit modifier selection guidance
- `ENTITY_EXTRACTION_PROMPT` and `SOAP_EXTRACTION_PROMPT` defined but never called — dead code
- `REVIEW_SUMMARY_PROMPT` defined but never called — dead code

**Temperature = 0.05:** Correct for medical coding (near-deterministic outputs desired).

---

### Clinical NLP Engine

**File:** `backend/app/nlp/entity_extractor.py`
**File:** `backend/app/nlp/soap_parser.py`

**Entity Extractor:**

Model loading cascade: `en_core_sci_lg` → `en_core_sci_md` → `en_core_sci_sm` → `en_core_web_lg` → `en_core_web_md` → `en_core_web_sm` → blank English model. This is good graceful degradation.

The active `.env` sets `SCISPACY_MODEL=en_core_web_sm` — the weakest possible model. In production, `en_core_sci_lg` is required for meaningful clinical NER. With `en_core_web_sm`, the system will extract general English named entities (PERSON, ORG, GPE) rather than medical entities (DISEASE, PROCEDURE, CHEMICAL).

UMLS linking is disabled (`ENABLE_UMLS_LINKING=false` in `.env`) — this removes the most valuable feature of the NLP pipeline: grounding entities to UMLS concept IDs that can then map to ICD-10 codes.

Confidence score is hardcoded at 0.85 when UMLS is unavailable, regardless of entity type or context quality. This is misleading.

Abbreviation expansion covers 40+ common clinical abbreviations. This is a solid pragmatic improvement that meaningfully improves embedding quality.

**SOAP Parser:**

Regex-based section detection using MULTILINE patterns. Handles standard SOAP headers, variation patterns (CC:, HPI:, PE:, A/P:, DX:), and discharge summary patterns.

Gap analysis:
- Single-pass regex: only finds the first occurrence of each section header
- Does not handle numbered SOAP sections (e.g., "S1:", "S2:")
- No handling for combined A/P sections with interleaved diagnosis/plan text
- No confidence score for section detection quality
- No support for H&P (History and Physical) format
- No support for Operative Note format (critical for CPT coding accuracy)
- No support for Radiology Report format (for radiology coding)

**Assessment extraction (`extract_diagnoses_from_assessment`):**
Uses line-splitting + heuristic cleaning. Removes list numbering, plan separators, and common non-diagnosis prefixes. This is functional but fragile — complex multi-line diagnoses will be truncated or missed.

---

### RAG Knowledge Base

**File:** `backend/app/rag/indexer.py`
**File:** `backend/app/rag/retriever.py`

**Indexing Architecture:**
- `SentenceTransformer` embedding with `pritamdeka/S-PubMedBert-MS-MARCO` (per config default) or `all-MiniLM-L6-v2` (per `.env`)
- Batch indexing at 500 codes per batch (efficient for large datasets)
- ChromaDB with cosine similarity (HNSW index, persisted to disk)
- Separate collections: `icd10_codes`, `cpt_codes`, `hcpcs_codes`
- Incremental indexing: checks if collection non-empty before rebuilding (startup-safe)

**Embedding Model Gap:**
`all-MiniLM-L6-v2` (actual `.env` setting) is a general-purpose model. It does not understand clinical language nuances (e.g., "MI" vs "myocardial infarction" semantic distance). `S-PubMedBert-MS-MARCO` (config default) or `cambridgeltl/SapBERT-from-PubMedBERT-fulltext` would dramatically improve retrieval quality. This is a meaningful accuracy gap.

**Retrieval:**
- `rag_similarity_threshold = 0.30` — very permissive. This will return low-quality matches frequently. For medical coding, a threshold of 0.55-0.65 is more appropriate.
- No re-ranking step (no cross-encoder or BM25 hybrid)
- The `where_filter` is only applied when `category_filter` is set — for normal queries, no metadata filter is used, meaning codes from all specialties are returned indiscriminately
- No category-guided retrieval (e.g., cardiac queries should be filtered to I-codes)

**Knowledge Base Data Assessment:**

| Dataset | Count | Quality | Source | Issue |
|---------|-------|---------|--------|-------|
| ICD-10-CM | 74,260 | Production-ready | CMS FY2026 official | None — this is complete |
| CPT | 46 (built-in) | Demo only | Hardcoded in indexer.py | CRITICAL: Only 46 of ~10,000+ codes |
| HCPCS Level II | 14 (sample) | Demo only | Hardcoded fallback | CRITICAL: ~5,000+ codes missing |

The CPT dataset situation is the most critical gap in the entire system. The 46 hardcoded CPT codes in `_get_builtin_cpt_codes()` cover only basic E/M codes, a handful of common procedures, and some lab codes. Any request for surgical, radiological, or specialty-specific CPT codes will fail to retrieve relevant candidates. The LLM will then either hallucinate codes or flag everything for review.

The CPT dataset also has a licensing problem: full CPT data requires an AMA license and cannot be freely distributed. The system has no legal pathway to a complete CPT dataset without procurement.

---

### Medical Code Validator

**File:** `backend/app/coding/validator.py`

**Positive aspects:**
- ICD-10-CM format regex correctly handles both `I21.9` and `I219` notations
- CPT pattern handles Category III alphanumeric codes (`0-9}{4}[0-9A-Z]`)
- HCPCS Level II pattern correct (A-V + 4 digits)
- Knowledge base lookup to verify code existence (with confidence penalty)
- Sequencing checks for clinical validity

**Gaps:**
- No ICD-10-PCS validation (would need completely different pattern)
- No modifier format validation (modifiers stored as raw strings)
- No age-sex conflict validation (pediatric codes on adult patients, obstetric codes on males)
- No excludes1/excludes2 note checking
- No "code also" or "use additional code" requirement checking
- No placeholder character validation (7th character requirements)
- The symptom code detection (`R05`, `R06`, etc.) is a small hardcoded prefix list — incomplete

---

### Document Processing

**File:** `backend/app/document/ocr.py`

**Positive aspects:**
- Dual PDF extraction: PyMuPDF → pdfplumber fallback (good resilience)
- Scanned PDF detection: if extracted text < 100 chars, apply OCR
- 2x zoom for better OCR accuracy (good practice)
- Grayscale conversion before OCR (helps accuracy)
- Tesseract with `--psm 6 --oem 3` flags (page segmentation mode for uniform text blocks)
- DOCX support via `python-docx`
- Image support (PNG, JPG, JPEG, TIFF, BMP, GIF)

**Gaps:**
- No DICOM support (medical imaging format used in hospitals)
- No HL7 v2 message parsing
- No FHIR R4 document parsing
- No table extraction from structured PDF reports
- No deduplication of OCR artifacts
- No clinical note template detection
- Synchronous OCR operations block the async event loop

---

### Authentication & Security

**File:** `backend/app/api/dependencies.py`

The authentication system is a single-layer static API key check. In development mode (`ALLOWED_API_KEYS` empty), all requests pass. This is the current state of `backend/.env`.

This means the production instance (if deployed) is completely open with zero authentication.

**Security inventory:**
- No JWT/OAuth2 authentication
- No RBAC (role-based access control)
- No user identity — all requests are anonymous
- No rate limiting
- No IP allowlisting
- No request signing
- No audit log of which user submitted what
- Live OpenAI API key exposed in `.env` file committed to repository
- `SECRET_KEY=dev-secret-key-change-in-production` in `.env` — development secret in production config
- No PHI encryption at rest
- No TLS enforcement
- No security headers (HSTS, CSP, X-Content-Type-Options)

---

## Dependency Analysis

From `requirements.txt`:

| Category | Package | Version | Notes |
|----------|---------|---------|-------|
| Web Framework | fastapi | 0.115.6 | Current, solid |
| ASGI Server | uvicorn[standard] | 0.32.1 | Good |
| Data Validation | pydantic | 2.10.4 | Current |
| Database ORM | sqlalchemy | 2.0.36 | Current async version |
| DB Driver | aiosqlite | 0.20.0 | SQLite only — no PostgreSQL driver |
| DB Migrations | alembic | 1.14.0 | Present but no migrations created |
| NLP | spacy | >=3.8.7 | General English only installed |
| NLP | scispacy | not installed | Clinical NLP missing |
| LLM | langchain | 0.3.13 | Installed but NEVER USED |
| LLM | langchain-core | 0.3.28 | Installed but NEVER USED |
| LLM | langchain-community | 0.3.13 | Installed but NEVER USED |
| LLM | langchain-ollama | 0.2.2 | Installed but NEVER USED |
| LLM | langchain-anthropic | 0.3.3 | Installed but NEVER USED |
| LLM | anthropic | 0.42.0 | Used directly |
| LLM | ollama | 0.4.5 | Used directly |
| RAG | llama-index | 0.12.7 | Installed but NEVER USED |
| RAG | llama-index-* | various | Installed but NEVER USED |
| Vector DB | chromadb | 0.6.3 | Used (but 1.5.9 in venv — version mismatch) |
| Embeddings | sentence-transformers | 3.3.1 | Used |
| PDF | pymupdf | 1.25.1 | Used |
| PDF | pdfplumber | 0.11.4 | Used as fallback |
| OCR | pytesseract | 0.3.13 | Used |
| Auth | python-jose[cryptography] | 3.3.0 | Installed but NEVER USED |
| Auth | passlib[bcrypt] | 1.7.4 | Installed but NEVER USED |

**Dead dependencies (installed but unused):** LangChain (all packages), LlamaIndex (all packages), python-jose, passlib — these add ~200MB+ of unused packages and attack surface.

**Version mismatch:** `chromadb==0.6.3` in requirements.txt but `chromadb-1.5.9` is what's installed in venv. API compatibility issues are possible.

---

## Async Processing Patterns

**Correct patterns used:**
- `asynccontextmanager` for FastAPI lifespan
- `async def` route handlers throughout
- `AsyncSession` and `async_sessionmaker` for database
- `AsyncOpenAI` for OpenAI calls
- `httpx.AsyncClient` for Ollama availability check

**Incorrect/blocking patterns:**
- `ollama_lib.chat()` in `async def _ollama_complete()` — synchronous, blocks event loop
- `anthropic.Anthropic` (sync client) in `async def _anthropic_complete()` — blocks event loop
- `SentenceTransformer.encode()` in `embed_texts()` — CPU-bound, blocks event loop
- `spacy(text)` NLP inference — CPU-bound, blocks event loop
- ChromaDB operations — synchronous, blocks event loop
- PDF/OCR processing — CPU-bound, blocks event loop

Under any concurrent load, these blocking operations will cause request timeouts for other users. A production system requires `asyncio.run_in_executor()` wrapping or a dedicated thread pool for CPU-bound operations.

---

## Session & State Management

- No user sessions — anonymous API
- `MedicalCoderAgent` is a module-level singleton (`_agent`)
- `LLMProvider` is a module-level singleton (`_llm_provider`)
- `CodeRetriever` is a module-level singleton (`_retriever`)
- ChromaDB client is a module-level singleton (`_chroma_client`)
- Embedding model is a module-level singleton (`_embedding_model`)
- spaCy NLP model is module-level global (`_nlp`, `_linker`)

All singletons are initialized lazily on first access. This means the first request after startup experiences cold-start latency for any component not pre-warmed during lifespan startup.

The database session is properly managed per-request via `get_db()` async generator with commit/rollback lifecycle.

There is no in-memory caching of code lookups, embedding results, or LLM responses. Repeated queries for identical clinical text will re-run the full pipeline.

---

## Knowledge Base Assessment

**ICD-10-CM (74,260 codes):**
This is the official CMS FY2026 dataset — production quality. All major chapters covered. Long descriptions, short descriptions, categories, and chapters are populated. The ChromaDB HNSW index is persisted and ready. This is the strongest component of the knowledge base.

**CPT (46 codes — hardcoded fallback):**
The 46 built-in codes cover: E/M office visits (99202-99215), hospital care (99221-99239), ED visits (99281-99285), ECG (93000), echo (93306), chest X-ray (71046), brain MRI (70553), knee replacement (27447), coronary bypass (33533), laparoscopic cholecystectomy (47562), appendectomy (44950), upper GI endoscopy (43239), colonoscopy (45378), FNA biopsy (10021), venipuncture (36415), labs (80053, 85025, 80061, 82947, 84443, 86003), IV infusion (96365), injection (96372), psychotherapy (90837, 90834), physical therapy (97110, 97140).

Missing CPT categories (each with hundreds to thousands of codes): surgery, orthopedics, radiology, nuclear medicine, anesthesia, pathology, ob/gyn, ophthalmology, otolaryngology, urology, neurosurgery, cardiology procedures, vascular, plastic surgery, dermatology, allergy, Category II quality codes, Category III emerging technology codes.

**HCPCS Level II (14 sample codes):**
The 14 codes are a token placeholder. CMS publishes ~5,000+ HCPCS Level II codes covering durable medical equipment, orthotics, prosthetics, drugs, transportation, and behavioral health. The build script downloads from CMS but the current data file is the fallback sample.

---

## Specialty Support Analysis

| Specialty | ICD-10 Coverage | CPT Coverage | Quality |
|-----------|----------------|-------------|---------|
| Internal Medicine | Excellent (full ICD-10) | E/M only (fair) | Medium |
| Cardiology | Excellent (I codes) | ECG, echo, bypass only | Low |
| Orthopedics | Excellent (M,S codes) | Knee replacement only | Very Low |
| Oncology | Excellent (C codes) | None | Very Low |
| Neurology | Excellent (G codes) | Brain MRI only | Very Low |
| Psychiatry | Excellent (F codes) | Psychotherapy only | Low |
| Radiology | Excellent (Z codes) | Chest X-ray, brain MRI | Very Low |
| Surgery | Excellent (procedure codes) | 3-4 procedures | Very Low |
| Emergency | Excellent (R, S, T codes) | ED E/M codes | Medium |
| Pediatrics | Excellent | None specialty-specific | Very Low |
| Obstetrics | Excellent (O codes) | None | Very Low |

The specialty hint system in `SPECIALTY_CONTEXT` is well-conceived but the CPT data gap makes the prompting irrelevant for procedure coding in most specialties.

---

## Critical Findings

1. **EXPOSED API KEY:** Live OpenAI API key committed to repository in both `.env` and `.env.example`. Immediate revocation and rotation required.

2. **CPT DATASET CRITICAL GAP:** Only 46 CPT codes available. This makes CPT coding functionally useless for any real clinical encounter beyond basic E/M codes.

3. **HCPCS DATASET CRITICAL GAP:** 14 sample codes only. Functionally useless for equipment, drug, or supply coding.

4. **BLOCKING ASYNC CALLS:** Ollama and Anthropic calls synchronously block the FastAPI event loop. Under any concurrent load, this causes cascading timeouts.

5. **NO AUTHENTICATION IN CURRENT STATE:** `ALLOWED_API_KEYS` is empty in `.env`, granting open access to all endpoints.

6. **PHI STORED IN PLAINTEXT:** Full clinical notes stored unencrypted in SQLite. Direct HIPAA violation for any real patient data.

7. **NO FRONTEND:** Zero frontend code exists. The system cannot be used without direct API access.

8. **DEAD CODE / WASTED DEPENDENCIES:** LangChain (5 packages), LlamaIndex (3 packages), python-jose, passlib all installed and imported by requirements.txt but never used. These packages add security surface and startup overhead with zero benefit.

9. **SCISPACY NOT INSTALLED:** The `.env` configures `en_core_web_sm` — a general English model. Clinical NER quality with this model is poor. Meaningful medical entity extraction requires `en_core_sci_lg`.

10. **NO DATABASE MIGRATIONS:** Alembic is installed but no migrations exist. Schema changes require manual table drops and recreates.
