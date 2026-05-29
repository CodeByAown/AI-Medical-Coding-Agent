"""
Health check and system status endpoints.
"""
import logging
from fastapi import APIRouter

from app.config import get_settings
from app.llm.provider import get_llm_provider
from app.models.schemas import HealthResponse
from app.rag.indexer import get_chroma_client

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System health check",
)
async def health_check():
    components = {}

    # LLM availability
    try:
        llm = get_llm_provider()
        llm_status = await llm.check_availability()
        llm_available = llm_status.get("available", False)
        components["llm"] = f"{settings.llm_provider}/{settings.llm_model} - {'ok' if llm_available else 'unavailable'}"
    except Exception as e:
        llm_available = False
        components["llm"] = f"error: {str(e)[:100]}"

    # Knowledge base (ChromaDB)
    try:
        client = get_chroma_client()
        icd10_count = 0
        cpt_count = 0
        try:
            icd10_count = client.get_collection(settings.chroma_collection_icd10).count()
        except Exception:
            pass
        try:
            cpt_count = client.get_collection(settings.chroma_collection_cpt).count()
        except Exception:
            pass
        kb_loaded = icd10_count > 0 or cpt_count > 0
        components["knowledge_base"] = f"ICD-10: {icd10_count} codes, CPT: {cpt_count} codes"
    except Exception as e:
        kb_loaded = False
        components["knowledge_base"] = f"error: {str(e)[:100]}"

    # NLP
    try:
        from app.nlp.entity_extractor import get_nlp, _negex_enabled
        nlp = get_nlp()
        nlp_loaded = nlp is not None
        negex_status = "with negation detection" if _negex_enabled else "without negation detection"
        components["nlp"] = f"model: {settings.scispacy_model} - {'loaded' if nlp_loaded else 'not loaded'} ({negex_status})"
    except Exception as e:
        nlp_loaded = False
        components["nlp"] = f"error: {str(e)[:100]}"

    # Authentication system
    try:
        from app.auth.jwt_handler import ALGORITHM
        components["auth"] = f"JWT ({ALGORITHM}) + RBAC enabled"
    except Exception:
        components["auth"] = "auth module error"

    # PHI Encryption status
    components["phi_encryption"] = (
        "enabled" if settings.enable_phi_encryption else "disabled (set ENABLE_PHI_ENCRYPTION=true)"
    )

    # Redis (optional)
    if settings.redis_url:
        try:
            import redis
            r = redis.from_url(settings.redis_url, socket_connect_timeout=2)
            r.ping()
            components["redis"] = f"connected ({settings.redis_url})"
        except Exception as e:
            components["redis"] = f"unavailable: {str(e)[:60]}"

    overall_status = "healthy" if kb_loaded else "degraded"

    return HealthResponse(
        status=overall_status,
        version=settings.app_version,
        llm_available=llm_available,
        knowledge_base_loaded=kb_loaded,
        nlp_loaded=nlp_loaded,
        components=components,
    )


@router.get("/", summary="Root endpoint")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }
