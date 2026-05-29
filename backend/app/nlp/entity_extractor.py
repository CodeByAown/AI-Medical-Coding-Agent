"""
Clinical NLP entity extractor using scispaCy.
Extracts medical entities (diseases, symptoms, procedures) and links to UMLS.
All spaCy nlp() calls are wrapped in run_sync() to avoid blocking the event loop.
"""
import logging
import re
from typing import List, Optional, Tuple
import spacy
from spacy.tokens import Doc

from app.config import get_settings
from app.models.schemas import ExtractedEntity
from app.utils.async_utils import run_sync

logger = logging.getLogger(__name__)
settings = get_settings()

_nlp = None
_linker = None
_negex_enabled = False


def get_nlp():
    global _nlp, _linker, _negex_enabled
    if _nlp is not None:
        return _nlp

    # Try scispaCy model first
    for model_name in [settings.scispacy_model, "en_core_sci_md", "en_core_sci_sm"]:
        try:
            _nlp = spacy.load(model_name)
            logger.info(f"Loaded scispaCy model: {model_name}")

            if settings.enable_umls_linking:
                try:
                    _nlp.add_pipe(
                        "scispacy_linker",
                        config={
                            "resolve_abbreviations": True,
                            "linker_name": "umls",
                            "max_entities_per_mention": 3,
                            "threshold": 0.85,
                            "filter_for_definitions": False,
                        },
                    )
                    _linker = _nlp.get_pipe("scispacy_linker")
                    logger.info("UMLS entity linker loaded")
                except Exception as e:
                    logger.warning(f"UMLS linker not available: {e} — running without UMLS linking")

            # Add negation detection if negspaCy is available
            _negex_enabled = _try_add_negex(_nlp)
            return _nlp
        except OSError:
            continue

    # Fall back to standard spaCy models
    for fallback_model in ["en_core_web_lg", "en_core_web_md", "en_core_web_sm"]:
        try:
            _nlp = spacy.load(fallback_model)
            logger.warning(
                f"scispaCy model not found — using {fallback_model} as fallback. "
                "For clinical NER accuracy, install scispaCy: "
                "pip install scispacy && pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_lg-0.5.4.tar.gz"
            )
            _negex_enabled = _try_add_negex(_nlp)
            return _nlp
        except OSError:
            continue

    _nlp = _create_fallback_nlp()
    return _nlp


def _try_add_negex(nlp) -> bool:
    """Attempt to add negspaCy negation detection. Returns True if successful."""
    try:
        import negspacy  # noqa: F401
        nlp.add_pipe("negex", config={"neg_termset": "en_clinical"}, last=True)
        logger.info("Negation detection enabled (negspaCy)")
        return True
    except ImportError:
        logger.warning("negspaCy not available — negation detection disabled. Install with: pip install negspacy")
        return False
    except Exception as e:
        logger.warning(f"negspaCy setup failed: {e} — negation detection disabled")
        return False


def _create_fallback_nlp():
    """Lightweight fallback when scispaCy model is unavailable."""
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        nlp = spacy.blank("en")
    return nlp


# Medical entity type mapping to ICD/coding relevance
MEDICAL_ENTITY_TYPES = {
    "DISEASE",
    "DISORDER",
    "FINDING",
    "SYMPTOM",
    "PROCEDURE",
    "CHEMICAL",
    "DRUG",
    "ANATOMY",
    "ORGANISM",
    "GENE",
    "INJURY",
}


def _extract_entities_sync(text: str) -> List[ExtractedEntity]:
    """Synchronous entity extraction — wrapped via run_sync in async callers."""
    nlp = get_nlp()
    doc = nlp(text)
    entities: List[ExtractedEntity] = []

    for ent in doc.ents:
        # Skip negated entities if negspaCy is active
        if _negex_enabled and hasattr(ent._, "negex") and ent._.negex:
            logger.debug(f"Skipping negated entity: {ent.text}")
            continue

        # Determine confidence based on entity source
        if hasattr(ent._, "kb_ents") and ent._.kb_ents:
            # UMLS-linked entity — use similarity score
            top_hit = ent._.kb_ents[0]
            confidence = float(top_hit[1])
        elif ent.label_ in MEDICAL_ENTITY_TYPES:
            # Medical entity type from scispaCy without UMLS
            confidence = 0.70
        else:
            # General English model entity
            confidence = 0.50

        entity = ExtractedEntity(
            text=ent.text,
            entity_type=ent.label_,
            start_char=ent.start_char,
            end_char=ent.end_char,
            confidence=confidence,
        )

        # UMLS linking if available
        if hasattr(ent._, "kb_ents") and ent._.kb_ents:
            top_hit = ent._.kb_ents[0]
            entity.umls_cui = top_hit[0]

            # Try to get canonical name
            if _linker and entity.umls_cui in _linker.kb.cui_to_entity:
                kb_entity = _linker.kb.cui_to_entity[entity.umls_cui]
                entity.umls_name = kb_entity.canonical_name

        entities.append(entity)

    return entities


async def extract_entities(text: str) -> List[ExtractedEntity]:
    """Extract medical entities from clinical text (async-safe)."""
    return await run_sync(_extract_entities_sync, text)


def extract_entities_sync(text: str) -> List[ExtractedEntity]:
    """Synchronous variant for non-async callers (e.g., scripts)."""
    return _extract_entities_sync(text)


async def extract_medical_terms(text: str) -> List[str]:
    """Return a flat list of extracted medical term strings."""
    return [e.text for e in await extract_entities(text)]


def preprocess_clinical_text(text: str) -> str:
    """Normalize clinical text for better NLP processing."""
    abbreviations = {
        r"\bpt\b": "patient",
        r"\bc/o\b": "complains of",
        r"\bh/o\b": "history of",
        r"\bHx\b": "history",
        r"\bDx\b": "diagnosis",
        r"\bRx\b": "prescription",
        r"\bTx\b": "treatment",
        r"\bHOB\b": "head of bed",
        r"\bSOB\b": "shortness of breath",
        r"\bCP\b": "chest pain",
        r"\bHTN\b": "hypertension",
        r"\bDM\b": "diabetes mellitus",
        r"\bCAD\b": "coronary artery disease",
        r"\bCHF\b": "congestive heart failure",
        r"\bCOPD\b": "chronic obstructive pulmonary disease",
        r"\bURI\b": "upper respiratory infection",
        r"\bUTI\b": "urinary tract infection",
        r"\bMI\b": "myocardial infarction",
        r"\bCVA\b": "cerebrovascular accident",
        r"\bDVT\b": "deep vein thrombosis",
        r"\bPE\b": "pulmonary embolism",
        r"\bBP\b": "blood pressure",
        r"\bHR\b": "heart rate",
        r"\bRR\b": "respiratory rate",
        r"\bT\b": "temperature",
        r"\bO2\b": "oxygen",
        r"\bSaO2\b": "oxygen saturation",
        r"\bSpO2\b": "oxygen saturation",
        r"\bBID\b": "twice daily",
        r"\bTID\b": "three times daily",
        r"\bQID\b": "four times daily",
        r"\bPRN\b": "as needed",
        r"\bIV\b": "intravenous",
        r"\bIM\b": "intramuscular",
        r"\bPO\b": "by mouth",
        r"\bNPO\b": "nothing by mouth",
        r"\bWBC\b": "white blood cell count",
        r"\bRBC\b": "red blood cell count",
        r"\bHgb\b": "hemoglobin",
        r"\bHct\b": "hematocrit",
        r"\bBUN\b": "blood urea nitrogen",
        r"\bCr\b": "creatinine",
        r"\bECG\b": "electrocardiogram",
        r"\bEEG\b": "electroencephalogram",
        r"\bCT\b": "computed tomography",
        r"\bMRI\b": "magnetic resonance imaging",
        r"\bCXR\b": "chest x-ray",
    }
    for pattern, replacement in abbreviations.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text
