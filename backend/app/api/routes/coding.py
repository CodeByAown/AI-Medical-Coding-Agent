"""
Medical coding API routes — core coding endpoints.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.medical_coder import get_medical_coder
from app.api.dependencies import CurrentUser, get_current_user
from app.models.database import AssignedCode, CodingSession, get_db
from app.models.schemas import (
    CodeType,
    CodingRequest,
    CodingResult,
    CodingStatus,
    PaginatedResponse,
    ReviewDecision,
    ReviewQueueItem,
)
from app.rag.retriever import get_retriever
from app.services.audit_service import AuditAction, log_audit_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/coding", tags=["Medical Coding"])


@router.post(
    "/code",
    response_model=CodingResult,
    status_code=status.HTTP_200_OK,
    summary="Code a clinical note",
    description="Submit clinical text for automated ICD-10, CPT, and HCPCS coding.",
)
async def code_clinical_note(
    request: Request,
    coding_request: CodingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    agent = get_medical_coder()
    result = await agent.code_clinical_note(coding_request)

    # Persist to database
    session_record = CodingSession(
        id=result.session_id,
        user_id=current_user.user_id,
        status=result.status.value,
        document_type=coding_request.document_type.value,
        specialty=coding_request.specialty.value,
        patient_id=coding_request.patient_id,
        encounter_id=coding_request.encounter_id,
        clinical_text=coding_request.text,
        soap_json=result.soap_sections.model_dump() if result.soap_sections else None,
        extracted_entities_json=[e.model_dump() for e in result.extracted_entities],
        model_used=result.model_used,
        processing_time_ms=result.processing_time_ms,
        summary=result.summary,
        requires_human_review=result.requires_human_review,
        review_reason=result.review_reason,
        metadata_json=coding_request.metadata,
    )
    db.add(session_record)

    for code in result.codes:
        code_record = AssignedCode(
            session_id=result.session_id,
            code=code.code,
            code_type=code.code_type.value,
            description=code.description,
            confidence=code.confidence,
            is_primary=code.is_primary,
            evidence=code.evidence,
            modifiers=code.modifiers,
            hierarchy=code.hierarchy,
        )
        db.add(code_record)

    # Audit log
    ip = request.client.host if request.client else "unknown"
    await log_audit_event(
        db,
        AuditAction.NOTE_SUBMITTED,
        user_id=current_user.user_id,
        resource_type="coding_session",
        resource_id=result.session_id,
        ip_address=ip,
        details={
            "specialty": coding_request.specialty.value,
            "codes_assigned": len(result.codes),
            "requires_review": result.requires_human_review,
        },
    )

    await db.commit()
    return result


@router.get(
    "/session/{session_id}",
    response_model=CodingResult,
    summary="Get coding session result",
)
async def get_session(
    session_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(CodingSession)
        .options(selectinload(CodingSession.codes))
        .where(CodingSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Audit log
    ip = request.client.host if request.client else "unknown"
    await log_audit_event(
        db,
        AuditAction.SESSION_VIEWED,
        user_id=current_user.user_id,
        resource_type="coding_session",
        resource_id=session_id,
        ip_address=ip,
    )
    await db.commit()

    from app.models.schemas import ExtractedEntity, MedicalCode, SOAPSection
    codes = [
        MedicalCode(
            code=c.code,
            code_type=CodeType(c.code_type),
            description=c.description,
            confidence=c.confidence,
            is_primary=c.is_primary,
            evidence=c.evidence or "",
            modifiers=c.modifiers or [],
            hierarchy=c.hierarchy,
        )
        for c in session.codes
    ]

    entities = []
    if session.extracted_entities_json:
        entities = [ExtractedEntity(**e) for e in session.extracted_entities_json]

    soap = None
    if session.soap_json:
        soap = SOAPSection(**session.soap_json)

    from app.models.schemas import DocumentType, Specialty
    return CodingResult(
        session_id=session.id,
        status=CodingStatus(session.status),
        codes=codes,
        extracted_entities=entities,
        soap_sections=soap,
        specialty=Specialty(session.specialty),
        document_type=DocumentType(session.document_type),
        summary=session.summary or "",
        requires_human_review=session.requires_human_review,
        review_reason=session.review_reason,
        processing_time_ms=session.processing_time_ms,
        model_used=session.model_used,
        created_at=session.created_at,
    )


@router.get(
    "/lookup/{code_type}/{code}",
    summary="Look up a specific medical code",
)
async def lookup_code(
    code_type: str,
    code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Look up a specific code in the knowledge base."""
    retriever = get_retriever()
    result = await retriever.lookup_code(code.upper(), code_type.upper())
    if not result:
        raise HTTPException(status_code=404, detail=f"Code {code} not found in knowledge base")

    ip = request.client.host if request.client else "unknown"
    await log_audit_event(
        db,
        AuditAction.CODE_LOOKED_UP,
        user_id=current_user.user_id,
        resource_type="code",
        resource_id=f"{code_type}/{code}",
        ip_address=ip,
    )
    await db.commit()
    return result


@router.get(
    "/search",
    summary="Search codes by clinical query",
)
async def search_codes(
    q: str = Query(..., min_length=3, description="Clinical query or term"),
    code_type: Optional[str] = Query(None, description="Filter by ICD-10-CM, CPT, or HCPCS"),
    top_k: int = Query(10, ge=1, le=50),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Semantic search for medical codes matching a clinical query."""
    retriever = get_retriever()
    results = {}

    if not code_type or code_type.upper() in ("ICD-10-CM", "ICD-10", "ICD10"):
        results["icd10"] = await retriever.search_icd10(q, top_k=top_k)
    if not code_type or code_type.upper() == "CPT":
        results["cpt"] = await retriever.search_cpt(q, top_k=top_k)
    if not code_type or code_type.upper() in ("HCPCS",):
        results["hcpcs"] = await retriever.search_hcpcs(q, top_k=top_k)

    return results


@router.post(
    "/review/{session_id}",
    response_model=CodingResult,
    summary="Submit human review decision",
)
async def submit_review(
    session_id: str,
    decision: ReviewDecision,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    from sqlalchemy import select, update
    from datetime import datetime

    # Update session status
    await db.execute(
        update(CodingSession)
        .where(CodingSession.id == session_id)
        .values(
            status=CodingStatus.APPROVED.value if decision.approved_codes else CodingStatus.REJECTED.value,
            reviewer_id=decision.reviewer_id or current_user.user_id,
            reviewer_notes=decision.reviewer_notes,
            reviewed_at=datetime.utcnow(),
        )
    )

    # Update individual code statuses
    if decision.approved_codes:
        await db.execute(
            update(AssignedCode)
            .where(
                AssignedCode.session_id == session_id,
                AssignedCode.code.in_(decision.approved_codes),
            )
            .values(status="approved")
        )
    if decision.rejected_codes:
        await db.execute(
            update(AssignedCode)
            .where(
                AssignedCode.session_id == session_id,
                AssignedCode.code.in_(decision.rejected_codes),
            )
            .values(status="rejected")
        )

    # Audit log
    ip = request.client.host if request.client else "unknown"
    action = AuditAction.REVIEW_APPROVED if decision.approved_codes else AuditAction.REVIEW_REJECTED
    await log_audit_event(
        db,
        action,
        user_id=current_user.user_id,
        resource_type="coding_session",
        resource_id=session_id,
        ip_address=ip,
        details={
            "approved_codes": decision.approved_codes,
            "rejected_codes": decision.rejected_codes,
        },
    )

    await db.commit()
    return await get_session(session_id, request, db, current_user)


@router.get(
    "/sessions",
    summary="List coding sessions for current user",
)
async def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status"),
    specialty: Optional[str] = Query(None, description="Filter by specialty"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    from sqlalchemy import func, select
    from sqlalchemy.orm import selectinload

    query = (
        select(CodingSession)
        .options(selectinload(CodingSession.codes))
        .where(CodingSession.user_id == current_user.user_id)
        .order_by(CodingSession.created_at.desc())
    )
    if status:
        query = query.where(CodingSession.status == status)
    if specialty:
        query = query.where(CodingSession.specialty == specialty)

    count_query = select(func.count()).select_from(
        select(CodingSession).where(CodingSession.user_id == current_user.user_id).subquery()
    )
    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    sessions = result.scalars().all()

    from app.models.schemas import DocumentType, ExtractedEntity, MedicalCode, SOAPSection, Specialty as SpecialtyEnum
    items = []
    for s in sessions:
        codes = [
            MedicalCode(
                code=c.code,
                code_type=CodeType(c.code_type),
                description=c.description,
                confidence=c.confidence,
                is_primary=c.is_primary,
                evidence=c.evidence or "",
                modifiers=c.modifiers or [],
                hierarchy=c.hierarchy,
            )
            for c in s.codes
        ]
        entities = [ExtractedEntity(**e) for e in (s.extracted_entities_json or [])]
        soap = SOAPSection(**s.soap_json) if s.soap_json else None
        items.append(
            CodingResult(
                session_id=s.id,
                status=CodingStatus(s.status),
                codes=codes,
                extracted_entities=entities,
                soap_sections=soap,
                specialty=SpecialtyEnum(s.specialty),
                document_type=DocumentType(s.document_type),
                summary=s.summary or "",
                requires_human_review=s.requires_human_review,
                review_reason=s.review_reason,
                processing_time_ms=s.processing_time_ms,
                model_used=s.model_used,
                created_at=s.created_at,
            )
        )

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get(
    "/review/queue",
    summary="Get pending human review queue",
)
async def get_review_queue(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    specialty: Optional[str] = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    from sqlalchemy import func, select
    from sqlalchemy.orm import selectinload

    query = (
        select(CodingSession)
        .options(selectinload(CodingSession.codes))
        .where(CodingSession.status == CodingStatus.NEEDS_REVIEW.value)
        .order_by(CodingSession.created_at.desc())
    )
    if specialty:
        query = query.where(CodingSession.specialty == specialty)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    sessions = result.scalars().all()

    items = []
    for s in sessions:
        from app.models.schemas import DocumentType, MedicalCode, Specialty as SpecialtyEnum
        codes = [
            MedicalCode(
                code=c.code,
                code_type=CodeType(c.code_type),
                description=c.description,
                confidence=c.confidence,
                is_primary=c.is_primary,
                evidence=c.evidence or "",
                modifiers=c.modifiers or [],
                hierarchy=c.hierarchy,
            )
            for c in s.codes
        ]
        items.append(
            ReviewQueueItem(
                session_id=s.id,
                status=CodingStatus(s.status),
                codes=codes,
                clinical_text_preview=s.clinical_text[:300] + "..." if len(s.clinical_text) > 300 else s.clinical_text,
                specialty=SpecialtyEnum(s.specialty),
                document_type=DocumentType(s.document_type),
                created_at=s.created_at,
                review_reason=s.review_reason,
                requires_human_review=s.requires_human_review,
                processing_time_ms=s.processing_time_ms,
            )
        )

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size),
    )
