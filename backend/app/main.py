"""
AI Medical Coder API — FastAPI application entry point.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.routes import coding, documents, health
from app.api.routes.auth import router as auth_router
from app.config import get_settings
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.timing import RequestTimingMiddleware
from app.models.database import get_async_session, init_db
from app.rag.indexer import index_cpt_codes, index_hcpcs_codes, index_icd10_codes
from app.utils.logging_config import configure_logging, get_logger

settings = get_settings()

# Configure structured logging at import time
configure_logging(log_level=settings.log_level, json_logs=settings.json_logs)
logger = get_logger(__name__)

# Rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_requests_per_minute}/minute"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", app=settings.app_name, version=settings.app_version)

    # Ensure data directory exists
    os.makedirs("./data", exist_ok=True)

    # Initialize database (creates tables if not exist)
    logger.info("Initializing database...")
    await init_db()

    # Create default admin user if none exists (first-run setup)
    try:
        async with get_async_session() as db:
            from app.services.user_service import create_user, get_user_by_email
            from app.auth.rbac import UserRole
            admin_email = "admin@medcoder.local"
            existing = await get_user_by_email(db, admin_email)
            if not existing:
                await create_user(db, admin_email, "ChangeMe123!", UserRole.ADMIN, "System Admin")
                logger.info("default_admin_created", email=admin_email)
    except Exception as e:
        logger.warning("admin_user_init_failed", error=str(e))

    # Build knowledge base indices (non-blocking — warns if data missing)
    logger.info("Loading knowledge base indices...")
    try:
        from app.utils.async_utils import run_sync
        icd10_count = await run_sync(index_icd10_codes)
        cpt_count = await run_sync(index_cpt_codes)
        hcpcs_count = await run_sync(index_hcpcs_codes)
        logger.info(
            "knowledge_base_loaded",
            icd10=icd10_count,
            cpt=cpt_count,
            hcpcs=hcpcs_count,
        )
        if icd10_count == 0:
            logger.warning(
                "icd10_empty",
                hint="Run: python knowledge_base/scripts/build_knowledge_base.py",
            )
    except Exception as e:
        logger.warning("knowledge_base_load_failed", error=str(e))

    # Pre-load NLP model
    logger.info("Loading clinical NLP model...")
    try:
        from app.nlp.entity_extractor import get_nlp
        get_nlp()
        logger.info("nlp_model_loaded", model=settings.scispacy_model)
    except Exception as e:
        logger.warning("nlp_model_load_failed", error=str(e))

    logger.info(
        "startup_complete",
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
    )
    yield
    logger.info("shutdown", app=settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description="""
## AI Medical Coder API

Production-grade AI-powered medical coding engine supporting:

- **ICD-10-CM** diagnosis coding
- **CPT** procedure coding
- **HCPCS** equipment/supply coding

### Features
- Clinical NLP entity extraction (scispaCy)
- Semantic RAG retrieval from official code databases
- LLM-powered code assignment with confidence scores
- Human review queue for low-confidence cases
- PDF/OCR document processing
- SOAP note parsing
- Multi-specialty support
- Full audit trail
- JWT authentication with RBAC

### LLM Backends
- **Ollama** (local, HIPAA-friendly — default)
- **Anthropic Claude** (highest accuracy — optional)
- **OpenAI GPT-4** (optional)

### Authentication
Use `Bearer <JWT>` header. In development mode (no keys configured), all requests are allowed.
    """,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)

# Request timing + structured logging
app.add_middleware(RequestTimingMiddleware)

# CORS — must be added after custom middleware (outermost layer)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(coding.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", exc_type=type(exc).__name__, error=str(exc)[:200])
    # In production, never expose exception type or internal details
    if settings.debug:
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "debug_type": type(exc).__name__},
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
