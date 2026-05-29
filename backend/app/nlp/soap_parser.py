"""
SOAP note parser — extracts Subjective / Objective / Assessment / Plan sections.
Works on both structured and semi-structured clinical notes.
"""
import re
from typing import Optional, Dict, Tuple
from app.models.schemas import SOAPSection


# Section header patterns (case-insensitive)
_SECTION_PATTERNS = {
    "subjective": re.compile(
        r"(?:^|\n)\s*(?:S[:\.]?\s+|SUBJECTIVE[:\s]|CC[:\s]|Chief\s+Complaint[:\s]|HPI[:\s]|History\s+of\s+Present\s+Illness[:\s])",
        re.IGNORECASE | re.MULTILINE,
    ),
    "objective": re.compile(
        r"(?:^|\n)\s*(?:O[:\.]?\s+|OBJECTIVE[:\s]|Vitals?[:\s]|Physical\s+Exam[:\s]|PE[:\s]|Examination[:\s])",
        re.IGNORECASE | re.MULTILINE,
    ),
    "assessment": re.compile(
        r"(?:^|\n)\s*(?:A[:\.]?\s+|ASSESSMENT[:\s]|IMPRESSION[:\s]|DIAGNOSIS[:\s]|DX[:\s]|A/P[:\s])",
        re.IGNORECASE | re.MULTILINE,
    ),
    "plan": re.compile(
        r"(?:^|\n)\s*(?:P[:\.]?\s+|PLAN[:\s]|TREATMENT[:\s]|MANAGEMENT[:\s]|ORDERS[:\s])",
        re.IGNORECASE | re.MULTILINE,
    ),
}

# Discharge summary section patterns
_DISCHARGE_PATTERNS = {
    "assessment": re.compile(
        r"(?:^|\n)\s*(?:DISCHARGE\s+DIAGNOSIS|FINAL\s+DIAGNOSIS|PRIMARY\s+DIAGNOSIS|DISCHARGE\s+DX)[:\s]",
        re.IGNORECASE | re.MULTILINE,
    ),
    "plan": re.compile(
        r"(?:^|\n)\s*(?:DISCHARGE\s+MEDICATIONS|DISCHARGE\s+INSTRUCTIONS|FOLLOW-?UP|PROCEDURES\s+PERFORMED)[:\s]",
        re.IGNORECASE | re.MULTILINE,
    ),
}


def parse_soap_note(text: str) -> SOAPSection:
    """Parse clinical text into SOAP sections."""
    soap = SOAPSection(raw_text=text)

    # Find section boundaries
    boundaries: Dict[str, int] = {}
    for section, pattern in _SECTION_PATTERNS.items():
        match = pattern.search(text)
        if match:
            boundaries[section] = match.start()

    if not boundaries:
        # Try discharge summary patterns
        for section, pattern in _DISCHARGE_PATTERNS.items():
            match = pattern.search(text)
            if match:
                boundaries[section] = match.start()

    if not boundaries:
        # No structured sections found — treat full text as assessment
        soap.assessment = text.strip()
        return soap

    # Sort sections by position
    sorted_sections = sorted(boundaries.items(), key=lambda x: x[1])

    for i, (section_name, start_pos) in enumerate(sorted_sections):
        # Content goes from after the header to the start of the next section
        if i + 1 < len(sorted_sections):
            end_pos = sorted_sections[i + 1][1]
        else:
            end_pos = len(text)

        content = text[start_pos:end_pos].strip()
        # Remove the section header itself
        content = _remove_header(content)

        setattr(soap, section_name, content)

    return soap


def _remove_header(text: str) -> str:
    """Remove section header from extracted section text."""
    first_newline = text.find("\n")
    if first_newline != -1 and first_newline < 80:
        return text[first_newline:].strip()
    # Try removing up to first colon or period
    for i, ch in enumerate(text[:80]):
        if ch in (":", "\n") and i > 0:
            return text[i + 1:].strip()
    return text


def extract_diagnoses_from_assessment(assessment_text: str) -> list:
    """Extract clean diagnosis names from the Assessment section."""
    if not assessment_text:
        return []
    lines = [line.strip() for line in assessment_text.split("\n") if line.strip()]
    diagnoses = []
    number_pattern = re.compile(r"^\d+[\.\)]\s+")
    # Separators that delimit diagnosis from plan text on the same line
    plan_separator = re.compile(r"\s+[-–:]\s+|\s*\bfor\b\s+(?:cardiac|respiratory|renal|monitoring|management)|,\s+(?:admit|start|continue|hold|order|refer)", re.IGNORECASE)
    skip_prefixes = ("PROCEDURES:", "ORDERS:", "LABS:", "IMAGING:", "MEDICATIONS:", "FOLLOW")
    for line in lines:
        if len(line) < 5:
            continue
        # Skip procedure/order lines
        if any(line.upper().startswith(p) for p in skip_prefixes):
            continue
        # Remove list numbering
        clean = number_pattern.sub("", line)
        # Strip plan text that follows the diagnosis name on the same line
        split_match = plan_separator.search(clean)
        if split_match:
            clean = clean[:split_match.start()].strip()
        if clean and len(clean) > 3:
            diagnoses.append(clean)
    return diagnoses


def extract_procedures_from_plan(plan_text: str) -> list:
    """Extract procedure statements from the Plan section."""
    if not plan_text:
        return []
    lines = [line.strip() for line in plan_text.split("\n") if line.strip()]
    procedures = []
    procedure_keywords = re.compile(
        r"\b(perform|refer|order|schedule|obtain|consult|administer|prescribe|admit|nebuli[sz]|x-ray|xray|initiat|monitor|start|continue|procedure|surgery|imaging|biopsy|scan|test|therapy|injection|catheter)\b",
        re.IGNORECASE,
    )
    for line in lines:
        if procedure_keywords.search(line):
            procedures.append(line)
    return procedures


def get_coding_relevant_text(soap: SOAPSection) -> str:
    """Return the most coding-relevant parts of a SOAP note (Assessment + Plan)."""
    parts = []
    if soap.assessment:
        parts.append(f"ASSESSMENT: {soap.assessment}")
    if soap.plan:
        parts.append(f"PLAN: {soap.plan}")
    if not parts and soap.raw_text:
        return soap.raw_text
    return "\n\n".join(parts)
