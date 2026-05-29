"""
Document processing — handles PDF, images, and DOCX extraction with OCR fallback.
All CPU-bound/blocking operations are wrapped with run_sync() for async safety.
"""
import io
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple

from app.config import get_settings
from app.utils.async_utils import run_sync

logger = logging.getLogger(__name__)
settings = get_settings()


class DocumentProcessor:
    """Extracts text from medical documents (PDF, DOCX, images)."""

    def extract_text(self, file_content: bytes, filename: str) -> Tuple[str, bool, Optional[int]]:
        """
        Synchronous text extraction — use extract_text_async() from async contexts.
        Returns (text, ocr_used, page_count).
        """
        extension = Path(filename).suffix.lower().lstrip(".")

        if extension == "txt":
            return file_content.decode("utf-8", errors="replace"), False, 1
        elif extension == "pdf":
            return self._extract_from_pdf(file_content)
        elif extension == "docx":
            return self._extract_from_docx(file_content)
        elif extension in ("png", "jpg", "jpeg", "tiff", "bmp", "gif"):
            return self._extract_from_image(file_content), True, 1
        else:
            raise ValueError(f"Unsupported file format: {extension}")

    async def extract_text_async(
        self, file_content: bytes, filename: str
    ) -> Tuple[str, bool, Optional[int]]:
        """
        Async-safe text extraction — wraps the synchronous version in run_sync().
        Use this from FastAPI route handlers.
        """
        return await run_sync(self.extract_text, file_content, filename)

    def _extract_from_pdf(self, content: bytes) -> Tuple[str, bool, int]:
        """Extract text from PDF using PyMuPDF, fall back to OCR."""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=content, filetype="pdf")
            page_count = len(doc)
            text_parts = []

            for page in doc:
                text = page.get_text("text")
                text_parts.append(text)

            full_text = "\n\n".join(text_parts).strip()

            if len(full_text) > 100:
                return full_text, False, page_count

            # Text too short — likely scanned PDF, use OCR
            logger.info("PDF has minimal text, applying OCR")
            ocr_parts = []
            for page in doc:
                mat = fitz.Matrix(2, 2)  # 2x zoom for better OCR
                clip = page.get_pixmap(matrix=mat)
                img_bytes = clip.tobytes("png")
                ocr_text = self._ocr_image_bytes(img_bytes)
                ocr_parts.append(ocr_text)
            doc.close()
            return "\n\n".join(ocr_parts).strip(), True, page_count

        except ImportError:
            logger.warning("PyMuPDF not installed. Trying pdfplumber.")
            return self._extract_pdf_pdfplumber(content)
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            raise

    def _extract_pdf_pdfplumber(self, content: bytes) -> Tuple[str, bool, int]:
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                pages = []
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    pages.append(text)
                return "\n\n".join(pages), False, len(pages)
        except Exception as e:
            raise RuntimeError(f"pdfplumber extraction failed: {e}")

    def _extract_from_docx(self, content: bytes) -> Tuple[str, bool, int]:
        try:
            import docx
            doc = docx.Document(io.BytesIO(content))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n".join(paragraphs), False, 1
        except ImportError:
            raise RuntimeError("python-docx not installed. Run: pip install python-docx")
        except Exception as e:
            raise RuntimeError(f"DOCX extraction failed: {e}")

    def _extract_from_image(self, content: bytes) -> str:
        return self._ocr_image_bytes(content)

    def _ocr_image_bytes(self, image_bytes: bytes) -> str:
        """Run Tesseract OCR on image bytes."""
        try:
            import pytesseract
            from PIL import Image

            if settings.tesseract_cmd and settings.tesseract_cmd != "tesseract":
                pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

            image = Image.open(io.BytesIO(image_bytes))
            # Pre-processing for better OCR accuracy
            image = image.convert("L")  # Grayscale
            text = pytesseract.image_to_string(
                image,
                lang=settings.ocr_language,
                config="--psm 6 --oem 3",
            )
            return text.strip()
        except ImportError:
            logger.warning("pytesseract/Pillow not installed. OCR unavailable.")
            return ""
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return ""


_processor: Optional[DocumentProcessor] = None


def get_document_processor() -> DocumentProcessor:
    global _processor
    if _processor is None:
        _processor = DocumentProcessor()
    return _processor
