# Improvement Roadmap — AI Medical Coding Agent
**Document Date:** 2026-05-28
**Total Estimated Timeline:** 12-18 months to enterprise-grade platform

---

## Phase Overview

| Phase | Timeline | Focus | Investment |
|-------|----------|-------|------------|
| Phase 1 | Weeks 1-2 | Critical security & stability fixes | 1-2 engineers |
| Phase 2 | Weeks 2-8 | Core production features | 2-3 engineers |
| Phase 3 | Months 2-4 | Advanced AI & enterprise features | 3-5 engineers |
| Phase 4 | Months 4-12 | Full enterprise platform | 5-10 engineers |

---

## Phase 1: Critical Fixes (Weeks 1-2)
**Goal:** Make the system safe, stable, and minimally viable for demonstration

### Week 1: Security Emergency

**1.1 Rotate Exposed API Key (Day 1 — Immediate)**
```
Action: Revoke sk-proj-vfuPcoNt... at platform.openai.com
Action: Generate new key, store in secrets manager (not .env)
Action: Add .env to .gitignore immediately
Action: Run git-filter-repo to purge key from git history
Cost: 0 hours engineering / $0
```

**1.2 Fix API Authentication**
```python
# Replace static API key with proper JWT
# backend/app/api/dependencies.py

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401)
        return user_id
    except JWTError:
        raise HTTPException(status_code=401)
```
Effort: 3-5 days. Includes: login endpoint, token generation, user table.

**1.3 Fix Blocking Async Calls**
```python
# backend/app/llm/provider.py — wrap all sync calls

import asyncio
from functools import partial

async def _ollama_complete(self, system_prompt, user_message, temperature, max_tokens):
    loop = asyncio.get_event_loop()
    sync_call = partial(
        ollama_lib.chat,
        model=settings.llm_model,
        messages=[...],
        options={...}
    )
    response = await loop.run_in_executor(None, sync_call)
    return response["message"]["content"]

# Apply same pattern to Anthropic, spaCy inference, ChromaDB, and SentenceTransformer
```
Effort: 2-3 days.

**1.4 Install scispaCy and Configure**
```bash
pip install scispacy==0.5.5
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_lg-0.5.4.tar.gz
```
Then update `.env`:
```
SCISPACY_MODEL=en_core_sci_lg
ENABLE_UMLS_LINKING=true
```
Effort: 4 hours.

**1.5 Remove Dead Dependencies**
```
Remove from requirements.txt:
- langchain==0.3.13
- langchain-core==0.3.28
- langchain-community==0.3.13
- langchain-ollama==0.2.2
- langchain-anthropic==0.3.3
- llama-index==0.12.7
- llama-index-vector-stores-chroma==0.4.1
- llama-index-embeddings-huggingface==0.4.0
(python-jose and passlib stay — needed for JWT in 1.2)
Saves ~200MB of packages + reduces attack surface
```
Effort: 2 hours.

### Week 2: Database & Knowledge Base

**1.6 Migrate to PostgreSQL**
```python
# backend/.env
DATABASE_URL=postgresql+asyncpg://medcoder:password@localhost:5432/medical_coder

# Add asyncpg to requirements.txt
asyncpg==0.30.0

# Initialize Alembic
alembic init alembic
alembic revision --autogenerate -m "initial_schema"
alembic upgrade head
```
Effort: 3-5 days (including migration scripts).

**1.7 Add PHI Encryption**
```python
# backend/app/models/database.py — use SQLAlchemy-Utils encryption
from sqlalchemy_utils import StringEncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import AesGcmEngine

class CodingSession(Base):
    clinical_text = Column(
        StringEncryptedType(Text, settings.encryption_key, AesGcmEngine, 'pkcs5'),
        nullable=False
    )
```
Alternatively: application-level AES-256-GCM encryption before insert.
Effort: 3-5 days.

**1.8 Ingest Full HCPCS Dataset**
```python
# Download from CMS — free, no license required
# URL: https://www.cms.gov/files/zip/2025-alpha-numeric-hcpcs-file.zip
# The build_knowledge_base.py script already has this download logic
# Just run: python knowledge_base/scripts/build_knowledge_base.py
```
The script already attempts this download. Just run it with internet access.
Effort: 2 hours (run script + verify index).

**1.9 CPT Data Strategy**
Option A (Recommended for production):
- Contact AMA: https://www.ama-assn.org/practice-management/cpt
- Request CodeManager API license (annual fee ~$3K-15K)
- Ingest via existing `_load_cpt_codes()` which reads `cpt_codes.json`

Option B (Development/Research):
- Download CMS Physician Fee Schedule (MPFS) from CMS.gov
- Contains all CPT codes with descriptions (publicly available Medicare data)
- Good for development; confirm licensing for commercial use
- Parse and convert to the existing JSON format

Option C (Immediate, limited):
- Expand `_get_builtin_cpt_codes()` from 46 to 500+ most common codes
- Cover all surgery, radiology, pathology, medicine, anesthesia sections
- Better than 46 but not production-quality

**1.10 Add Audit Logging**
```python
# New table in database.py
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), nullable=False, index=True)
    action = Column(String(50), nullable=False)  # "code_request", "review_submit", "lookup"
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(100), nullable=True)
    patient_id = Column(String(100), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

# Add middleware to auto-log PHI access
```
Effort: 2-3 days.

---

## Phase 2: Core Production Features (Weeks 2-8)
**Goal:** Production-ready backend with complete coding coverage

### Weeks 2-4: Frontend (Parallel track)

**2.1 React Frontend — Minimum Viable**

**Recommended Stack:**
- Next.js 14 (App Router) — SSR for faster initial load
- Tailwind CSS + shadcn/ui — rapid UI component development
- TanStack Query (React Query) — API state management
- React Hook Form + Zod — form validation
- Recharts — analytics charts

**Required Screens (MVP):**
```
Screen 1: Login / Authentication
Screen 2: Coding Workspace
  - Text input / document upload
  - Specialty/document type selectors
  - Submit button
  - Results panel: code list with confidence badges
  - Evidence viewer
  - Approve/reject individual codes
Screen 3: Review Queue
  - Paginated list of NEEDS_REVIEW sessions
  - Filter by specialty, date, status
  - Quick review action
Screen 4: Session History
  - Searchable list of all coding sessions
  - Status badges, date, specialty
Screen 5: Health/Status Dashboard
  - System health indicators
  - LLM availability
  - Knowledge base code counts
```

Estimated effort: 6-8 weeks for 1 frontend engineer (MVP only).

### Weeks 3-6: Advanced Coding Features

**2.2 E/M Complexity Scoring**

Add Medical Decision Making (MDM) scoring to determine correct E/M level:
```python
# New file: backend/app/coding/em_scorer.py

class EMComplexityScorer:
    """
    Scores E/M encounters per 2021 AMA E/M guidelines.
    Three elements: Problems, Data, Risk
    """
    
    def score_mdm(self, soap: SOAPSection, entities: List[ExtractedEntity]) -> EMLevel:
        problems_score = self._score_problems(entities)
        data_score = self._score_data(soap)
        risk_score = self._score_risk(soap, entities)
        # MDM level = minimum 2 of 3 elements at that level
        return self._determine_level(problems_score, data_score, risk_score)
    
    def _score_problems(self, entities) -> int:
        # Minimal=1, Low=2, Moderate=3, High=4
        # Based on number of diagnoses, new vs established, chronic vs acute
        ...
    
    def _score_data(self, soap) -> int:
        # Minimal=1, Low=2, Moderate=3, High=4
        # Based on data reviewed: labs, imaging, records
        ...
    
    def _score_risk(self, soap, entities) -> int:
        # Minimal, Low, Moderate, High
        # Based on prescription drug management, procedures, social determinants
        ...
```
Estimated effort: 3-4 weeks.

**2.3 Modifier Logic Engine**

```python
# New file: backend/app/coding/modifier_engine.py

COMMON_MODIFIERS = {
    "26": "Professional component",
    "TC": "Technical component",
    "25": "Significant, separately identifiable E/M service",
    "59": "Distinct procedural service",
    "51": "Multiple procedures",
    "RT": "Right side",
    "LT": "Left side",
    "50": "Bilateral procedure",
    "22": "Increased procedural services",
    "52": "Reduced services",
    "76": "Repeat procedure or service by same physician",
    "77": "Repeat procedure by another physician",
    "91": "Repeat clinical diagnostic laboratory test",
}

class ModifierEngine:
    def suggest_modifiers(self, codes: List[MedicalCode], soap: SOAPSection) -> List[MedicalCode]:
        """Apply appropriate modifiers based on clinical context."""
        for code in codes:
            if code.code_type == CodeType.CPT:
                # Check for bilateral procedures
                # Check for technical/professional component split
                # Check for multiple procedures
                # Check for laterality
                ...
```
Estimated effort: 4-6 weeks (modifier logic is complex).

**2.4 Negation Detection**

```python
# backend/app/nlp/negation_detector.py
# Using negspaCy or custom rule-based negation

import negspacy  # pip install negspacy

def add_negation_detection(nlp):
    """Add negation detection to the spaCy pipeline."""
    negex = nlp.add_pipe(
        "negex",
        config={"neg_termset": "en_clinical", "ent_types": ["DISEASE", "FINDING"]}
    )
    return nlp

def filter_negated_entities(entities: List[ExtractedEntity], doc) -> List[ExtractedEntity]:
    """Remove entities that are negated or uncertain."""
    confirmed = []
    for ent in doc.ents:
        if not ent._.negex:  # negspaCy flag
            confirmed.append(ent)
    return confirmed
```
Estimated effort: 1-2 weeks.

**2.5 Temporal Reasoning (Acute vs Chronic)**

Add temporal classification to entities:
```python
# In entity_extractor.py — add temporal analysis
CHRONIC_INDICATORS = ["chronic", "history of", "h/o", "longstanding", "known", "established"]
ACUTE_INDICATORS = ["acute", "new onset", "sudden", "exacerbation", "presenting with"]

def classify_temporal_status(entity_text: str, context_window: str) -> str:
    """Classify entity as acute, chronic, or unknown."""
    context_lower = context_window.lower()
    if any(ind in context_lower for ind in CHRONIC_INDICATORS):
        return "chronic"
    elif any(ind in context_lower for ind in ACUTE_INDICATORS):
        return "acute"
    return "unknown"
```
Estimated effort: 1-2 weeks.

### Weeks 5-8: Infrastructure

**2.6 Add Rate Limiting**
```python
# Using slowapi (FastAPI rate limiter)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@router.post("/code")
@limiter.limit("10/minute")  # 10 coding requests per minute per IP
async def code_clinical_note(request: Request, ...):
    ...
```
Estimated effort: 1 day.

**2.7 Redis Caching**
```python
# Cache embedding results and frequent code lookups
import redis.asyncio as redis

CACHE_TTL = 3600  # 1 hour

async def get_cached_embedding(text: str) -> Optional[List[float]]:
    cache_key = f"embedding:{hashlib.md5(text.encode()).hexdigest()}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    return None

async def cache_embedding(text: str, embedding: List[float]):
    cache_key = f"embedding:{hashlib.md5(text.encode()).hexdigest()}"
    await redis_client.setex(cache_key, CACHE_TTL, json.dumps(embedding))
```
Estimated effort: 3-5 days. Impact: eliminates re-embedding for duplicate queries.

**2.8 Celery Task Queue for Long-Running Operations**
```python
# For async document processing and LLM calls
from celery import Celery

celery_app = Celery("medical_coder", broker="redis://localhost:6379")

@celery_app.task
def process_coding_task(request_data: dict) -> dict:
    """Process coding asynchronously, notify via webhook or polling."""
    ...

# Route:
@router.post("/code/async")
async def code_async(request: CodingRequest):
    task = process_coding_task.delay(request.model_dump())
    return {"task_id": task.id, "status": "queued"}

@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    task = AsyncResult(task_id)
    return {"status": task.status, "result": task.result}
```
Estimated effort: 1-2 weeks.

**2.9 Docker Compose Configuration**

```yaml
# docker-compose.yml
version: '3.9'

services:
  api:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql+asyncpg://medcoder:password@postgres:5432/medical_coder
      - REDIS_URL=redis://redis:6379
    depends_on: [postgres, redis]
    ports: ["8000:8000"]

  worker:
    build: ./backend
    command: celery -A app.tasks worker --loglevel=info
    depends_on: [postgres, redis]

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: medical_coder
      POSTGRES_USER: medcoder
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]  # Optional GPU

volumes:
  postgres_data:
  ollama_data:
```
Estimated effort: 1-2 days.

---

## Phase 3: Advanced AI Features (Months 2-4)
**Goal:** Clinical-grade AI accuracy and workflow integration

### Month 2: Enhanced AI Pipeline

**3.1 Upgrade Embedding Model**

Switch from `all-MiniLM-L6-v2` to a clinical biomedical model:
```
# Option A: SapBERT (best for medical entity matching)
EMBEDDING_MODEL=cambridgeltl/SapBERT-from-PubMedBERT-fulltext

# Option B: S-PubMedBert (already in config default — just set it)
EMBEDDING_MODEL=pritamdeka/S-PubMedBert-MS-MARCO

# Option C: Med-BERT (strongest clinical understanding)
EMBEDDING_MODEL=Charangan/MedBERT
```
Rebuild ChromaDB indices after model change.
Estimated effort: 1 day (model swap) + 2-4 hours (reindex 74K ICD-10 codes).

**3.2 Hybrid Retrieval (BM25 + Dense)**

Add BM25 keyword retrieval alongside dense vector search:
```python
# backend/app/rag/hybrid_retriever.py
from rank_bm25 import BM25Okapi

class HybridCodeRetriever:
    def search(self, query: str, top_k: int = 15) -> List[Dict]:
        # Dense vector search
        dense_results = self._dense_search(query, top_k * 2)
        # BM25 keyword search
        bm25_results = self._bm25_search(query, top_k * 2)
        # Reciprocal Rank Fusion
        return self._rrf_merge(dense_results, bm25_results, top_k)
    
    def _rrf_merge(self, results_a, results_b, k=60):
        """Reciprocal Rank Fusion for combining two ranked lists."""
        scores = {}
        for rank, doc in enumerate(results_a):
            scores[doc['code']] = scores.get(doc['code'], 0) + 1/(rank + k)
        for rank, doc in enumerate(results_b):
            scores[doc['code']] = scores.get(doc['code'], 0) + 1/(rank + k)
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```
Estimated effort: 2-3 weeks. Expected retrieval accuracy improvement: 10-20%.

**3.3 Cross-Encoder Re-Ranking**

Add a cross-encoder to re-rank the top-k retrieved codes:
```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

def rerank_candidates(query: str, candidates: List[Dict], top_k: int = 15) -> List[Dict]:
    """Re-rank candidates using cross-encoder for higher precision."""
    pairs = [(query, f"{c['code']}: {c['description']}") for c in candidates]
    scores = reranker.predict(pairs)
    ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
    return [c for c, _ in ranked[:top_k]]
```
Estimated effort: 1-2 weeks.

**3.4 Specificity Guidance Engine**

```python
# backend/app/coding/specificity_engine.py

class SpecificityEngine:
    """Guides LLM to select most specific code."""
    
    def get_specificity_hints(self, code: str, clinical_text: str) -> List[str]:
        """Return hints for coding to higher specificity."""
        hints = []
        # ICD-10 hierarchy analysis
        # Check if more specific code exists (subcategory vs category)
        # Check laterality requirements
        # Check acuity requirements (initial vs subsequent encounter)
        # Check complication specificity
        return hints
    
    def check_laterality_required(self, code: str) -> bool:
        """Check if this code requires laterality specification."""
        # Build laterality requirement map from ICD-10 tabular
        ...
    
    def check_7th_character_required(self, code: str) -> Optional[Dict]:
        """Check if this code requires 7th character extension."""
        # S/T codes require encounter type (A/D/S)
        # Certain other codes require episode type
        ...
```
Estimated effort: 3-4 weeks.

**3.5 Long Note Handling (Token Window Management)**

The current 3,000-character truncation loses critical information for complex notes:
```python
# backend/app/agents/medical_coder.py

def _extract_coding_relevant_segments(self, text: str, max_chars: int = 8000) -> str:
    """
    Intelligently extract the most coding-relevant segments from a long note.
    Priority: Assessment > Plan > Discharge Diagnosis > HPI > Medications
    """
    soap = parse_soap_note(text)
    segments = []
    
    # Always include full Assessment (primary coding source)
    if soap.assessment:
        segments.append(f"ASSESSMENT:\n{soap.assessment}")
    
    # Include full Plan
    if soap.plan and len(segments) < max_chars:
        segments.append(f"PLAN:\n{soap.plan}")
    
    # Add HPI if space allows
    if soap.subjective and len("\n\n".join(segments)) < max_chars * 0.7:
        segments.append(f"HISTORY:\n{soap.subjective[:1000]}")
    
    result = "\n\n".join(segments)
    return result[:max_chars] if len(result) > max_chars else result
```
Estimated effort: 1 week.

### Month 3: FHIR & EHR Integration

**3.6 FHIR R4 Input/Output**

```python
# backend/app/fhir/parser.py — FHIR R4 ClinicalImpression / Condition resources
from fhir.resources.R4B import bundle, condition, clinicalimpression

class FHIRParser:
    def extract_text_from_composition(self, fhir_composition: dict) -> str:
        """Extract clinical text from FHIR Composition resource."""
        ...
    
    def extract_text_from_diagnosticreport(self, report: dict) -> str:
        """Extract narrative from FHIR DiagnosticReport."""
        ...

class FHIROutputFormatter:
    def to_fhir_condition(self, code: MedicalCode, patient_id: str) -> dict:
        """Convert MedicalCode to FHIR R4 Condition resource."""
        return {
            "resourceType": "Condition",
            "code": {
                "coding": [{
                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                    "code": code.code,
                    "display": code.description
                }]
            },
            "subject": {"reference": f"Patient/{patient_id}"},
            "verificationStatus": {
                "coding": [{"code": "confirmed" if code.confidence > 0.85 else "provisional"}]
            }
        }
```
Estimated effort: 4-6 weeks (FHIR is complex to implement correctly).

**3.7 HL7 v2 Message Support**

```python
# backend/app/hl7/parser.py
import hl7  # pip install hl7

class HL7Parser:
    def parse_adt_a01(self, message: str) -> PatientEncounter:
        """Parse ADT^A01 (admission) for patient encounter data."""
        ...
    
    def parse_orb_r01(self, message: str) -> List[LabResult]:
        """Parse ORU^R01 (results) for lab and diagnostic data."""
        ...
```
Estimated effort: 2-3 weeks.

### Month 4: Revenue Cycle Features

**3.8 Denial Prediction Engine**

```python
# backend/app/billing/denial_predictor.py

class DenialPredictor:
    """
    Predicts claim denial probability based on:
    - Code combinations (NCCI edits)
    - Payer-specific patterns (from historical data)
    - Medical necessity indicators
    - Documentation completeness
    """
    
    def predict_denial_risk(
        self,
        codes: List[MedicalCode],
        payer: str,
        patient_demographics: Dict
    ) -> DenialRiskAssessment:
        
        ncci_violations = self._check_ncci_edits(codes)
        lcd_violations = self._check_lcd_coverage(codes, payer)
        documentation_gaps = self._assess_documentation(codes)
        
        return DenialRiskAssessment(
            risk_score=...,
            violations=ncci_violations + lcd_violations,
            documentation_gaps=documentation_gaps,
            recommendations=...
        )
```
Estimated effort: 8-12 weeks (requires NCCI edit files from CMS + payer rule data).

**3.9 NCCI Edit Checking**

CMS publishes NCCI (National Correct Coding Initiative) edit files quarterly. These define which CPT code pairs cannot be billed together:
```python
# Download from: https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-edits
# backend/app/billing/ncci_checker.py

class NCCIChecker:
    def check_procedure_to_procedure(
        self, 
        code1: str, 
        code2: str
    ) -> Optional[NCCIConflict]:
        """Check if two CPT codes are in NCCI conflict."""
        ...
```
Estimated effort: 2-3 weeks (CMS files are public, parsing is straightforward).

---

## Phase 4: Full Enterprise Platform (Months 4-12)
**Goal:** Market-ready platform competing with Sully AI and Notable Health

### Months 4-6: Enterprise Infrastructure

**4.1 Multi-Tenancy Architecture**
```
- Organization model: org_id on all tables
- Tenant isolation at database level (row-level security in PostgreSQL)
- Tenant-specific configuration (payer rules, code preferences)
- White-label capability
- SSO / SAML 2.0 / OIDC via Okta/Auth0 integration
```
Estimated effort: 8-12 weeks.

**4.2 Advanced Analytics Dashboard**
```
- Real-time coding accuracy metrics
- Coder productivity dashboard
- Revenue impact reports (estimated RVU values per encounter)
- Denial rate tracking
- Query management reports (CDI query rates)
- Benchmark comparisons (vs CMS national averages)
```
Estimated effort: 6-8 weeks (frontend + backend + reporting queries).

**4.3 Kubernetes Deployment**
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: medical-coder-api
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
  template:
    spec:
      containers:
      - name: api
        image: medical-coder:latest
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
```
Estimated effort: 2-3 weeks.

### Months 6-9: Advanced AI

**4.4 Fine-Tuned Coding Model**

For highest accuracy, fine-tune a clinical BERT/LLM on coding examples:
```
Dataset: Physician Note → ICD-10/CPT code pairs
- MIMIC-III (research, with IRB)
- Proprietary hospital data (with BAA)
- Synthetic clinical notes generated from ICD-10 descriptions

Training approach:
- Base model: Llama-3.1-8B or BioMedLM-3B
- PEFT/LoRA fine-tuning (parameter-efficient)
- Multi-task: primary dx, secondary dx, CPT, E/M level
- Evaluate on coding accuracy metrics (exact match, valid code %)

Infrastructure: 4x A100 80GB GPUs (AWS p4d.24xlarge) for training
```
Estimated effort: 6-12 months including data collection, training, evaluation, validation.
This is the path to 90%+ coding accuracy that would match enterprise incumbents.

**4.5 Ambient AI / Voice Pipeline**

```
- Real-time audio stream transcription (Whisper large-v3)
- Streaming clinical note generation
- Real-time code suggestion as note is dictated
- Post-encounter note finalization + coding
- Integration with EHR ambient modules

Infrastructure: WebSocket endpoint for streaming audio
Model: OpenAI Whisper or Deepgram for STT
LLM: Streaming mode (Anthropic/OpenAI streaming API)
```
Estimated effort: 16-24 weeks.

### Months 9-12: Market Readiness

**4.6 Epic SMART on FHIR Integration**
- Epic App Orchard application review (6-12 month process)
- CDS Hooks for real-time coding suggestions within Epic
- SMART launch context for provider identity
- Epic-specific FHIR API customizations

**4.7 Certification and Compliance**
- SOC 2 Type II certification (5-6 months)
- HITRUST CSF certification (12-18 months)
- ONC Health IT Module certification (if applicable)
- State-specific healthcare AI regulations

**4.8 Payer Integration**
- CMS Medicare/Medicaid coverage rules engine
- Commercial payer prior auth APIs (Availity, Council)
- Real-time eligibility checking
- ERA/835 remittance processing

---

## Recommended Open-Source Integrations

| Component | Tool | Purpose | License |
|-----------|------|---------|---------|
| Clinical NLP | scispaCy + en_core_sci_lg | Medical NER + UMLS | MIT |
| Negation | negspaCy | Clinical negation detection | MIT |
| FHIR | fhir.resources | FHIR R4 Python objects | BSD |
| HL7 | python-hl7 | HL7 v2 message parsing | BSD |
| OCR | EasyOCR | Better OCR than Tesseract | Apache 2.0 |
| Task Queue | Celery + Redis | Async processing | BSD/MIT |
| Rate Limiting | slowapi | FastAPI rate limiter | MIT |
| Caching | Redis (asyncio) | Query/embedding cache | BSD |
| BM25 | rank-bm25 | Hybrid retrieval | Apache 2.0 |
| Reranking | sentence-transformers CrossEncoder | Candidate reranking | Apache 2.0 |
| Monitoring | Prometheus + Grafana | Metrics/observability | Apache 2.0 |
| Tracing | OpenTelemetry | Distributed tracing | Apache 2.0 |
| Auth | python-jose + passlib | JWT tokens | MIT |

---

## Recommended Frontend Stack

| Layer | Technology | Justification |
|-------|-----------|---------------|
| Framework | Next.js 14 (App Router) | SSR, TypeScript, ecosystem |
| UI Components | shadcn/ui + Tailwind CSS | Rapid, accessible components |
| State Management | TanStack Query v5 | Server state, caching |
| Forms | React Hook Form + Zod | Validation, performance |
| Charts | Recharts | Lightweight, composable |
| Tables | TanStack Table v8 | Virtualized, sortable/filterable |
| Code Editor | CodeMirror 6 | Clinical text input with syntax highlighting |
| PDF Viewer | react-pdf | Inline document viewing |
| Auth | NextAuth.js | OAuth2/JWT integration |
| Testing | Vitest + Testing Library | Fast unit tests |
| E2E Testing | Playwright | Cross-browser automated testing |

---

## Recommended Infrastructure

### Development
```
Local: Docker Compose (API + PostgreSQL + Redis + Ollama)
GPU: NVIDIA RTX 3090+ or Apple Silicon M3 Pro for local LLM
IDE: VS Code + Python extension + ESLint
```

### Staging
```
Cloud: AWS, GCP, or Azure
Compute: 2x c6i.xlarge (API) + 1x r6i.large (DB) + 1x cache.t3.medium (Redis)
GPU (if local LLM): g4dn.xlarge (T4 GPU, $0.526/hr)
Database: RDS PostgreSQL 16 Multi-AZ
Cache: ElastiCache Redis 7
Storage: S3 for documents, EBS for ChromaDB
```

### Production
```
Compute: EKS (Kubernetes) with autoscaling 3-10 API pods
Database: RDS PostgreSQL 16 Multi-AZ with read replicas
Cache: ElastiCache Redis Cluster
Search: Consider migrating from ChromaDB to Qdrant (better cluster support)
Observability: DataDog or AWS CloudWatch + OpenTelemetry
CDN: CloudFront for frontend
WAF: AWS WAF for API protection
Secrets: AWS Secrets Manager
Encryption: AWS KMS for data encryption keys
HIPAA compliance: AWS Healthcare competency (BAA available)
```

### Estimated Monthly Infrastructure Cost (Production)
| Component | Monthly Cost |
|-----------|-------------|
| EKS cluster (3 m6i.xlarge nodes) | ~$650 |
| RDS PostgreSQL Multi-AZ (db.r6g.xlarge) | ~$480 |
| ElastiCache Redis (cache.r6g.large) | ~$165 |
| OpenAI API (GPT-4o, ~1000 requests/day) | ~$300-1500 |
| Anthropic API (alternative) | ~$200-800 |
| Data transfer + storage | ~$100 |
| **Total (cloud LLM)** | **~$1,700-3,000/month** |
| **Total (local Ollama on GPU)** | **~$900-1,200/month** |
