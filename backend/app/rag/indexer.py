"""
Knowledge base indexer — builds ChromaDB vector indices for ICD-10, CPT, and HCPCS codes.
Run once, then serve queries through the retriever.
"""
import asyncio
import csv
import json
import logging
import os
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_chroma_client: Optional[chromadb.PersistentClient] = None
_embedding_model: Optional[SentenceTransformer] = None


def get_chroma_client() -> chromadb.PersistentClient:
    global _chroma_client
    if _chroma_client is None:
        persist_dir = Path(settings.chroma_persist_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        logger.info(f"ChromaDB initialized at {persist_dir}")
    return _chroma_client


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        logger.info(f"Loading embedding model: {settings.embedding_model}")
        _embedding_model = SentenceTransformer(settings.embedding_model)
        logger.info("Embedding model loaded")
    return _embedding_model


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Synchronous embedding — use run_sync() when calling from async context."""
    model = get_embedding_model()
    return model.encode(texts, convert_to_numpy=True, show_progress_bar=False).tolist()


# ─── ICD-10 Indexing ─────────────────────────────────────────────────────────

def index_icd10_codes(force_rebuild: bool = False) -> int:
    """Index ICD-10-CM codes into ChromaDB. Returns number of codes indexed.
    NOTE: This is synchronous. Wrap with run_sync() when calling from async context."""
    client = get_chroma_client()
    collection_name = settings.chroma_collection_icd10

    if not force_rebuild:
        try:
            col = client.get_collection(collection_name)
            count = col.count()
            if count > 0:
                logger.info(f"ICD-10 collection already indexed ({count} codes)")
                return count
        except Exception:
            pass

    logger.info("Building ICD-10 index...")
    codes = list(_load_icd10_codes())
    if not codes:
        logger.warning("No ICD-10 data found. Run knowledge_base/scripts/build_knowledge_base.py first.")
        return 0

    collection = client.get_or_create_collection(
        collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    if force_rebuild:
        try:
            collection.delete(where={"code_type": "ICD-10-CM"})
        except Exception:
            pass

    _batch_index(collection, codes, "ICD-10-CM")
    total = collection.count()
    logger.info(f"ICD-10 index built: {total} codes")
    return total


def index_cpt_codes(force_rebuild: bool = False) -> int:
    """Index CPT codes into ChromaDB. Returns number of codes indexed."""
    client = get_chroma_client()
    collection_name = settings.chroma_collection_cpt

    if not force_rebuild:
        try:
            col = client.get_collection(collection_name)
            count = col.count()
            if count > 0:
                logger.info(f"CPT collection already indexed ({count} codes)")
                return count
        except Exception:
            pass

    logger.info("Building CPT index...")
    codes = list(_load_cpt_codes())
    if not codes:
        logger.warning("No CPT data found. Add CPT data to knowledge_base/data/cpt/")
        return 0

    collection = client.get_or_create_collection(
        collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    _batch_index(collection, codes, "CPT")
    total = collection.count()
    logger.info(f"CPT index built: {total} codes")
    return total


def index_hcpcs_codes(force_rebuild: bool = False) -> int:
    """Index HCPCS codes into ChromaDB. Returns number of codes indexed."""
    client = get_chroma_client()
    collection_name = settings.chroma_collection_hcpcs

    if not force_rebuild:
        try:
            col = client.get_collection(collection_name)
            count = col.count()
            if count > 0:
                logger.info(f"HCPCS collection already indexed ({count} codes)")
                return count
        except Exception:
            pass

    logger.info("Building HCPCS index...")
    codes = list(_load_hcpcs_codes())
    if not codes:
        logger.warning("No HCPCS data found. Run knowledge_base/scripts/build_knowledge_base.py first.")
        return 0

    collection = client.get_or_create_collection(
        collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    _batch_index(collection, codes, "HCPCS")
    total = collection.count()
    logger.info(f"HCPCS index built: {total} codes")
    return total


def _batch_index(collection, codes: List[Dict], code_type: str, batch_size: int = 500):
    """Index codes in batches to avoid memory issues."""
    for i in range(0, len(codes), batch_size):
        batch = codes[i:i + batch_size]
        texts = [c["search_text"] for c in batch]
        ids = [f"{code_type}_{c['code']}_{i + j}" for j, c in enumerate(batch)]
        metadatas = [{
            "code": c["code"],
            "code_type": code_type,
            "description": c["description"],
            "long_description": c.get("long_description", c["description"]),
            "category": c.get("category", ""),
            "chapter": c.get("chapter", ""),
        } for c in batch]
        embeddings = embed_texts(texts)
        collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        if (i // batch_size + 1) % 10 == 0:
            logger.debug(f"Indexed {min(i + batch_size, len(codes))}/{len(codes)} {code_type} codes")


# ─── Async wrappers for startup indexing ─────────────────────────────────────

async def async_index_icd10_codes(force_rebuild: bool = False) -> int:
    """Async-safe wrapper for index_icd10_codes."""
    from app.utils.async_utils import run_sync
    return await run_sync(index_icd10_codes, force_rebuild)


async def async_index_cpt_codes(force_rebuild: bool = False) -> int:
    """Async-safe wrapper for index_cpt_codes."""
    from app.utils.async_utils import run_sync
    return await run_sync(index_cpt_codes, force_rebuild)


async def async_index_hcpcs_codes(force_rebuild: bool = False) -> int:
    """Async-safe wrapper for index_hcpcs_codes."""
    from app.utils.async_utils import run_sync
    return await run_sync(index_hcpcs_codes, force_rebuild)


# ─── Data Loaders ────────────────────────────────────────────────────────────

def _load_icd10_codes() -> Iterator[Dict]:
    """Load ICD-10-CM codes from downloaded data files."""
    data_dir = Path(settings.icd10_data_dir)

    # Try JSON first (from our download script)
    json_file = data_dir / "icd10cm_codes.json"
    if json_file.exists():
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            yield {
                "code": item["code"],
                "description": item["description"],
                "long_description": item.get("long_description", item["description"]),
                "category": item.get("category", ""),
                "chapter": item.get("chapter", ""),
                "search_text": f"{item['code']}: {item['description']}. {item.get('long_description', '')}",
            }
        return

    # Try CSV format (CMS official download)
    for csv_name in ["icd10cm_order_2026.txt", "icd10cm_codes.csv", "codes.csv"]:
        csv_file = data_dir / csv_name
        if csv_file.exists():
            yield from _parse_cms_icd10_file(csv_file)
            return

    logger.warning(f"No ICD-10 data files found in {data_dir}")


def _normalize_icd10_code(raw: str) -> str:
    """Convert CMS no-period format (I219) to standard notation (I21.9)."""
    if len(raw) > 3 and "." not in raw:
        return raw[:3] + "." + raw[3:]
    return raw


def _parse_cms_icd10_file(filepath: Path) -> Iterator[Dict]:
    """Parse CMS ICD-10-CM order file format."""
    with open(filepath, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip()
            if len(line) < 10:
                continue
            # CMS order file format: order_num(5) code(7) header_flag(1) short_desc(60) long_desc
            try:
                raw_code = line[6:13].strip()
                is_valid = line[14:15].strip() == "1"
                short_desc = line[15:77].strip()
                long_desc = line[77:].strip() if len(line) > 77 else short_desc
                if raw_code and short_desc and is_valid:
                    code = _normalize_icd10_code(raw_code)
                    yield {
                        "code": code,
                        "description": short_desc,
                        "long_description": long_desc,
                        "category": code[:3],
                        "search_text": f"{code}: {short_desc}. {long_desc}",
                    }
            except Exception:
                continue


def _load_cpt_codes() -> Iterator[Dict]:
    """Load CPT codes from data files."""
    data_dir = Path(settings.cpt_data_dir)

    json_file = data_dir / "cpt_codes.json"
    if json_file.exists():
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            yield {
                "code": item["code"],
                "description": item["description"],
                "long_description": item.get("long_description", item["description"]),
                "category": item.get("category", ""),
                "search_text": f"CPT {item['code']}: {item['description']}. {item.get('long_description', '')}",
            }
        return

    csv_file = data_dir / "cpt_codes.csv"
    if csv_file.exists():
        with open(csv_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row.get("code", row.get("CPT", "")).strip()
                desc = row.get("description", row.get("Description", "")).strip()
                if code and desc:
                    yield {
                        "code": code,
                        "description": desc,
                        "long_description": row.get("long_description", desc),
                        "category": row.get("category", ""),
                        "search_text": f"CPT {code}: {desc}",
                    }
        return

    # Built-in common CPT codes subset as fallback
    yield from _get_builtin_cpt_codes()


def _load_hcpcs_codes() -> Iterator[Dict]:
    """Load HCPCS codes from data files."""
    data_dir = Path(settings.hcpcs_data_dir)

    json_file = data_dir / "hcpcs_codes.json"
    if json_file.exists():
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            yield {
                "code": item["code"],
                "description": item["description"],
                "search_text": f"HCPCS {item['code']}: {item['description']}",
            }
        return

    logger.debug("No HCPCS JSON found; using empty set.")


def _get_builtin_cpt_codes() -> Iterator[Dict]:
    """Built-in subset of common CPT codes (for fallback when no data file exists)."""
    common_cpts = [
        ("99202", "Office or other outpatient visit, new patient, straightforward medical decision making, 15-29 minutes"),
        ("99203", "Office or other outpatient visit, new patient, low medical decision making, 30-44 minutes"),
        ("99204", "Office or other outpatient visit, new patient, moderate medical decision making, 45-59 minutes"),
        ("99205", "Office or other outpatient visit, new patient, high medical decision making, 60-74 minutes"),
        ("99211", "Office or other outpatient visit, established patient, minimal presenting problem"),
        ("99212", "Office or other outpatient visit, established patient, straightforward medical decision making, 10-19 minutes"),
        ("99213", "Office or other outpatient visit, established patient, low medical decision making, 20-29 minutes"),
        ("99214", "Office or other outpatient visit, established patient, moderate medical decision making, 30-39 minutes"),
        ("99215", "Office or other outpatient visit, established patient, high medical decision making, 40-54 minutes"),
        ("99221", "Initial hospital inpatient or observation care, straightforward or low medical decision making"),
        ("99222", "Initial hospital inpatient or observation care, moderate medical decision making"),
        ("99223", "Initial hospital inpatient or observation care, high medical decision making"),
        ("99231", "Subsequent hospital inpatient or observation care, straightforward or low medical decision making"),
        ("99232", "Subsequent hospital inpatient or observation care, moderate medical decision making"),
        ("99233", "Subsequent hospital inpatient or observation care, high medical decision making"),
        ("99238", "Hospital inpatient or observation discharge day management, 30 minutes or less"),
        ("99239", "Hospital inpatient or observation discharge day management, more than 30 minutes"),
        ("99281", "Emergency department visit, self-limited or minor problem"),
        ("99282", "Emergency department visit, low complexity problem"),
        ("99283", "Emergency department visit, moderate complexity problem"),
        ("99284", "Emergency department visit, moderate-high complexity problem"),
        ("99285", "Emergency department visit, high complexity problem"),
        ("99291", "Critical care, evaluation and management of the critically ill or critically injured patient; first 30-74 minutes"),
        ("99292", "Critical care, evaluation and management of the critically ill; each additional 30 minutes"),
        ("99381", "Initial comprehensive preventive medicine evaluation, infant (age younger than 1 year)"),
        ("99382", "Initial comprehensive preventive medicine evaluation, early childhood (age 1 through 4 years)"),
        ("99383", "Initial comprehensive preventive medicine evaluation, late childhood (age 5 through 11 years)"),
        ("99384", "Initial comprehensive preventive medicine evaluation, adolescent (age 12 through 17 years)"),
        ("99385", "Initial comprehensive preventive medicine evaluation, 18-39 years"),
        ("99386", "Initial comprehensive preventive medicine evaluation, 40-64 years"),
        ("99387", "Initial comprehensive preventive medicine evaluation, 65 years and older"),
        ("99391", "Periodic comprehensive preventive medicine re-evaluation, infant"),
        ("99392", "Periodic comprehensive preventive medicine re-evaluation, early childhood"),
        ("99393", "Periodic comprehensive preventive medicine re-evaluation, late childhood"),
        ("99394", "Periodic comprehensive preventive medicine re-evaluation, adolescent"),
        ("99395", "Periodic comprehensive preventive medicine re-evaluation, 18-39 years"),
        ("99396", "Periodic comprehensive preventive medicine re-evaluation, 40-64 years"),
        ("99397", "Periodic comprehensive preventive medicine re-evaluation, 65 years and older"),
        ("93000", "Electrocardiogram, routine ECG with at least 12 leads"),
        ("93306", "Echocardiography, transthoracic, real-time with image documentation"),
        ("93308", "Echocardiography, transthoracic, real-time; follow-up or limited study"),
        ("93454", "Catheter placement in coronary artery(s) for coronary angiography"),
        ("71046", "Radiologic examination, chest; 2 views"),
        ("71045", "Radiologic examination, chest; single view"),
        ("70553", "Magnetic resonance imaging, brain with and without contrast"),
        ("70551", "Magnetic resonance imaging, brain without contrast"),
        ("70450", "Computed tomography, head or brain; without contrast material"),
        ("74177", "Computed tomography, abdomen and pelvis; with contrast"),
        ("27447", "Arthroplasty, knee, condyle and plateau; medial and lateral compartments with or without patella resurfacing"),
        ("27130", "Arthroplasty, acetabular and proximal femoral prosthetic replacement (total hip arthroplasty)"),
        ("33533", "Coronary artery bypass, using arterial graft(s); single"),
        ("47562", "Laparoscopic cholecystectomy"),
        ("44950", "Appendectomy"),
        ("43239", "Upper gastrointestinal endoscopy including esophagus, stomach, and either the duodenum"),
        ("45378", "Colonoscopy, flexible; diagnostic"),
        ("45380", "Colonoscopy, flexible; with biopsy, single or multiple"),
        ("10021", "Fine needle aspiration biopsy, without imaging guidance; first lesion"),
        ("36415", "Collection of venous blood by venipuncture"),
        ("80053", "Comprehensive metabolic panel"),
        ("80048", "Basic metabolic panel (calcium, total)"),
        ("85025", "Complete blood count (CBC) with differential WBC count"),
        ("85027", "Complete blood count (CBC); automated, without platelet count"),
        ("80061", "Lipid panel"),
        ("82947", "Glucose; quantitative, blood (except reagent strip)"),
        ("83036", "Hemoglobin; glycosylated (A1C)"),
        ("84443", "Thyroid stimulating hormone (TSH)"),
        ("84153", "Prostate specific antigen (PSA); total"),
        ("86003", "Allergen specific IgE; quantitative or semiquantitative"),
        ("87502", "Influenza virus, for multiple types or subtypes; first 2 types or subtypes"),
        ("87880", "Infectious agent antigen detection; Streptococcus, group A"),
        ("96365", "Intravenous infusion, for therapy, prophylaxis, or diagnosis; initial, up to 1 hour"),
        ("96372", "Therapeutic, prophylactic, or diagnostic injection; subcutaneous or intramuscular"),
        ("96374", "Therapeutic, prophylactic, or diagnostic injection; intravenous push, single or initial substance/drug"),
        ("90837", "Psychotherapy, 60 minutes with patient"),
        ("90834", "Psychotherapy, 45 minutes with patient"),
        ("90832", "Psychotherapy, 30 minutes with patient"),
        ("97110", "Therapeutic procedure, one or more areas, each 15 minutes; therapeutic exercises"),
        ("97140", "Manual therapy techniques, one or more regions, each 15 minutes"),
        ("97530", "Therapeutic activities, direct (one-on-one) patient contact; each 15 minutes"),
        ("20610", "Arthrocentesis, aspiration and/or injection, major joint or bursa; without ultrasound guidance"),
        ("29881", "Arthroscopy, knee, surgical; with meniscectomy (medial OR lateral, including any meniscal shaving)"),
        ("43239", "Esophagogastroduodenoscopy, flexible, transoral; with biopsy, single or multiple"),
    ]
    for code, desc in common_cpts:
        yield {
            "code": code,
            "description": desc,
            "long_description": desc,
            "category": "E/M" if code.startswith(("992", "993")) else "Procedure",
            "search_text": f"CPT {code}: {desc}",
        }
