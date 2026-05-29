# Production Readiness Assessment — AI Medical Coding Agent
**Assessment Date:** 2026-05-28
**System Version:** 1.0.0
**Verdict: NOT PRODUCTION READY**

---

## Scorecard

| Category | Score | Justification |
|----------|-------|---------------|
| Backend Architecture | 6/10 | Clean async FastAPI, proper patterns; SQLite limits scale |
| AI/LLM Accuracy | 4/10 | Good prompting; fatally limited by CPT dataset (46 codes) |
| Medical Coding Completeness | 3/10 | ICD-10 solid; CPT/HCPCS are demo-only |
| Knowledge Base | 4/10 | ICD-10 excellent; CPT/HCPCS critically incomplete |
| API Design | 5/10 | Reasonable REST design; no versioning strategy, no pagination on all endpoints |
| Security | 1/10 | API key exposed in repo; open access in dev mode; no encryption |
| HIPAA Compliance | 0/10 | PHI unencrypted; no audit trail; no BAA capability; no user identity |
| Authentication & Authorization | 1/10 | Static API key only; no RBAC; no user management |
| Performance & Scalability | 3/10 | Blocking async calls; SQLite; no caching; no queuing |
| Frontend / UX | 0/10 | No frontend exists |
| Testing Coverage | 3/10 | ~25 unit tests; no integration test suite; no load tests |
| DevOps / Infrastructure | 2/10 | No Docker; no CI/CD; no deployment config; no monitoring |
| **OVERALL** | **3/10** | **Solid prototype; not deployable for real clinical use** |

---

## What Works Well

### Architectural Strengths
- **Clean code structure** — well-organized module hierarchy, single responsibility per file
- **Pydantic v2 schemas** — comprehensive request/response validation with proper field constraints
- **Async database layer** — SQLAlchemy 2.0 async with proper session lifecycle (commit/rollback)
- **LLM provider abstraction** — clean interface supporting Ollama, Anthropic, and OpenAI
- **Lifespan management** — correct startup/shutdown ordering with graceful degradation
- **Structured error handling** — global exception handler, per-component try/catch with warnings
- **ChromaDB HNSW indexing** — efficient vector search, persisted across restarts

### AI/NLP Strengths
- **System prompt quality** — CPC/CCS persona, correct coding principles, evidence citation requirement
- **Temperature = 0.05** — near-deterministic LLM output, appropriate for coding
- **Hallucination guard** — LLM restricted to candidate list only (major accuracy safeguard)
- **ICD-10-CM knowledge base** — 74,260 FY2026 codes indexed and searchable
- **Abbreviation expansion** — 40+ clinical abbreviations correctly expanded before NLP
- **SOAP section parsing** — handles common note formats with fallback patterns
- **Code format validation** — regex patterns for ICD-10-CM, CPT, HCPCS

### Human-in-the-Loop
- **Review queue** — NEEDS_REVIEW status, paginated queue endpoint
- **Confidence thresholds** — configurable auto-approve (0.90) and review (0.70) thresholds
- **Review decision API** — approve/reject individual codes with reviewer notes
- **Sequencing warnings** — primary diagnosis count, symptom code conflicts

### Document Processing
- **Multi-format support** — PDF (text + OCR fallback), DOCX, TXT, images
- **Scanned PDF detection** — auto-detects digital vs scanned PDFs
- **Dual PDF library** — PyMuPDF with pdfplumber fallback

---

## Critical Blockers for Production

### Blocker 1: Exposed Live API Key (IMMEDIATE)
**Severity: CRITICAL — Stop everything**
The OpenAI API key `sk-proj-vfuPcoNt...` is committed in plaintext to `backend/.env` AND `.env.example`. This key must be revoked immediately. Any git clone or repository access grants full API usage.

**Fix:** Rotate the OpenAI key immediately. Scrub from git history. Never commit `.env` to version control. Add `.env` to `.gitignore`.

### Blocker 2: Zero Authentication (CRITICAL for production)
**Severity: CRITICAL**
`ALLOWED_API_KEYS` is empty in `backend/.env`. Every endpoint is completely open. There is no user identity, no RBAC, no session management.

**Fix:** Generate and configure API keys at minimum. Implement JWT authentication for a production system.

### Blocker 3: PHI Stored Unencrypted (HIPAA Violation)
**Severity: CRITICAL — Legal liability**
Full clinical notes are stored as plaintext `TEXT` columns in an unencrypted SQLite file. Patient names, diagnoses, medications, and clinical details are exposed to anyone with filesystem access.

**Fix:** Field-level encryption for `clinical_text`, `soap_json`, `extracted_entities_json`. Minimum: SQLite encryption (SQLCipher) or migrate to encrypted PostgreSQL.

### Blocker 4: CPT Dataset Contains 46 of ~10,000+ Codes
**Severity: CRITICAL — Clinical usability**
The system can only match CPT codes against 46 hardcoded entries. Any surgical, specialty, radiological, or advanced procedure will fail to retrieve the correct CPT code. The LLM will either flag everything for review or hallucinate codes not in the candidate list.

**Fix:** Procure AMA CPT license (mandatory for commercial use) and ingest the full CPT dataset. See ENTERPRISE_FEATURE_GAP.md for alternatives.

### Blocker 5: Blocking Async Operations (Performance)
**Severity: HIGH — System stability under load**
Ollama calls, Anthropic calls, SentenceTransformer embedding, spaCy inference, ChromaDB queries, and OCR are all synchronous operations inside async handlers. Under concurrent load (>2 simultaneous requests), these will block each other, causing cascading timeouts.

**Fix:** Wrap all CPU-bound and blocking I/O operations in `asyncio.run_in_executor()` or migrate to truly async variants where available.

### Blocker 6: SQLite Database
**Severity: HIGH — Scale limitation**
SQLite cannot handle concurrent writes from multiple workers. Single-file database cannot be shared across horizontal scaling instances. No connection pooling for production load.

**Fix:** Migrate to PostgreSQL with `asyncpg` driver. Configuration comment for PostgreSQL URL is already present in `.env.example`.

### Blocker 7: No Frontend
**Severity: HIGH — Usability**
There is no web interface. Coders must interact via raw HTTP API calls. This makes the system unusable for the intended audience (medical coders, CDI specialists, billers).

**Fix:** Build a React/Next.js frontend. See IMPROVEMENT_ROADMAP.md Phase 1.

### Blocker 8: No Audit Trail
**Severity: HIGH — HIPAA / Compliance**
HIPAA requires an audit trail for all PHI access. There is no logging of who accessed patient records, what codes were suggested, or what human review decisions were made at the individual user level (no user identity exists).

**Fix:** Add immutable `AuditLog` table. Implement middleware to log all PHI access events. Include user identity, timestamp, action, and record identifier.

### Blocker 9: scispaCy Not Installed
**Severity: HIGH — Clinical NLP accuracy**
The `.env` sets `SCISPACY_MODEL=en_core_web_sm`. The standard English spaCy model will extract PERSON, ORG, GPE entities from clinical text — not DISEASE, DISORDER, PROCEDURE, CHEMICAL. Clinical entity extraction quality is severely degraded.

**Fix:** Install `scispacy` and `en_core_sci_lg`. Set `SCISPACY_MODEL=en_core_sci_lg` in `.env`.

### Blocker 10: No Database Migrations
**Severity: MEDIUM — Operations**
Alembic is installed but no migration scripts exist. Any schema change (adding audit fields, new indexes, new columns) requires destroying and recreating the database, losing all historical coding data.

**Fix:** Initialize Alembic, generate baseline migration, and follow migration-based schema evolution going forward.

---

## Risk Assessment Table

| Risk | Probability | Impact | Risk Level | Mitigation |
|------|-------------|--------|------------|------------|
| API key abuse (already exposed) | Certain | Financial loss | CRITICAL | Revoke key immediately |
| PHI breach (unencrypted storage) | High if deployed | Legal/regulatory | CRITICAL | Encrypt clinical_text field |
| CPT coding failures (wrong codes billed) | Certain (46 codes) | Claim denials, fraud risk | CRITICAL | Procure full CPT dataset |
| Event loop stall under load | High (any concurrency) | System unavailability | HIGH | Wrap blocking calls in executor |
| HIPAA audit failure | Certain if deployed | $100K-$1.9M fines | CRITICAL | Full HIPAA compliance program |
| Data loss (SQLite corruption) | Medium | All coding history lost | HIGH | Migrate to PostgreSQL + backups |
| Hallucinated codes submitted to payer | Medium (weak scispaCy) | Claim denials, fraud | HIGH | Enable scispaCy, stricter validation |
| Unauthorized API access | Certain (empty key list) | Data exposure | CRITICAL | Configure API keys |
| LLM cost overrun (GPT-4o with no rate limiting) | Medium | Budget impact | MEDIUM | Add rate limiting, cost controls |
| Dependency vulnerabilities (unused packages) | Medium | Security exposure | MEDIUM | Remove unused dependencies |

---

## HIPAA Compliance Gap Analysis

### HIPAA Security Rule — Technical Safeguards

| Requirement | Status | Gap |
|-------------|--------|-----|
| Access Control (164.312(a)) | FAIL | No user authentication, no RBAC |
| Audit Controls (164.312(b)) | FAIL | No PHI access logging |
| Integrity Controls (164.312(c)) | FAIL | No data integrity verification |
| Transmission Security (164.312(e)) | FAIL | No TLS enforcement, no transport security |
| Encryption at Rest | FAIL | Clinical text stored in plaintext SQLite |
| Automatic Logoff | N/A | No session management |
| Unique User Identification | FAIL | No user identity concept |
| Emergency Access Procedure | FAIL | Not implemented |

### HIPAA Security Rule — Administrative Safeguards

| Requirement | Status | Gap |
|-------------|--------|-----|
| Risk Analysis | FAIL | Not documented |
| Workforce Training | N/A | Prototype — no workforce |
| Access Management | FAIL | No user provisioning |
| Business Associate Agreements | FAIL | No BAA capability |
| Contingency Plan | FAIL | No backup/recovery procedures |
| Evaluation | FAIL | No security review process |

### HIPAA Privacy Rule — Minimum Necessary

| Requirement | Status | Gap |
|-------------|--------|-----|
| Minimum Necessary PHI | PARTIAL | Stores full clinical text when only assessment needed |
| De-identification | FAIL | No PHI de-identification capability |
| Data Retention | FAIL | No configurable retention policy, no deletion |

### What Would Be Needed for HIPAA Compliance

1. Business Associate Agreement (BAA) with cloud providers (OpenAI, Anthropic if used)
2. Field-level encryption for all PHI columns
3. TLS 1.2+ for all API traffic
4. User authentication with unique IDs
5. Role-based access control
6. Immutable audit logs with timestamps
7. PHI access logging
8. Secure key management (AWS KMS, HashiCorp Vault, etc.)
9. Data backup and recovery procedures
10. Workforce security training program documentation
11. Risk analysis documentation
12. De-identification pipeline for any data used in model training/testing

**Bottom line:** This system would fail a HIPAA audit across all three rules (Privacy, Security, Breach Notification). It cannot legally process real patient data in the United States without a comprehensive compliance program.

---

## Minimum Viable Production Requirements

Before this system can process any real patient data, the following are non-negotiable:

1. Rotate the exposed OpenAI API key
2. Add `.env` to `.gitignore`
3. Implement JWT authentication with user identity
4. Encrypt `clinical_text` and related PHI columns at rest
5. Switch database to PostgreSQL with TLS
6. Implement immutable audit logging
7. Wrap all blocking operations in thread pool executor
8. Install `en_core_sci_lg` for clinical NER
9. Procure and ingest complete CPT dataset
10. Obtain BAAs from all PHI-touching vendors
11. Deploy with TLS termination (nginx/AWS ALB)
12. Build a frontend for actual user workflow
