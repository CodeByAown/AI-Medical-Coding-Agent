# AI Medical Coder Agent

> Production-grade, open-source AI medical coding engine supporting ICD-10-CM, CPT, and HCPCS.
> HIPAA-friendly architecture with local LLM support via Ollama.

---

## What This Does

This agent takes clinical documentation (SOAP notes, discharge summaries, progress notes, etc.) and automatically assigns accurate medical codes:

- **ICD-10-CM** — Diagnosis codes (primary + secondary)
- **CPT** — Procedure codes
- **HCPCS Level II** — Equipment and supply codes

**Pipeline:**
```
Clinical Text / PDF / Image
        ↓
  Document OCR / Parsing
        ↓
  Clinical NLP (scispaCy)  →  Entity Extraction + UMLS Linking
        ↓
  RAG Retrieval  →  Semantic search over ICD-10/CPT/HCPCS knowledge base
        ↓
  LLM Reasoning  →  Code assignment with confidence + evidence
        ↓
  Validation  →  Format check, sequencing rules
        ↓
  Human Review Queue (if confidence < threshold)
        ↓
  Structured JSON Result + Audit Trail
```

---

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| API Framework | FastAPI | Async, auto-docs, production-grade |
| Clinical NLP | scispaCy (Allen AI) | Best open-source clinical NER + UMLS linking |
| Vector Database | ChromaDB | Fast local vector search, no external service |
| Embeddings | S-PubMedBert-MS-MARCO | Medical domain-tuned embeddings |
| Local LLM | Ollama (Llama 3.1 8B) | Self-hosted, HIPAA-friendly |
| Cloud LLM | Anthropic Claude (optional) | Higher accuracy fallback |
| RAG Framework | LlamaIndex / direct ChromaDB | Efficient code retrieval |
| Database | SQLite / PostgreSQL | Audit trail, review queue |
| OCR | PyMuPDF + Tesseract | PDF and image document processing |

---

## Project Structure

```
ai medical coding agent/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app entry point
│   │   ├── config.py                # All settings (from .env)
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── coding.py        # /api/v1/coding/* endpoints
│   │   │   │   ├── documents.py     # /api/v1/documents/* endpoints
│   │   │   │   └── health.py        # /health endpoint
│   │   │   └── dependencies.py      # API key auth
│   │   ├── agents/
│   │   │   └── medical_coder.py     # Main coding agent orchestrator
│   │   ├── nlp/
│   │   │   ├── entity_extractor.py  # scispaCy NER + UMLS linking
│   │   │   └── soap_parser.py       # SOAP note section parser
│   │   ├── rag/
│   │   │   ├── indexer.py           # Build ChromaDB indices
│   │   │   └── retriever.py         # Semantic code search
│   │   ├── llm/
│   │   │   ├── provider.py          # Ollama/Anthropic/OpenAI abstraction
│   │   │   └── prompts.py           # Medical coding prompts
│   │   ├── coding/
│   │   │   └── validator.py         # Code format + sequencing validation
│   │   ├── document/
│   │   │   └── ocr.py               # PDF/image text extraction
│   │   └── models/
│   │       ├── schemas.py           # Pydantic schemas (request/response)
│   │       └── database.py          # SQLAlchemy ORM models
│   ├── knowledge_base/
│   │   ├── scripts/
│   │   │   └── build_knowledge_base.py  # Download + index ICD-10, HCPCS
│   │   ├── data/
│   │   │   ├── icd10/               # ICD-10-CM JSON data
│   │   │   ├── cpt/                 # CPT codes JSON
│   │   │   └── hcpcs/               # HCPCS JSON data
│   │   └── indices/                 # ChromaDB vector indices
│   ├── tests/
│   │   ├── test_coding.py
│   │   └── test_nlp.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── pyproject.toml
├── docker-compose.yml
├── setup.ps1                        # Windows setup script
├── .env.example                     # Environment template
└── README.md
```

---

## Quick Start

### Option A: Automated Setup (Windows)

```powershell
cd "C:\Ai Agents\ai medical coding agent"
.\setup.ps1
```

### Option B: Manual Setup

**1. Create virtual environment:**
```powershell
cd "C:\Ai Agents\ai medical coding agent\backend"
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

**2. Install scispaCy clinical NLP model (~600MB):**
```bash
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_lg-0.5.4.tar.gz
```

**3. Configure environment:**
```powershell
# Copy .env.example to backend/.env
copy .env.example backend\.env
# Edit backend/.env and set your LLM provider
```

**4. Set up LLM backend — choose ONE:**

*Option 1: Ollama (local, HIPAA-friendly — recommended)*
```bash
# Install Ollama from https://ollama.com
ollama pull llama3.1:8b
# In .env: LLM_PROVIDER=ollama, LLM_MODEL=llama3.1:8b
```

*Option 2: Anthropic Claude (highest accuracy)*
```bash
# In .env: LLM_PROVIDER=anthropic, ANTHROPIC_API_KEY=your-key
```

**5. Build knowledge base:**
```bash
cd backend
python knowledge_base/scripts/build_knowledge_base.py
```
This downloads:
- **ICD-10-CM** from CMS/CDC (75,000+ diagnosis codes)
- **HCPCS Level II** from CMS (equipment/supply codes)
- **CPT** built-in common codes (full CPT requires AMA license)

**6. Start the API:**
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**7. Open API docs:**
```
http://localhost:8000/docs
```

---

## API Usage

### Code a Clinical Note

```bash
curl -X POST "http://localhost:8000/api/v1/coding/code" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "65yo male with COPD exacerbation and pneumonia. BP 148/92. Started IV antibiotics.",
    "document_type": "soap_note",
    "specialty": "internal_medicine",
    "include_cpt": true
  }'
```

**Response:**
```json
{
  "session_id": "uuid-here",
  "status": "completed",
  "codes": [
    {
      "code": "J44.1",
      "code_type": "ICD-10-CM",
      "description": "COPD with acute exacerbation",
      "confidence": 0.93,
      "evidence": "COPD exacerbation",
      "is_primary": true
    },
    {
      "code": "J18.9",
      "code_type": "ICD-10-CM",
      "description": "Pneumonia, unspecified",
      "confidence": 0.88,
      "evidence": "pneumonia",
      "is_primary": false
    },
    {
      "code": "I10",
      "code_type": "ICD-10-CM",
      "description": "Essential hypertension",
      "confidence": 0.85,
      "evidence": "BP 148/92",
      "is_primary": false
    },
    {
      "code": "96365",
      "code_type": "CPT",
      "description": "Intravenous infusion, up to 1 hour",
      "confidence": 0.80,
      "evidence": "IV antibiotics"
    }
  ],
  "requires_human_review": false,
  "processing_time_ms": 2341
}
```

### Upload a PDF Document

```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@clinical_note.pdf"
```

### Search for Codes

```bash
# Semantic search — finds best matching codes for a clinical term
curl "http://localhost:8000/api/v1/coding/search?q=community+acquired+pneumonia&code_type=ICD-10-CM"
```

### Look Up a Specific Code

```bash
curl "http://localhost:8000/api/v1/coding/lookup/ICD-10-CM/J18.9"
```

### Get Human Review Queue

```bash
curl "http://localhost:8000/api/v1/coding/review/queue"
```

### Approve / Reject Codes (Human Review)

```bash
curl -X POST "http://localhost:8000/api/v1/coding/review/{session_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "uuid-here",
    "approved_codes": ["J44.1", "J18.9"],
    "rejected_codes": ["I10"],
    "reviewer_notes": "I10 not documented as active problem",
    "reviewer_id": "coder-001"
  }'
```

---

## Docker Deployment

```bash
# Start both the API and Ollama
docker-compose up -d

# Pull the LLM model (one-time)
docker exec ai-medical-coder-ollama ollama pull llama3.1:8b

# Build knowledge base inside container
docker exec ai-medical-coder-api python knowledge_base/scripts/build_knowledge_base.py

# View logs
docker-compose logs -f api
```

---

## Configuration Reference

Key settings in `backend/.env`:

| Setting | Default | Description |
|---------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | `ollama` \| `anthropic` \| `openai` |
| `LLM_MODEL` | `llama3.1:8b` | Model name for Ollama |
| `ANTHROPIC_API_KEY` | - | Claude API key (if using Anthropic) |
| `MIN_CONFIDENCE_THRESHOLD` | `0.70` | Below this → needs review |
| `AUTO_APPROVE_THRESHOLD` | `0.90` | Above this → auto-approved |
| `RAG_TOP_K` | `15` | How many candidate codes to retrieve |
| `SCISPACY_MODEL` | `en_core_sci_lg` | Clinical NLP model size |
| `ENABLE_UMLS_LINKING` | `true` | Link entities to UMLS ontology |
| `DATABASE_URL` | SQLite | Change to PostgreSQL for production |

---

## Specialty Support

The agent supports 16 medical specialties with specialty-aware coding guidance:
- General Medicine, Cardiology, Orthopedics, Oncology
- Neurology, Psychiatry, Radiology, Surgery
- Emergency Medicine, Internal Medicine, Pediatrics
- Obstetrics, Dermatology, Urology, Pulmonology, Gastroenterology

---

## Human Review Workflow

Cases are automatically routed to human review when:
- Overall confidence < 70% (configurable)
- Documentation is ambiguous
- Code sequencing issues detected
- LLM cannot parse the clinical note
- `require_review=true` in the request

Reviewers access the queue via `/api/v1/coding/review/queue` and approve/reject via `/api/v1/coding/review/{session_id}`.

---

## Running Tests

```bash
cd backend
pytest tests/ -v
```

---

## Extending the System

**Add full CPT dataset (requires AMA license):**
1. Purchase CPT data file from AMA
2. Convert to JSON: `[{"code": "99213", "description": "..."}]`
3. Save to `knowledge_base/data/cpt/cpt_codes.json`
4. Rebuild index: `python knowledge_base/scripts/build_knowledge_base.py`

**Add custom specialty rules:**
Edit `app/agents/medical_coder.py` → `SPECIALTY_CONTEXT` dict

**Use a different embedding model:**
In `.env`: `EMBEDDING_MODEL=cambridgeltl/SapBERT-from-PubMedBERT-fulltext`

**Switch to BioMistral (medical fine-tuned model):**
```bash
ollama pull biomistral  # if available
# In .env: LLM_MODEL=biomistral
```

---

## Integration with Other Healthcare Agents

This agent exposes a clean REST API designed for integration with:
- **AI Medical Scribe** → Pass transcribed SOAP notes directly
- **AI Document Reader** → Pass OCR text from scanned records
- **EMR/EHR systems** → Submit notes via REST, receive coded results
- **AI Prior Authorization** → Use assigned codes for PA requests
- **AI Compliance Agent** → Audit coded encounters

---

## HIPAA Compliance Notes

- **Local LLM (Ollama)**: All clinical text stays on your server — never sent to external APIs
- **Database**: SQLite by default, stores coded results locally
- **No telemetry**: ChromaDB telemetry disabled by default
- **API Keys**: Configure `ALLOWED_API_KEYS` to restrict access
- **Audit Trail**: All coding sessions stored with timestamps

For production HIPAA compliance, additionally:
- Use HTTPS (TLS termination via nginx/reverse proxy)
- Enable database encryption
- Set up access logging
- Configure data retention policies
- Use PostgreSQL with encryption at rest

---

## Roadmap

- [ ] Fine-tuned coding model (Llama + MIMIC-IV dataset)
- [ ] ICD-10-PCS procedure coding
- [ ] DSM-5 psychiatric coding
- [ ] Modifier suggestion engine
- [ ] Denial prediction
- [ ] Prior authorization code sets
- [ ] CMS quality measure coding (HCC, RAF)
- [ ] Voice input integration
- [ ] EMR connectors (Epic, Cerner)
