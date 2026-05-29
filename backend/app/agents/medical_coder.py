"""
Core AI Medical Coder Agent — the main orchestration layer.
Combines NLP extraction, RAG retrieval, LLM reasoning, and validation.
"""
import logging
import time
import uuid
from typing import Dict, List, Optional

from app.coding.validator import detect_sequencing_issues, validate_codes
from app.config import get_settings
from app.llm.prompts import CODING_PROMPT_TEMPLATE, ENTITY_EXTRACTION_PROMPT, SYSTEM_PROMPT
from app.llm.provider import get_llm_provider, parse_llm_json_response
from app.models.schemas import (
    CodeType,
    CodingRequest,
    CodingResult,
    CodingStatus,
    ExtractedEntity,
    MedicalCode,
    SOAPSection,
    Specialty,
)
from app.nlp.entity_extractor import extract_entities, preprocess_clinical_text
from app.nlp.soap_parser import (
    extract_diagnoses_from_assessment,
    extract_procedures_from_plan,
    get_coding_relevant_text,
    parse_soap_note,
)
from app.rag.retriever import get_retriever

logger = logging.getLogger(__name__)
settings = get_settings()

# Specialty-specific hints for the LLM
SPECIALTY_CONTEXT = {
    Specialty.CARDIOLOGY: "Focus on cardiac diagnoses (I-codes), cardiac procedures. Check for AMI, heart failure, arrhythmia specificity.",
    Specialty.ORTHOPEDICS: "Focus on musculoskeletal codes (M-codes, S-codes). Apply laterality, fracture type, encounter type (initial/subsequent/sequela).",
    Specialty.ONCOLOGY: "Follow neoplasm coding guidelines. Sequence primary neoplasm first. Code complications separately.",
    Specialty.NEUROLOGY: "Apply stroke coding guidelines. Distinguish cerebral infarction type (occlusion/embolism/thrombosis).",
    Specialty.PSYCHIATRY: "Apply DSM-5 aligned ICD-10 codes. Distinguish severity levels.",
    Specialty.EMERGENCY: "Code the reason for ED visit. Apply injury codes with external cause codes.",
    Specialty.EMERGENCY_MEDICINE: "Code the reason for ED visit. Apply injury codes with external cause codes. Use E/M code 99281-99285.",
    Specialty.SURGERY: "Match CPT to surgical approach (open/laparoscopic/robotic). Include E/M if significant separate service.",
    Specialty.GENERAL: "Apply standard ICD-10-CM guidelines. Sequence correctly.",
    Specialty.INTERNAL: "Apply general internal medicine coding. Sequence principal diagnosis first. Code all treated comorbidities.",
    Specialty.PULMONOLOGY: "Focus on respiratory codes (J-codes). Distinguish COPD types, asthma severity, respiratory failure causes.",
    Specialty.GASTROENTEROLOGY: "Focus on digestive system codes (K-codes). Specify ulcer type, IBD activity, procedure approach.",
    Specialty.ENDOCRINOLOGY: "Focus on metabolic/endocrine codes (E-codes). Specify diabetes type and complications precisely.",
    Specialty.NEPHROLOGY: "Focus on kidney disease codes (N-codes). Code CKD stage. Link to underlying cause (diabetic nephropathy, HTN).",
    Specialty.RHEUMATOLOGY: "Focus on musculoskeletal and connective tissue codes (M-codes). Specify joint involvement and laterality.",
    Specialty.INFECTIOUS_DISEASE: "Identify pathogen when documented (B-codes, A-codes). Code sepsis correctly per ICD-10 guidelines.",
    Specialty.OPHTHALMOLOGY: "Focus on eye codes (H-codes). Apply laterality. Specify diabetic retinopathy type and severity.",
    Specialty.OBSTETRICS: "Apply obstetric coding guidelines (O-codes). Use trimester codes. Code maternal conditions.",
    Specialty.OBSTETRICS_GYNECOLOGY: "Apply obstetric and gynecologic coding (O-codes, N-codes). Use trimester codes for obstetric conditions.",
    Specialty.DERMATOLOGY: "Focus on skin codes (L-codes). Specify lesion type, location, and benign vs malignant.",
    Specialty.UROLOGY: "Focus on genitourinary codes (N-codes). Specify laterality for paired organs.",
    Specialty.PEDIATRICS: "Apply pediatric-specific ICD-10 codes. Document congenital vs acquired conditions.",
    Specialty.RADIOLOGY: "Code the imaging procedure (CPT). Code reason for study as primary ICD-10 code.",
}


class MedicalCoderAgent:
    """Main medical coding agent orchestrating the full coding pipeline."""

    async def code_clinical_note(self, request: CodingRequest) -> CodingResult:
        """Process a clinical note through the full coding pipeline."""
        start_time = time.time()
        session_id = str(uuid.uuid4())

        logger.info(f"[{session_id}] Starting coding: {request.document_type} / {request.specialty}")

        try:
            # Step 1: Preprocess and parse the note
            processed_text = preprocess_clinical_text(request.text)
            soap = parse_soap_note(processed_text)
            coding_text = get_coding_relevant_text(soap)
            if not coding_text.strip():
                coding_text = processed_text

            # Step 2: Extract clinical entities (async-safe via run_sync)
            entities = await extract_entities(coding_text)
            extracted_diagnoses = extract_diagnoses_from_assessment(soap.assessment or "")
            extracted_procedures = extract_procedures_from_plan(soap.plan or "")

            # Step 3: Build search queries from extracted entities
            search_queries = self._build_search_queries(
                entities, extracted_diagnoses, extracted_procedures, coding_text
            )

            # Step 4: RAG retrieval — get candidate codes (async)
            retriever = get_retriever()
            icd10_candidates = []
            cpt_candidates = []

            for query in search_queries[:5]:  # Top 5 queries to avoid token overflow
                icd10_hits = await retriever.search_icd10(query, top_k=8)
                icd10_candidates.extend(icd10_hits)
                if request.include_cpt:
                    cpt_hits = await retriever.search_cpt(query, top_k=5)
                    cpt_candidates.extend(cpt_hits)

            # Deduplicate candidates by code
            icd10_candidates = self._deduplicate_candidates(icd10_candidates)[:20]
            cpt_candidates = self._deduplicate_candidates(cpt_candidates)[:15]

            # Step 5: LLM coding assignment
            llm_result = await self._llm_assign_codes(
                clinical_text=coding_text,
                soap=soap,
                entities=entities,
                icd10_candidates=icd10_candidates,
                cpt_candidates=cpt_candidates,
                request=request,
            )

            # Step 6: Build structured MedicalCode objects
            codes = self._build_medical_codes(llm_result, icd10_candidates, cpt_candidates)

            # Step 7: Validate codes
            validated_codes = validate_codes(codes)
            sequencing_warnings = detect_sequencing_issues(validated_codes)

            # Step 8: Determine review status
            overall_confidence = llm_result.get("overall_confidence", 0.0)
            requires_review = (
                request.require_review
                or llm_result.get("requires_review", False)
                or overall_confidence < settings.human_review_threshold
                or len(sequencing_warnings) > 0
                or len(validated_codes) == 0
            )

            review_reason = None
            if requires_review:
                reasons = []
                if overall_confidence < settings.human_review_threshold:
                    reasons.append(f"Low confidence ({overall_confidence:.0%})")
                if llm_result.get("review_reason"):
                    reasons.append(llm_result["review_reason"])
                if sequencing_warnings:
                    reasons.extend(sequencing_warnings)
                review_reason = ". ".join(reasons) if reasons else "Flagged for review"

            status = CodingStatus.NEEDS_REVIEW if requires_review else CodingStatus.COMPLETED
            if not validated_codes:
                status = CodingStatus.NEEDS_REVIEW

            processing_ms = int((time.time() - start_time) * 1000)

            result = CodingResult(
                session_id=session_id,
                status=status,
                codes=validated_codes,
                extracted_entities=entities,
                soap_sections=soap,
                specialty=request.specialty,
                document_type=request.document_type,
                summary=llm_result.get("coding_notes", ""),
                requires_human_review=requires_review,
                review_reason=review_reason,
                processing_time_ms=processing_ms,
                model_used=f"{settings.llm_provider}/{settings.llm_model}",
                metadata={
                    "icd10_candidates_count": len(icd10_candidates),
                    "cpt_candidates_count": len(cpt_candidates),
                    "entities_extracted": len(entities),
                    "sequencing_warnings": sequencing_warnings,
                },
            )

            logger.info(
                f"[{session_id}] Coding complete: {len(validated_codes)} codes, "
                f"confidence={overall_confidence:.0%}, review={requires_review}, "
                f"time={processing_ms}ms"
            )
            return result

        except Exception as e:
            logger.error(f"[{session_id}] Coding failed: {e}", exc_info=True)
            processing_ms = int((time.time() - start_time) * 1000)
            return CodingResult(
                session_id=session_id,
                status=CodingStatus.ERROR,
                specialty=request.specialty,
                document_type=request.document_type,
                requires_human_review=True,
                review_reason=f"Processing error: {str(e)[:200]}",
                processing_time_ms=processing_ms,
                model_used=f"{settings.llm_provider}/{settings.llm_model}",
            )

    def _build_search_queries(
        self,
        entities: List[ExtractedEntity],
        diagnoses: List[str],
        procedures: List[str],
        fallback_text: str,
    ) -> List[str]:
        """Build semantic search queries from extracted information."""
        queries = []
        # Use extracted entities as queries
        for entity in entities[:10]:
            if len(entity.text) > 3:
                query = entity.umls_name or entity.text
                queries.append(query)
        # Add extracted diagnoses
        queries.extend(d for d in diagnoses[:5] if len(d) > 5)
        # Add procedures
        queries.extend(p for p in procedures[:3] if len(p) > 5)
        # Fallback: use first 500 chars of text
        if not queries:
            queries.append(fallback_text[:500])
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for q in queries:
            if q.lower() not in seen:
                seen.add(q.lower())
                unique.append(q)
        return unique

    def _deduplicate_candidates(self, candidates: List[Dict]) -> List[Dict]:
        """Remove duplicate codes, keeping highest similarity."""
        seen = {}
        for c in candidates:
            code = c["code"]
            if code not in seen or c["similarity"] > seen[code]["similarity"]:
                seen[code] = c
        return sorted(seen.values(), key=lambda x: x["similarity"], reverse=True)

    async def _llm_assign_codes(
        self,
        clinical_text: str,
        soap: SOAPSection,
        entities: List[ExtractedEntity],
        icd10_candidates: List[Dict],
        cpt_candidates: List[Dict],
        request: CodingRequest,
    ) -> Dict:
        """Use LLM to assign codes from retrieved candidates."""
        llm = get_llm_provider()

        # Format candidates for the prompt
        icd10_text = self._format_candidates(icd10_candidates[:15], "ICD-10-CM")
        cpt_text = self._format_candidates(cpt_candidates[:10], "CPT") if cpt_candidates else "No CPT candidates retrieved."

        # Format entities
        entity_text = "\n".join(
            f"- {e.text} [{e.entity_type}]"
            + (f" → UMLS: {e.umls_name}" if e.umls_name else "")
            for e in entities[:15]
        ) or "No entities extracted."

        specialty_hint = SPECIALTY_CONTEXT.get(request.specialty, SPECIALTY_CONTEXT[Specialty.GENERAL])

        user_message = CODING_PROMPT_TEMPLATE.format(
            document_type=request.document_type.value,
            specialty=f"{request.specialty.value} — {specialty_hint}",
            encounter_context="Standard clinical encounter",
            clinical_text=clinical_text[:3000],  # Limit to avoid token overflow
            extracted_entities=entity_text,
            icd10_candidates=icd10_text,
            cpt_candidates=cpt_text,
        )

        try:
            response_text = await llm.complete(
                system_prompt=SYSTEM_PROMPT,
                user_message=user_message,
                temperature=0.05,  # Very low temperature for coding accuracy
                max_tokens=2048,
            )
            result = parse_llm_json_response(response_text)
            if not result:
                logger.warning("LLM returned empty/unparseable response")
                return {"requires_review": True, "review_reason": "LLM parsing failed", "overall_confidence": 0.0}
            return result
        except Exception as e:
            logger.error(f"LLM coding failed: {e}")
            return {"requires_review": True, "review_reason": str(e)[:200], "overall_confidence": 0.0}

    def _format_candidates(self, candidates: List[Dict], code_type: str) -> str:
        if not candidates:
            return f"No {code_type} candidates retrieved."
        lines = [f"## {code_type} Candidates:"]
        for c in candidates:
            similarity_pct = f"{c['similarity'] * 100:.0f}%"
            lines.append(
                f"- {c['code']}: {c['description']} (relevance: {similarity_pct})"
            )
        return "\n".join(lines)

    def _build_medical_codes(
        self,
        llm_result: Dict,
        icd10_candidates: List[Dict],
        cpt_candidates: List[Dict],
    ) -> List[MedicalCode]:
        codes = []
        all_candidates = {}
        for c in icd10_candidates + cpt_candidates:
            all_candidates[c["code"]] = c
            # Register both period (I21.9) and no-period (I219) formats
            raw = c["code"]
            if "." in raw:
                all_candidates[raw.replace(".", "")] = c
            elif len(raw) > 3 and raw[0].isalpha() and raw[1].isdigit():
                all_candidates[raw[:3] + "." + raw[3:]] = c

        # Primary diagnosis
        primary = llm_result.get("primary_diagnosis", {})
        if primary and primary.get("code"):
            code = self._make_code(primary, all_candidates, is_primary=True)
            if code:
                codes.append(code)

        # Secondary diagnoses
        for dx in llm_result.get("secondary_diagnoses", []):
            if dx and dx.get("code"):
                code = self._make_code(dx, all_candidates, is_primary=False)
                if code:
                    codes.append(code)

        # Procedure codes (CPT)
        for proc in llm_result.get("procedure_codes", []):
            if proc and proc.get("code"):
                code = self._make_code(proc, all_candidates, is_primary=False, code_type_override=CodeType.CPT)
                if code:
                    codes.append(code)

        return codes

    def _make_code(
        self,
        code_data: Dict,
        candidates: Dict,
        is_primary: bool,
        code_type_override: Optional[CodeType] = None,
    ) -> Optional[MedicalCode]:
        raw_code = str(code_data.get("code", "")).strip().upper()
        if not raw_code:
            return None

        description = code_data.get("description", "")
        if not description and raw_code in candidates:
            description = candidates[raw_code].get("description", "")

        # Determine code type
        if code_type_override:
            code_type = code_type_override
        elif raw_code in candidates:
            ct_str = candidates[raw_code].get("code_type", "ICD-10-CM")
            code_type = CodeType(ct_str) if ct_str in [t.value for t in CodeType] else CodeType.ICD10_CM
        else:
            # Infer from format
            if raw_code[0].isdigit() and len(raw_code) == 5:
                code_type = CodeType.CPT
            elif len(raw_code) > 0 and raw_code[0].isalpha() and len(raw_code) >= 5 and raw_code[1].isdigit():
                code_type = CodeType.HCPCS
            else:
                code_type = CodeType.ICD10_CM

        return MedicalCode(
            code=raw_code,
            code_type=code_type,
            description=description or "Unknown",
            confidence=float(code_data.get("confidence", 0.7)),
            evidence=str(code_data.get("evidence", ""))[:500],
            is_primary=is_primary,
            modifiers=code_data.get("modifiers", []),
        )


_agent: Optional[MedicalCoderAgent] = None


def get_medical_coder() -> MedicalCoderAgent:
    global _agent
    if _agent is None:
        _agent = MedicalCoderAgent()
    return _agent
