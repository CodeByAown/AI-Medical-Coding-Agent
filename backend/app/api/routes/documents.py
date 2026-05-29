"""
Document upload and OCR routes.
"""
import uuid
import logging
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from app.api.dependencies import CurrentUser, get_current_user
from app.config import get_settings
from app.document.ocr import get_document_processor
from app.models.schemas import DocumentUploadResponse

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/documents", tags=["Document Processing"])


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    summary="Upload and extract text from a medical document",
    description="Upload PDF, DOCX, TXT, or image files. Text is extracted (with OCR if needed) for coding.",
)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
):
    # Check file size
    max_bytes = settings.max_document_size_mb * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.max_document_size_mb}MB",
        )

    # Check format
    extension = (file.filename or "").split(".")[-1].lower()
    if extension not in settings.supported_formats_list:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported format: {extension}. Supported: {', '.join(settings.supported_formats_list)}",
        )

    processor = get_document_processor()
    try:
        # Use async-safe extraction to avoid blocking the event loop
        text, ocr_used, page_count = await processor.extract_text_async(
            content, file.filename or "document.txt"
        )
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Document processing failed: {str(e)}",
        )

    if not text or len(text.strip()) < 20:
        raise HTTPException(
            status_code=422,
            detail="Could not extract meaningful text from document",
        )

    return DocumentUploadResponse(
        document_id=str(uuid.uuid4()),
        filename=file.filename or "unknown",
        extracted_text=text,
        page_count=page_count,
        ocr_used=ocr_used,
    )
