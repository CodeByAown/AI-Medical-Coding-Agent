# Neural Hub — AI Medical Coding Agent
## Project Overview (Short Reference)

---

## What Is Medical Coding?

When a doctor treats a patient, every diagnosis and procedure must be converted into standardized numeric/alphanumeric codes before a hospital can bill insurance companies. This is called **medical coding**.

There are three main code systems:

| Code System | What It Covers | Example |
|-------------|---------------|---------|
| **ICD-10-CM** | Diagnoses / diseases | `E11.9` = Type 2 Diabetes |
| **CPT** | Procedures / surgeries | `27447` = Total Knee Replacement |
| **HCPCS** | Equipment / supplies | `A4253` = Blood glucose test strips |

Traditionally, human coders read doctor's notes and manually assign these codes. It is slow, expensive, and error-prone. **This project automates that process using AI.**

---

## What This Project Does

Neural Hub reads a doctor's clinical note (SOAP note, discharge summary, etc.) and automatically:
1. Extracts medical entities (diseases, symptoms, procedures)
2. Searches 74,000+ medical codes
3. Assigns the correct ICD-10, CPT, and HCPCS codes with confidence scores
4. Flags low-confidence results for human review

---

## System Architecture

```
Frontend (Next.js)          Backend (FastAPI / Python)
──────────────────          ──────────────────────────
Login Page           ──→    JWT Authentication
Dashboard            
AI Coding Workspace  ──→    POST /api/v1/coding/code
  ↳ paste SOAP note              │
  ↳ click "Run AI Coding"        ▼
  ↳ see results             1. NLP Pipeline (spaCy)
                                 ↓ extracts entities
History Page         ──→    2. RAG Retrieval (ChromaDB)
Review Queue         ──→         ↓ searches 74K codes
Settings                    3. LLM (GPT-4o via OpenAI)
                                 ↓ assigns final codes
                            4. Validator
                                 ↓ checks format/rules
                            5. Database (SQLite)
                                 ↓ saves session
                            6. Returns JSON result
```

---

## The 6-Step Coding Pipeline (Backend)

**Step 1 — NLP Entity Extraction**
The clinical note text is processed by spaCy NLP. It finds medical entities like "diabetes mellitus", "hypertension", "chest pain", etc.

**Step 2 — SOAP Parsing**
The note is split into Subjective / Objective / Assessment / Plan sections to focus on the most coding-relevant parts.

**Step 3 — RAG Code Retrieval**
The extracted entities are turned into vector embeddings and searched against a ChromaDB vector database containing 74,260 ICD-10 codes + CPT + HCPCS codes. Returns the top candidate codes.

**Step 4 — LLM Code Assignment (GPT-4o)**
The candidates + full clinical text are sent to GPT-4o with a structured medical coding prompt. The LLM selects the correct codes, assigns primary vs secondary, and provides confidence scores + evidence.

**Step 5 — Code Validation**
The assigned codes are validated against format rules (ICD-10 pattern, CPT numeric range, etc.). Low confidence sessions are flagged for human review.

**Step 6 — Save & Return**
The session (codes, entities, SOAP sections, confidence, model used, processing time) is saved to the database and returned to the frontend as JSON.

---

## Key Files & Folders

```
ai medical coding agent/
├── backend/                          ← Python FastAPI server (port 8000)
│   ├── app/
│   │   ├── agents/medical_coder.py   ← Main orchestrator (runs steps 1-5)
│   │   ├── nlp/entity_extractor.py   ← spaCy NLP pipeline
│   │   ├── nlp/soap_parser.py        ← SOAP note parser
│   │   ├── rag/retriever.py          ← ChromaDB vector search
│   │   ├── llm/provider.py           ← GPT-4o / Anthropic / Ollama
│   │   ├── coding/validator.py       ← Code format validation
│   │   ├── models/database.py        ← SQLite tables (SQLAlchemy)
│   │   ├── api/routes/coding.py      ← POST /coding/code endpoint
│   │   └── auth/                     ← JWT + RBAC (4 roles)
│   └── knowledge_base/
│       └── data/icd10/               ← 74,260 ICD-10 codes (JSON)
│
└── frontend/                         ← Next.js 16 app (port 3000)
    └── app/
        ├── (auth)/login/             ← Login page
        └── dashboard/
            ├── page.tsx              ← Dashboard with stats
            ├── coding/page.tsx       ← AI Coding Workspace
            ├── history/page.tsx      ← Past sessions
            ├── review/page.tsx       ← Human review queue
            └── settings/page.tsx     ← Config + system status
```

---

## Data Flow Example

**Input (user pastes this):**
```
Patient has type 2 diabetes mellitus and essential hypertension.
BP 158/96. Started on metformin and lisinopril.
```

**Pipeline:**
1. NLP finds: `diabetes mellitus`, `hypertension`
2. Vector search finds top ICD-10 candidates for each
3. GPT-4o picks: `E11.9` (DM2) as primary, `I10` (HTN) as secondary
4. Confidence: 95% and 85%
5. Saved to DB, returned to UI

**Output (shown in UI):**
```
E11.9 — Type 2 diabetes mellitus without complications  [PRIMARY]  95%
I10   — Essential (primary) hypertension                           85%
```

---

## Authentication & Roles

| Role | Can Do |
|------|--------|
| **Admin** | Everything |
| **Coder** | Submit notes, view own sessions |
| **Reviewer** | Approve/reject coding queue |
| **Auditor** | Read-only access, audit logs |

**Dev credentials:** `admin@medcoder.local` / `ChangeMe123!`

---

## Running Locally

```bash
# Backend (Python)
cd backend
.\venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000

# Frontend (Node.js)
cd frontend
npm run dev
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS, Framer Motion |
| Backend | Python 3.13, FastAPI, SQLAlchemy async |
| AI/LLM | OpenAI GPT-4o (primary), Anthropic Claude, Ollama (local) |
| NLP | spaCy (`en_core_web_sm`) |
| Vector DB | ChromaDB with `all-MiniLM-L6-v2` embeddings |
| Database | SQLite (dev) → PostgreSQL (production) |
| Auth | JWT HS256 + RBAC |
| Embeddings | SentenceTransformers `all-MiniLM-L6-v2` |
