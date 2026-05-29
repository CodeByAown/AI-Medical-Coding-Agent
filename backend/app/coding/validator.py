"""
Medical code validator — verifies codes exist in the knowledge base and are well-formed.
"""
import re
from typing import Dict, List, Optional, Tuple

from app.config import get_settings
from app.models.schemas import CodeType, MedicalCode

settings = get_settings()

# ICD-10-CM: standard (I21.9) or CMS no-period (I219) — decimal optional; includes U codes (COVID)
# Note: HCPCS codes like A0001 also match this pattern but are validated separately by code_type
ICD10_CM_PATTERN = re.compile(r"^[A-Z][0-9][0-9A-Z](\.[0-9A-Z]{1,4}|[0-9A-Z]{1,4})?$", re.IGNORECASE)
# CPT: 5 digits (and some alphanumeric Category III codes)
CPT_PATTERN = re.compile(r"^[0-9]{4}[0-9A-Z]$")
# HCPCS Level II: Letter + 4 digits
HCPCS_PATTERN = re.compile(r"^[A-V][0-9]{4}$", re.IGNORECASE)


def validate_code_format(code: str, code_type: CodeType) -> Tuple[bool, Optional[str]]:
    """Returns (is_valid, error_message)."""
    code = code.strip().upper()
    if code_type in (CodeType.ICD10_CM, CodeType.ICD10_PCS):
        if ICD10_CM_PATTERN.match(code):
            return True, None
        return False, f"Invalid ICD-10-CM format: {code} (expected like A01.0 or J18.9)"
    elif code_type == CodeType.CPT:
        if CPT_PATTERN.match(code):
            return True, None
        return False, f"Invalid CPT format: {code} (expected 5 digits like 99213)"
    elif code_type == CodeType.HCPCS:
        if HCPCS_PATTERN.match(code):
            return True, None
        return False, f"Invalid HCPCS format: {code} (expected like A0001)"
    return False, f"Unknown code type: {code_type}"


def _lookup_code_sync(code: str, code_type_value: str) -> Optional[Dict]:
    """Synchronous code lookup using direct ChromaDB access (no async)."""
    from app.rag.indexer import get_chroma_client
    from app.config import get_settings
    settings = get_settings()

    collection_map = {
        "ICD-10-CM": settings.chroma_collection_icd10,
        "ICD-10-PCS": settings.chroma_collection_icd10,
        "CPT": settings.chroma_collection_cpt,
        "HCPCS": settings.chroma_collection_hcpcs,
    }
    collection_name = collection_map.get(code_type_value)
    if not collection_name:
        return None

    candidates_to_try = [code]
    if "." in code:
        candidates_to_try.append(code.replace(".", ""))
    elif len(code) > 3 and code[0].isalpha() and code[1].isdigit():
        candidates_to_try.append(code[:3] + "." + code[3:])

    client = get_chroma_client()
    for lookup_code in candidates_to_try:
        try:
            collection = client.get_collection(collection_name)
            results = collection.get(
                where={"code": lookup_code},
                include=["metadatas", "documents"],
            )
            if results["metadatas"]:
                return results["metadatas"][0]
        except Exception:
            pass
    return None


def validate_codes(codes: List[MedicalCode]) -> List[MedicalCode]:
    """
    Validate a list of medical codes.
    Returns list with invalid codes filtered out and confidence adjusted.
    This function is synchronous and safe to call from sync contexts.
    """
    validated = []
    for code in codes:
        is_format_valid, error = validate_code_format(code.code, code.code_type)
        if not is_format_valid:
            continue  # Drop malformed codes

        # Verify against knowledge base (synchronous direct lookup)
        kb_entry = _lookup_code_sync(code.code, code.code_type.value)
        if kb_entry:
            # Update description from authoritative source
            code.description = kb_entry.get("description", code.description)
            if not code.hierarchy:
                code.hierarchy = kb_entry.get("category", "")
        else:
            # Code not in knowledge base — reduce confidence slightly
            code.confidence = max(0.0, code.confidence - 0.10)

        validated.append(code)
    return validated


def detect_sequencing_issues(codes: List[MedicalCode]) -> List[str]:
    """Detect common code sequencing issues."""
    warnings = []
    primary_count = sum(1 for c in codes if c.is_primary)
    if primary_count == 0 and codes:
        warnings.append("No primary diagnosis designated")
    elif primary_count > 1:
        warnings.append(f"Multiple primary diagnoses ({primary_count}). Only one primary allowed.")

    icd10_codes = [c for c in codes if c.code_type == CodeType.ICD10_CM]
    if len(icd10_codes) > 25:
        warnings.append(f"Unusually high number of ICD-10 codes ({len(icd10_codes)})")

    # Check for symptom codes when specific diagnosis available
    symptom_prefixes = {"R05", "R06", "R07", "R10", "R11", "R50", "R51", "R52", "R53"}
    specific_codes = [c for c in icd10_codes if not c.code.startswith(tuple(symptom_prefixes))]
    symptom_codes = [c for c in icd10_codes if c.code.startswith(tuple(symptom_prefixes))]
    if specific_codes and symptom_codes:
        warnings.append(
            "Signs/symptom codes present alongside specific diagnosis codes. "
            "Review: symptom codes should not be coded when integral to a definitive diagnosis."
        )

    return warnings


def normalize_code(code: str) -> str:
    """Normalize a code string to standard format."""
    code = code.strip().upper()
    # Add decimal point to ICD-10-CM codes if missing (e.g., J189 -> J18.9)
    if ICD10_CM_PATTERN.match(code.replace(".", "")) and "." not in code and len(code) > 3:
        return code[:3] + "." + code[3:]
    return code
