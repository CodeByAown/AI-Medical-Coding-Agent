# Technical Debt Register — AI Medical Coding Agent
**Date:** 2026-05-28
**Version:** 1.0.0

This document catalogs all identified technical debt items with severity, effort estimates, and impact if left unaddressed.

---

## Summary

| Severity | Count | Estimated Total Effort |
|----------|-------|----------------------|
| Critical | 8 | 8-12 weeks |
| High | 12 | 16-24 weeks |
| Medium | 14 | 12-20 weeks |
| Low | 8 | 4-8 weeks |
| **Total** | **42** | **40-64 weeks** |

---

## Critical Severity

### TD-001: Live API Key Committed to Version Control
**Severity:** CRITICAL
**Category:** Security
**File(s):** `backend/.env`, `.env.example`
**Description:** An active OpenAI API key (`sk-proj-vfuPcoNt...`) is committed to version control in two files. Anyone with repository access can use this key to incur charges on the account owner's behalf or access any data in OpenAI's platform.
**Impact if not fixed:** Financial loss from unauthorized API usage, possible data exposure, vendor policy violation.
**Estimated effort:** 2 hours (key rotation + git history scrub + .gitignore update)
**Fix:**
```bash
# 1. Revoke key at platform.openai.com immediately
# 2. Add to .gitignore
echo ".env" >> .gitignore
# 3. Scrub from git history
git filter-repo --path .env --invert-paths
# 4. Force push (coordinate with all collaborators)
# 5. Store new keys in environment variables or secrets manager
```

---

### TD-002: No Authentication in Current Deployment State
**Severity:** CRITICAL
**Category:** Security
**File(s):** `backend/.env`, `backend/app/api/dependencies.py`
**Description:** `ALLOWED_API_KEYS` is empty in the live `.env` file. The `get_current_api_key` dependency explicitly bypasses all authentication when no keys are configured, granting completely open access to all endpoints.
**Impact if not fixed:** Any person with network access can submit clinical notes, access the review queue, retrieve all coded sessions, and approve/reject codes.
**Estimated effort:** 4 hours (set API keys) to 2 weeks (full JWT implementation)
**Fix:** Generate and configure API keys immediately. Implement JWT long-term.

---

### TD-003: PHI Stored in Plaintext
**Severity:** CRITICAL
**Category:** HIPAA Compliance / Security
**File(s):** `backend/app/models/database.py`
**Description:** The `clinical_text` column in `coding_sessions` stores full clinical notes as unencrypted plaintext TEXT in SQLite. `soap_json` and `extracted_entities_json` also store potentially PHI-containing data unencrypted.
**Impact if not fixed:** HIPAA violation if real patient data is processed. Direct legal liability. OCR Breach Notification Rule triggered if data is exposed.
**Estimated effort:** 1-2 weeks
**Fix:** Field-level AES-256-GCM encryption on `clinical_text`, `soap_json`, `extracted_entities_json`. Key management via AWS KMS or HashiCorp Vault.

---

### TD-004: Ollama and Anthropic Calls Block the Event Loop
**Severity:** CRITICAL
**Category:** Performance / Correctness
**File(s):** `backend/app/llm/provider.py`
**Description:** `_ollama_complete()` calls `ollama_lib.chat()` (synchronous) inside an `async def` method. `_anthropic_complete()` instantiates `anthropic.Anthropic` (synchronous client) inside `async def`. Both block the entire FastAPI event loop while waiting for the LLM response (2-30 seconds).
**Impact if not fixed:** Under any concurrent load (2+ simultaneous requests), all other requests queue behind the LLM call, causing cascading timeouts.
**Estimated effort:** 3-5 days
**Fix:**
```python
import asyncio
from functools import partial

async def _ollama_complete(self, ...):
    loop = asyncio.get_event_loop()
    fn = partial(ollama_lib.chat, model=..., messages=..., options=...)
    response = await loop.run_in_executor(None, fn)
    return response["message"]["content"]
```
For Anthropic: use `anthropic.AsyncAnthropic` client.

---

### TD-005: CPT Dataset Has Only 46 Codes
**Severity:** CRITICAL
**Category:** Clinical Functionality
**File(s):** `backend/app/rag/indexer.py` (`_get_builtin_cpt_codes`)
**Description:** The CPT knowledge base contains only 46 hardcoded codes (basic E/M, a handful of procedures). The full CPT dataset contains ~10,000+ codes. Any specialty-specific, surgical, or advanced procedure coding will fail to retrieve relevant candidates.
**Impact if not fixed:** CPT coding is functionally useless for the vast majority of real clinical encounters. System cannot be marketed as a coding solution.
**Estimated effort:** 1 day (data ingestion) + $3K-15K/yr (AMA license for commercial use)
**Fix:** Procure AMA CPT license. Ingest full CPT dataset in existing JSON format.

---

### TD-006: HCPCS Dataset Has Only 14 Sample Codes
**Severity:** CRITICAL
**Category:** Clinical Functionality
**File(s):** `backend/knowledge_base/data/hcpcs/hcpcs_codes.json`
**Description:** The HCPCS knowledge base contains 14 sample codes representing a tiny fraction of the ~5,000+ HCPCS Level II codes published by CMS.
**Impact if not fixed:** Equipment, drug, supply, and DME coding is completely non-functional.
**Estimated effort:** 2 hours (CMS download is free, build script already has logic)
**Fix:** Run `python knowledge_base/scripts/build_knowledge_base.py` with internet access. CMS HCPCS data is free.

---

### TD-007: No Audit Trail for PHI Access
**Severity:** CRITICAL
**Category:** HIPAA Compliance
**File(s):** No audit log table or middleware exists
**Description:** HIPAA Security Rule 164.312(b) requires audit controls to record activity in information systems containing PHI. There is no logging of which user (no user identity exists) accessed which patient record, when, or for what purpose.
**Impact if not fixed:** HIPAA audit failure. OCR investigation if breach occurs. Fines up to $1.9M per violation category.
**Estimated effort:** 1-2 weeks
**Fix:** Add `AuditLog` database table. Add middleware to log all PHI access events with timestamps and user identity.

---

### TD-008: scispaCy Not Installed / Wrong Model Configured
**Severity:** CRITICAL
**Category:** Clinical NLP Accuracy
**File(s):** `backend/.env`, `backend/app/nlp/entity_extractor.py`
**Description:** `SCISPACY_MODEL=en_core_web_sm` in `.env` uses the general English spaCy model. This model is trained on news articles and web text — not clinical literature. It identifies PERSON, ORG, GPE entities, not DISEASE, PROCEDURE, CHEMICAL. Clinical entity extraction quality is severely degraded compared to `en_core_sci_lg`.
**Impact if not fixed:** The NLP pipeline provides near-useless medical entities. RAG search queries are derived from these entities, so retrieval quality is directly impacted. Overall coding accuracy degrades significantly.
**Estimated effort:** 4 hours (install scispaCy + configure)
**Fix:**
```bash
pip install scispacy==0.5.5
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_lg-0.5.4.tar.gz
# Update .env: SCISPACY_MODEL=en_core_sci_lg
# Update .env: ENABLE_UMLS_LINKING=true
```

---

## High Severity

### TD-009: SentenceTransformer Embedding Blocks Event Loop
**Severity:** HIGH
**Category:** Performance
**File(s):** `backend/app/rag/indexer.py`
**Description:** `SentenceTransformer.encode()` is a CPU-bound operation called from within async route handlers via the agent. There is no thread pool wrapping. Under concurrent requests, this blocks the event loop.
**Impact if not fixed:** Slow response times under load. Potential timeouts.
**Estimated effort:** 1-2 days
**Fix:** Wrap `embed_texts()` in `asyncio.run_in_executor()` or use a background worker.

---

### TD-010: spaCy NLP Inference Blocks Event Loop
**Severity:** HIGH
**Category:** Performance
**File(s):** `backend/app/nlp/entity_extractor.py`
**Description:** `nlp(text)` (spaCy model inference) is CPU-bound and called synchronously inside async handlers.
**Impact if not fixed:** Same as TD-009 — blocks event loop under concurrent load.
**Estimated effort:** 1 day
**Fix:** Wrap spaCy inference in thread pool executor.

---

### TD-011: SQLite Database Not Suitable for Production
**Severity:** HIGH
**Category:** Infrastructure
**File(s):** `backend/.env`, `backend/app/models/database.py`
**Description:** SQLite (configured as default) does not support concurrent writes, network access, or horizontal scaling. It cannot serve multiple API workers simultaneously.
**Impact if not fixed:** Data loss under concurrent writes. Cannot scale. Cannot deploy with multiple workers.
**Estimated effort:** 3-5 days (schema + migration + configuration)
**Fix:** Migrate to PostgreSQL. `asyncpg` driver. Alembic migration.

---

### TD-012: No Database Migrations (Alembic Not Initialized)
**Severity:** HIGH
**Category:** Operations
**File(s):** No Alembic migration scripts exist
**Description:** Alembic is installed but `alembic init` has never been run. There are no migration scripts. Any schema change requires destroying the database and losing all data.
**Impact if not fixed:** Cannot evolve schema without data loss. No deployment rollback capability.
**Estimated effort:** 1 day
**Fix:** `alembic init alembic && alembic revision --autogenerate -m "initial_schema" && alembic upgrade head`

---

### TD-013: Unused Dependencies in requirements.txt
**Severity:** HIGH
**Category:** Maintainability / Security
**File(s):** `backend/requirements.txt`
**Description:** Five LangChain packages (`langchain`, `langchain-core`, `langchain-community`, `langchain-ollama`, `langchain-anthropic`) and three LlamaIndex packages (`llama-index`, `llama-index-vector-stores-chroma`, `llama-index-embeddings-huggingface`) are in requirements.txt but no import from any of these packages exists anywhere in the application code. Combined, these add ~200MB+ of installed packages.
**Impact if not fixed:** Increased Docker image size, longer startup times, expanded vulnerability surface, confusing developer experience.
**Estimated effort:** 2 hours
**Fix:** Remove the 8 unused packages from requirements.txt. Run tests to confirm nothing breaks.

---

### TD-014: ChromaDB Version Mismatch
**Severity:** HIGH
**Category:** Reliability
**File(s):** `backend/requirements.txt` (chromadb==0.6.3), `backend/venv/` (chromadb-1.5.9 installed)
**Description:** requirements.txt pins `chromadb==0.6.3` but the installed version in venv is 1.5.9. These versions have significantly different APIs. Any new pip install from requirements.txt will downgrade ChromaDB and likely break the existing index files.
**Impact if not fixed:** Environment inconsistency. Deployment failures. Index corruption when downgrading.
**Estimated effort:** 2 hours (test with 1.5.9, update requirements.txt pin)
**Fix:** Verify all ChromaDB 1.5.9 API calls work, then update `requirements.txt` to `chromadb==1.5.9`.

---

### TD-015: Clinical Text Truncated to 3,000 Characters
**Severity:** HIGH
**Category:** Clinical Accuracy
**File(s):** `backend/app/agents/medical_coder.py`
**Description:** In `_llm_assign_codes()`, the clinical text is truncated to `coding_text[:3000]` before being sent to the LLM. A typical hospital discharge summary can be 5,000-20,000 characters. Any diagnoses, procedures, or contextual information beyond 3,000 characters is silently dropped.
**Impact if not fixed:** Missed diagnoses. Incomplete coding. Revenue loss.
**Estimated effort:** 1 week (intelligent segment extraction + LLM context management)
**Fix:** Implement `_extract_coding_relevant_segments()` as described in IMPROVEMENT_ROADMAP.md Phase 3.

---

### TD-016: RAG Similarity Threshold Too Low
**Severity:** HIGH
**Category:** Clinical Accuracy
**File(s):** `backend/app/config.py`, `backend/.env`
**Description:** `RAG_SIMILARITY_THRESHOLD=0.3` is very permissive. At 30% similarity, the retriever will return many irrelevant codes that then pollute the LLM's candidate list. For medical coding, the LLM should only see relevant candidates.
**Impact if not fixed:** LLM receives noisy candidate lists, increasing chance of wrong code selection.
**Estimated effort:** 2 hours (empirical threshold testing)
**Fix:** Set `RAG_SIMILARITY_THRESHOLD=0.55-0.65`. Test against sample clinical notes to calibrate.

---

### TD-017: General-Purpose Embedding Model
**Severity:** HIGH
**Category:** Clinical Accuracy
**File(s):** `backend/.env`
**Description:** `.env` sets `EMBEDDING_MODEL=all-MiniLM-L6-v2` — a general-purpose model trained on web data. Clinical terminology has very different semantic relationships than general English. "MI" vs "myocardial infarction" would not be recognized as equivalent.
**Impact if not fixed:** Lower retrieval recall for medical terms. More relevant codes missed.
**Estimated effort:** 4 hours (model swap + reindex)
**Fix:** Switch to `EMBEDDING_MODEL=cambridgeltl/SapBERT-from-PubMedBERT-fulltext` or `pritamdeka/S-PubMedBert-MS-MARCO`. Rebuild ChromaDB index.

---

### TD-018: No Rate Limiting
**Severity:** HIGH
**Category:** Security / Cost Control
**File(s):** No rate limiting exists
**Description:** The API has no rate limiting. A single client can submit unlimited coding requests, running up LLM API costs indefinitely. With OpenAI GPT-4o at ~$0.005-0.015 per request, 10,000 requests/hour = $50-150/hour uncontrolled spend.
**Impact if not fixed:** Runaway API costs. Denial of service via resource exhaustion.
**Estimated effort:** 1 day
**Fix:** Add `slowapi` rate limiting: 10 coding requests/minute per API key.

---

### TD-019: CORS Configuration Accepts Credentials with Limited Origins
**Severity:** HIGH
**Category:** Security
**File(s):** `backend/app/main.py`
**Description:** `allow_credentials=True` combined with specific origin allowlist is better than wildcard, but the current origins (`localhost:3000`, `localhost:8080`) are development-only values. In production, these would need to be updated. The combination of `allow_credentials=True` with wildcard methods/headers is still a potential CSRF vector.
**Impact if not fixed:** CSRF attacks possible if frontend is compromised.
**Estimated effort:** 2 hours (configure proper origins + CSRF tokens)

---

### TD-020: Global Exception Handler Leaks Internal Type Names
**Severity:** HIGH
**Category:** Security
**File(s):** `backend/app/main.py`
**Description:** `type(exc).__name__` is included in the 500 error response. This leaks internal Python class names to external callers (e.g., `"type": "IntegrityError"` reveals SQLAlchemy is in use).
**Impact if not fixed:** Information disclosure to attackers. Aids in fingerprinting the tech stack.
**Estimated effort:** 30 minutes
**Fix:** Return generic error message without internal type names in production.

---

## Medium Severity

### TD-021: Dead Prompt Templates Never Invoked
**Severity:** MEDIUM
**Category:** Code Quality
**File(s):** `backend/app/llm/prompts.py`
**Description:** `ENTITY_EXTRACTION_PROMPT`, `SOAP_EXTRACTION_PROMPT`, and `REVIEW_SUMMARY_PROMPT` are defined but never imported or called anywhere in the codebase.
**Estimated effort:** 1 day (implement or delete)
**Fix:** Either implement the LLM-based extraction flows (replacing regex SOAP parsing with LLM extraction) or remove the dead templates.

---

### TD-022: utils/__init__.py is Empty
**Severity:** MEDIUM
**Category:** Code Quality
**File(s):** `backend/app/utils/__init__.py`
**Description:** The `utils/` module exists but contains only an empty `__init__.py`. There are no utility functions despite needing common helpers (datetime formatting, text cleaning, code normalization).
**Estimated effort:** 1 week (move shared utility logic here)

---

### TD-023: No Request/Response Logging Middleware
**Severity:** MEDIUM
**Category:** Observability
**File(s):** `backend/app/main.py`
**Description:** There is no middleware logging request duration, status codes, or endpoint paths. Debugging performance issues or errors in production requires parsing application-level logs.
**Estimated effort:** 1 day
**Fix:** Add structlog request middleware logging method, path, status_code, duration_ms, request_id.

---

### TD-024: Health Endpoint Status Logic Bug
**Severity:** MEDIUM
**Category:** Correctness
**File(s):** `backend/app/api/routes/health.py` line 64
**Description:** `overall_status = "healthy" if (kb_loaded or True) else "degraded"` — the `or True` makes this expression always evaluate to `True`. The health endpoint always returns `"healthy"` regardless of actual component states.
**Estimated effort:** 30 minutes
**Fix:** `overall_status = "healthy" if (llm_available and kb_loaded and nlp_loaded) else "degraded"`

---

### TD-025: Document ID Not Persisted
**Severity:** MEDIUM
**Category:** Data Model
**File(s):** `backend/app/api/routes/documents.py`
**Description:** `DocumentUploadResponse.document_id` is a fresh UUID generated per request but never saved to the database. There is no way to retrieve a previously uploaded document's extracted text.
**Estimated effort:** 1 week (add Document table, store extracted text)

---

### TD-026: session_id in ReviewDecision Body Must Match Path Parameter
**Severity:** MEDIUM
**Category:** API Design
**File(s):** `backend/app/api/routes/coding.py`, `backend/app/models/schemas.py`
**Description:** `ReviewDecision.session_id` is a field in the request body, but the route also takes `session_id` as a path parameter. The body's `session_id` is never validated against the path parameter — they can silently diverge.
**Estimated effort:** 2 hours
**Fix:** Remove `session_id` from `ReviewDecision` schema (it's redundant with the path parameter) or add validation that they match.

---

### TD-027: Modifier Logic is a Placeholder
**Severity:** MEDIUM
**Category:** Clinical Functionality
**File(s):** `backend/app/models/schemas.py`, `backend/app/agents/medical_coder.py`
**Description:** The `modifiers` field exists on `MedicalCode` and is passed through from the LLM response, but there is no modifier suggestion logic. The LLM is not given guidance on when to apply modifiers, and no validation of modifier applicability occurs.
**Estimated effort:** 4-6 weeks (full modifier logic engine)

---

### TD-028: No Re-ranking of RAG Candidates
**Severity:** MEDIUM
**Category:** Clinical Accuracy
**File(s):** `backend/app/rag/retriever.py`
**Description:** Retrieved code candidates are sorted by vector cosine similarity only. No cross-encoder re-ranking, no BM25 hybrid, no clinical relevance scoring.
**Estimated effort:** 2-3 weeks

---

### TD-029: ICD-10 Code Normalization Inconsistency
**Severity:** MEDIUM
**Category:** Data Quality
**File(s):** `backend/app/agents/medical_coder.py`, `backend/app/rag/retriever.py`
**Description:** Both `_build_medical_codes()` in the agent and `lookup_code()` in the retriever implement their own period/no-period normalization logic independently, leading to duplicated and potentially inconsistent normalization. The `normalize_code()` function in `validator.py` is the canonical implementation but is not used by either.
**Estimated effort:** 2 hours
**Fix:** All code normalization should call `validator.normalize_code()`.

---

### TD-030: No Pagination on Session History
**Severity:** MEDIUM
**Category:** API Design
**File(s):** `backend/app/api/routes/coding.py`
**Description:** There is no endpoint to list coding sessions with pagination. Only individual session retrieval by ID is supported. To build a history view, a client would need to know all session IDs in advance.
**Estimated effort:** 1 week (add GET /coding/sessions endpoint with pagination)

---

### TD-031: Review Queue Does Not Expire Sessions
**Severity:** MEDIUM
**Category:** Data Model
**File(s):** `backend/app/models/schemas.py`
**Description:** `ReviewQueueItem.expires_at` and `CodingSession` have `auto_expire_hours=72` configured, but no expiration mechanism is implemented. Sessions sit in NEEDS_REVIEW indefinitely.
**Estimated effort:** 1 week (background job or scheduled task for expiration)

---

### TD-032: HCPCS Collection Returns Wrong `where_filter`
**Severity:** MEDIUM
**Category:** Correctness
**File(s):** `backend/app/rag/retriever.py`
**Description:** In `_search()`, `where_filter = {"code_type": code_type}`. For HCPCS, `code_type = "HCPCS"`. However, ChromaDB filter on a single-key dict with no additional filters may throw an exception in some versions. The code has `where_filter if len(where_filter) > 1 else None` — so single-key filters are currently set to `None` (no filter applied). This means any search on any collection returns all code types, not just the requested type.
**Estimated effort:** 2 hours
**Fix:** Apply single-key filters properly or remove filter when only one condition exists.

---

### TD-033: No Retry Logic for LLM Calls
**Severity:** MEDIUM
**Category:** Reliability
**File(s):** `backend/app/llm/provider.py`
**Description:** LLM API calls have no retry logic. Transient failures (network timeouts, rate limit 429s from OpenAI/Anthropic) cause immediate errors. `tenacity` is installed but unused.
**Estimated effort:** 1 day
**Fix:** Use `tenacity` with exponential backoff: `@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))`

---

### TD-034: `patient_id` and `encounter_id` Accept PHI
**Severity:** MEDIUM
**Category:** HIPAA Compliance
**File(s):** `backend/app/models/schemas.py`
**Description:** `CodingRequest.patient_id` accepts any string. Documentation says "De-identified patient reference" but there is no enforcement or validation. A caller could easily pass a real MRN or patient name.
**Estimated effort:** 1 day (documentation + server-side validation warning)

---

## Low Severity

### TD-035: `requirements.txt` Pins httpx Twice
**Severity:** LOW
**Category:** Dependencies
**File(s):** `backend/requirements.txt`
**Description:** `httpx==0.28.1` appears twice (once under Core API Framework, once under Testing).
**Estimated effort:** 5 minutes

---

### TD-036: No `.gitignore` File
**Severity:** LOW
**Category:** Repository hygiene
**File(s):** Repository root
**Description:** No `.gitignore` file is present. The `backend/venv/` directory (containing gigabytes of Python packages) and `backend/.env` (containing secrets) could easily be committed.
**Estimated effort:** 15 minutes
**Fix:** Create `.gitignore` with: `venv/`, `.env`, `*.pyc`, `__pycache__/`, `*.db`, `knowledge_base/indices/`

---

### TD-037: `KnowledgeBaseEntry` Table Barely Used
**Severity:** LOW
**Category:** Code Quality
**File(s):** `backend/app/models/database.py`
**Description:** The `KnowledgeBaseEntry` (knowledge_base_log) table is defined but never written to. The indexer runs without logging to this table.
**Estimated effort:** 1 day (implement logging calls in indexer)

---

### TD-038: Confidence Score Hardcoded to 0.85 Without UMLS
**Severity:** LOW
**Category:** Data Quality
**File(s):** `backend/app/nlp/entity_extractor.py` line 106
**Description:** `entity.confidence = 0.85` is set for all entities when UMLS linking is unavailable. This is a meaningless hardcoded value that misrepresents actual NLP confidence.
**Estimated effort:** 2 hours (use spaCy's `ent.label_score_` or derive from model score)

---

### TD-039: No OpenTelemetry / Distributed Tracing
**Severity:** LOW
**Category:** Observability
**File(s):** `backend/app/main.py`
**Description:** Despite `opentelemetry-sdk` and `opentelemetry-exporter-otlp-proto-grpc` being installed in venv, no tracing or metrics instrumentation exists.
**Estimated effort:** 1-2 days (add FastAPI instrumentation, database instrumentation)

---

### TD-040: `auto_expire_hours` Configuration Not Implemented
**Severity:** LOW
**Category:** Configuration
**File(s):** `backend/app/config.py`
**Description:** `auto_expire_hours: int = 72` is defined and loaded from `.env` but never referenced in any route or background job.
**Estimated effort:** 1 week (implement background expiration job)

---

### TD-041: No Input Sanitization for Code Search Query
**Severity:** LOW
**Category:** Security
**File(s):** `backend/app/api/routes/coding.py`
**Description:** The `q` parameter in `/search` passes directly into `embed_texts()` without sanitization. Very long strings could cause embedding model memory issues.
**Estimated effort:** 2 hours (add `q` length limit, strip whitespace)

---

### TD-042: No Version Header in API Responses
**Severity:** LOW
**Category:** API Design
**File(s):** `backend/app/main.py`
**Description:** API responses do not include an `X-API-Version` response header. Clients cannot determine which version of the API served their request.
**Estimated effort:** 1 hour (add middleware to inject version header)

---

## Debt Reduction Priority Order

For maximum impact-per-effort, address in this order:

1. TD-001 — Rotate exposed API key (2 hours, stops bleeding)
2. TD-008 — Install scispaCy (4 hours, immediate NLP improvement)
3. TD-006 — HCPCS full dataset (2 hours, free CMS data)
4. TD-004 — Fix blocking async calls (3-5 days, system stability)
5. TD-024 — Fix health endpoint bug (30 minutes, correctness)
6. TD-035 — Remove duplicate httpx pin (5 minutes)
7. TD-036 — Add .gitignore (15 minutes)
8. TD-002 — Configure API keys (4 hours, security)
9. TD-017 — Switch to medical embedding model (4 hours, accuracy)
10. TD-013 — Remove dead dependencies (2 hours, cleanliness)
11. TD-014 — Fix ChromaDB version pin (2 hours, correctness)
12. TD-033 — Add LLM retry logic (1 day, reliability)
13. TD-011 — Migrate to PostgreSQL (3-5 days, production readiness)
14. TD-012 — Initialize Alembic migrations (1 day, operations)
15. TD-018 — Add rate limiting (1 day, cost control)
