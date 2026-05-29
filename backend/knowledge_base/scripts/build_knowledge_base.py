#!/usr/bin/env python3
"""
Knowledge Base Builder — downloads and indexes ICD-10, CPT, and HCPCS codes.

Run from the backend/ directory:
    python knowledge_base/scripts/build_knowledge_base.py

This script:
1. Downloads ICD-10-CM data from CDC (free, official)
2. Downloads HCPCS Level II data from CMS (free, official)
3. Builds a built-in CPT common codes set (full CPT requires AMA license)
4. Indexes all codes into ChromaDB vector database
"""
import json
import logging
import os
import sys
import zipfile
from io import BytesIO
from pathlib import Path

import requests
from tqdm import tqdm

# Add backend root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
os.chdir(Path(__file__).parent.parent.parent)

from app.config import get_settings
from app.rag.indexer import index_cpt_codes, index_hcpcs_codes, index_icd10_codes

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()

# Official CMS/CDC download URLs (FY2026)
ICD10_CM_URL = "https://www.cms.gov/files/zip/2026-code-descriptions-tabular-order-update.zip"
ICD10_CM_FALLBACK_URL = "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Publications/ICD10CM/2026/icd10cm_tabular_2026.zip"
HCPCS_URL = "https://www.cms.gov/files/zip/2025-alpha-numeric-hcpcs-file.zip"


def download_file(url: str, dest: Path, description: str) -> bool:
    """Download a file with progress bar. Returns True on success."""
    logger.info(f"Downloading {description} from {url}")
    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        total = int(response.headers.get("content-length", 0))
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f, tqdm(
            desc=description,
            total=total,
            unit="iB",
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in response.iter_content(chunk_size=8192):
                size = f.write(chunk)
                bar.update(size)
        logger.info(f"Downloaded: {dest}")
        return True
    except Exception as e:
        logger.warning(f"Download failed for {url}: {e}")
        return False


def build_icd10_data():
    """Download and parse ICD-10-CM data from CMS."""
    icd10_dir = Path(settings.icd10_data_dir)
    icd10_dir.mkdir(parents=True, exist_ok=True)
    output_file = icd10_dir / "icd10cm_codes.json"

    if output_file.exists():
        logger.info(f"ICD-10 data already exists: {output_file}")
        return True

    # Try to download from CMS
    zip_path = icd10_dir / "icd10cm_2026.zip"
    urls_to_try = [
        "https://www.cms.gov/files/zip/2026-code-descriptions-tabular-order-update.zip",
        "https://www.cms.gov/files/zip/2025-code-descriptions-tabular-order.zip",
    ]

    downloaded = False
    for url in urls_to_try:
        if download_file(url, zip_path, "ICD-10-CM codes"):
            downloaded = True
            break

    if downloaded:
        try:
            codes = []
            with zipfile.ZipFile(zip_path) as zf:
                # Find the order file
                order_files = [n for n in zf.namelist() if "order" in n.lower() and n.endswith(".txt")]
                if not order_files:
                    order_files = [n for n in zf.namelist() if n.endswith(".txt")]

                for fname in order_files[:1]:
                    logger.info(f"Parsing: {fname}")
                    with zf.open(fname) as f:
                        for line in f:
                            line = line.decode("utf-8", errors="replace").rstrip()
                            if len(line) < 16:
                                continue
                            try:
                                # CMS order file format (fixed-width):
                                # [0:5]  = order number
                                # [5]    = space
                                # [6:13] = code (7 chars, right-padded with spaces)
                                # [13]   = space
                                # [14]   = valid flag (1=valid leaf code, 0=header)
                                # [15]   = space
                                # [16:76] = short description (60 chars)
                                # [76:]  = long description
                                code = line[6:13].strip()
                                is_valid = line[14:15].strip() == "1"
                                short_desc = line[15:77].strip()
                                long_desc = line[77:].strip() if len(line) > 77 else short_desc
                                if code and short_desc and is_valid:
                                    codes.append({
                                        "code": code,
                                        "description": short_desc,
                                        "long_description": long_desc,
                                        "category": code[:3],
                                        "chapter": _get_icd10_chapter(code),
                                    })
                            except Exception:
                                continue

            if codes:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(codes, f, indent=2)
                logger.info(f"Saved {len(codes)} ICD-10-CM codes to {output_file}")
                zip_path.unlink(missing_ok=True)
                return True
        except Exception as e:
            logger.error(f"Failed to parse ICD-10 ZIP: {e}")

    # Fallback: create sample data for testing
    logger.warning("Using built-in ICD-10 sample data (run again with internet access for full dataset)")
    _create_sample_icd10(output_file)
    return True


def _create_sample_icd10(output_file: Path):
    """Create a comprehensive sample ICD-10-CM dataset for testing."""
    sample_codes = [
        # Infectious diseases (A, B)
        {"code": "A00.0", "description": "Cholera due to Vibrio cholerae 01, biovar cholerae", "long_description": "Cholera due to Vibrio cholerae 01, biovar cholerae", "category": "A00", "chapter": "Infectious"},
        {"code": "A09", "description": "Other and unspecified gastroenteritis and colitis of infectious origin", "long_description": "Other and unspecified gastroenteritis and colitis of infectious and unspecified origin", "category": "A09", "chapter": "Infectious"},
        {"code": "B34.9", "description": "Viral infection, unspecified", "long_description": "Viral infection, unspecified", "category": "B34", "chapter": "Infectious"},
        # Neoplasms (C, D)
        {"code": "C34.10", "description": "Malignant neoplasm of upper lobe, bronchus or lung, unspecified side", "long_description": "Malignant neoplasm of upper lobe, bronchus or lung, unspecified side", "category": "C34", "chapter": "Neoplasms"},
        {"code": "C50.911", "description": "Malignant neoplasm of unspecified site of right female breast", "long_description": "Malignant neoplasm of unspecified site of right female breast", "category": "C50", "chapter": "Neoplasms"},
        {"code": "C18.9", "description": "Malignant neoplasm of colon, unspecified", "long_description": "Malignant neoplasm of colon, unspecified", "category": "C18", "chapter": "Neoplasms"},
        {"code": "C61", "description": "Malignant neoplasm of prostate", "long_description": "Malignant neoplasm of prostate", "category": "C61", "chapter": "Neoplasms"},
        {"code": "D50.9", "description": "Iron deficiency anemia, unspecified", "long_description": "Iron deficiency anemia, unspecified", "category": "D50", "chapter": "Neoplasms"},
        # Endocrine (E)
        {"code": "E11.9", "description": "Type 2 diabetes mellitus without complications", "long_description": "Type 2 diabetes mellitus without complications", "category": "E11", "chapter": "Endocrine"},
        {"code": "E11.65", "description": "Type 2 diabetes mellitus with hyperglycemia", "long_description": "Type 2 diabetes mellitus with hyperglycemia", "category": "E11", "chapter": "Endocrine"},
        {"code": "E10.9", "description": "Type 1 diabetes mellitus without complications", "long_description": "Type 1 diabetes mellitus without complications", "category": "E10", "chapter": "Endocrine"},
        {"code": "E78.5", "description": "Hyperlipidemia, unspecified", "long_description": "Hyperlipidemia, unspecified", "category": "E78", "chapter": "Endocrine"},
        {"code": "E03.9", "description": "Hypothyroidism, unspecified", "long_description": "Hypothyroidism, unspecified", "category": "E03", "chapter": "Endocrine"},
        {"code": "E11.40", "description": "Type 2 diabetes mellitus with diabetic neuropathy, unspecified", "long_description": "Type 2 diabetes mellitus with diabetic neuropathy, unspecified", "category": "E11", "chapter": "Endocrine"},
        {"code": "E66.9", "description": "Obesity, unspecified", "long_description": "Obesity, unspecified", "category": "E66", "chapter": "Endocrine"},
        # Mental (F)
        {"code": "F32.9", "description": "Major depressive disorder, single episode, unspecified", "long_description": "Major depressive disorder, single episode, unspecified", "category": "F32", "chapter": "Mental"},
        {"code": "F41.1", "description": "Generalized anxiety disorder", "long_description": "Generalized anxiety disorder", "category": "F41", "chapter": "Mental"},
        {"code": "F20.9", "description": "Schizophrenia, unspecified", "long_description": "Schizophrenia, unspecified", "category": "F20", "chapter": "Mental"},
        {"code": "F10.20", "description": "Alcohol dependence, uncomplicated", "long_description": "Alcohol dependence, uncomplicated", "category": "F10", "chapter": "Mental"},
        # Nervous system (G)
        {"code": "G43.909", "description": "Migraine, unspecified, not intractable, without status migrainosus", "long_description": "Migraine, unspecified, not intractable, without status migrainosus", "category": "G43", "chapter": "Nervous"},
        {"code": "G20", "description": "Parkinson's disease", "long_description": "Parkinson's disease", "category": "G20", "chapter": "Nervous"},
        {"code": "G35", "description": "Multiple sclerosis", "long_description": "Multiple sclerosis", "category": "G35", "chapter": "Nervous"},
        {"code": "G40.909", "description": "Epilepsy, unspecified, not intractable, without status epilepticus", "long_description": "Epilepsy, unspecified, not intractable, without status epilepticus", "category": "G40", "chapter": "Nervous"},
        # Eye (H00-H59)
        {"code": "H25.12", "description": "Age-related nuclear cataract, left eye", "long_description": "Age-related nuclear cataract, left eye", "category": "H25", "chapter": "Eye"},
        {"code": "H40.10X0", "description": "Open-angle glaucoma, unspecified, stage unspecified", "long_description": "Open-angle glaucoma, unspecified, stage unspecified", "category": "H40", "chapter": "Eye"},
        # Circulatory (I)
        {"code": "I10", "description": "Essential (primary) hypertension", "long_description": "Essential (primary) hypertension", "category": "I10", "chapter": "Circulatory"},
        {"code": "I21.9", "description": "Acute myocardial infarction, unspecified", "long_description": "Acute myocardial infarction, unspecified", "category": "I21", "chapter": "Circulatory"},
        {"code": "I50.9", "description": "Heart failure, unspecified", "long_description": "Heart failure, unspecified", "category": "I50", "chapter": "Circulatory"},
        {"code": "I63.9", "description": "Cerebral infarction, unspecified", "long_description": "Cerebral infarction, unspecified", "category": "I63", "chapter": "Circulatory"},
        {"code": "I48.91", "description": "Unspecified atrial fibrillation", "long_description": "Unspecified atrial fibrillation", "category": "I48", "chapter": "Circulatory"},
        {"code": "I25.10", "description": "Atherosclerotic heart disease of native coronary artery without angina pectoris", "long_description": "Atherosclerotic heart disease of native coronary artery without angina pectoris", "category": "I25", "chapter": "Circulatory"},
        {"code": "I11.9", "description": "Hypertensive heart disease without heart failure", "long_description": "Hypertensive heart disease without heart failure", "category": "I11", "chapter": "Circulatory"},
        {"code": "I50.32", "description": "Chronic diastolic (congestive) heart failure", "long_description": "Chronic diastolic (congestive) heart failure", "category": "I50", "chapter": "Circulatory"},
        # Respiratory (J)
        {"code": "J18.9", "description": "Pneumonia, unspecified organism", "long_description": "Pneumonia, unspecified organism", "category": "J18", "chapter": "Respiratory"},
        {"code": "J44.1", "description": "Chronic obstructive pulmonary disease with (acute) exacerbation", "long_description": "Chronic obstructive pulmonary disease with (acute) exacerbation", "category": "J44", "chapter": "Respiratory"},
        {"code": "J45.20", "description": "Mild intermittent asthma, uncomplicated", "long_description": "Mild intermittent asthma, uncomplicated", "category": "J45", "chapter": "Respiratory"},
        {"code": "J06.9", "description": "Acute upper respiratory infection, unspecified", "long_description": "Acute upper respiratory infection, unspecified", "category": "J06", "chapter": "Respiratory"},
        {"code": "J44.0", "description": "Chronic obstructive pulmonary disease with acute lower respiratory infection", "long_description": "COPD with acute lower respiratory infection", "category": "J44", "chapter": "Respiratory"},
        # Digestive (K)
        {"code": "K21.0", "description": "Gastro-esophageal reflux disease with esophagitis", "long_description": "Gastro-esophageal reflux disease with esophagitis", "category": "K21", "chapter": "Digestive"},
        {"code": "K21.9", "description": "Gastro-esophageal reflux disease without esophagitis", "long_description": "Gastro-esophageal reflux disease without esophagitis", "category": "K21", "chapter": "Digestive"},
        {"code": "K57.30", "description": "Diverticulosis of large intestine without perforation or abscess without bleeding", "long_description": "Diverticulosis of large intestine without perforation or abscess without bleeding", "category": "K57", "chapter": "Digestive"},
        {"code": "K50.90", "description": "Crohn's disease of small intestine without complications", "long_description": "Crohn's disease of small intestine without complications", "category": "K50", "chapter": "Digestive"},
        # Musculoskeletal (M)
        {"code": "M17.11", "description": "Primary osteoarthritis, right knee", "long_description": "Primary osteoarthritis, right knee", "category": "M17", "chapter": "Musculoskeletal"},
        {"code": "M54.5", "description": "Low back pain", "long_description": "Low back pain", "category": "M54", "chapter": "Musculoskeletal"},
        {"code": "M06.9", "description": "Rheumatoid arthritis, unspecified", "long_description": "Rheumatoid arthritis, unspecified", "category": "M06", "chapter": "Musculoskeletal"},
        {"code": "M10.9", "description": "Gout, unspecified", "long_description": "Gout, unspecified", "category": "M10", "chapter": "Musculoskeletal"},
        {"code": "M81.0", "description": "Age-related osteoporosis without current pathological fracture", "long_description": "Age-related osteoporosis without current pathological fracture", "category": "M81", "chapter": "Musculoskeletal"},
        # Genitourinary (N)
        {"code": "N18.3", "description": "Chronic kidney disease, stage 3 (moderate)", "long_description": "Chronic kidney disease, stage 3 (moderate)", "category": "N18", "chapter": "Genitourinary"},
        {"code": "N18.9", "description": "Chronic kidney disease, unspecified", "long_description": "Chronic kidney disease, unspecified", "category": "N18", "chapter": "Genitourinary"},
        {"code": "N39.0", "description": "Urinary tract infection, site not specified", "long_description": "Urinary tract infection, site not specified", "category": "N39", "chapter": "Genitourinary"},
        {"code": "N40.1", "description": "Benign prostatic hyperplasia with lower urinary tract symptoms", "long_description": "Benign prostatic hyperplasia with lower urinary tract symptoms", "category": "N40", "chapter": "Genitourinary"},
        # Pregnancy (O)
        {"code": "O10.012", "description": "Pre-existing essential hypertension complicating pregnancy, second trimester", "long_description": "Pre-existing essential hypertension complicating pregnancy, second trimester", "category": "O10", "chapter": "Pregnancy"},
        {"code": "O20.0", "description": "Threatened abortion", "long_description": "Threatened abortion", "category": "O20", "chapter": "Pregnancy"},
        # Symptoms (R)
        {"code": "R05.9", "description": "Cough, unspecified", "long_description": "Cough, unspecified", "category": "R05", "chapter": "Symptoms"},
        {"code": "R07.9", "description": "Chest pain, unspecified", "long_description": "Chest pain, unspecified", "category": "R07", "chapter": "Symptoms"},
        {"code": "R10.9", "description": "Unspecified abdominal pain", "long_description": "Unspecified abdominal pain", "category": "R10", "chapter": "Symptoms"},
        {"code": "R50.9", "description": "Fever, unspecified", "long_description": "Fever, unspecified", "category": "R50", "chapter": "Symptoms"},
        {"code": "R53.1", "description": "Weakness", "long_description": "Weakness", "category": "R53", "chapter": "Symptoms"},
        {"code": "R51.9", "description": "Headache, unspecified", "long_description": "Headache, unspecified", "category": "R51", "chapter": "Symptoms"},
        # Injuries (S, T)
        {"code": "S52.501A", "description": "Unspecified fracture of the lower end of right radius, initial encounter for closed fracture", "long_description": "Unspecified fracture of the lower end of right radius, initial encounter for closed fracture", "category": "S52", "chapter": "Injury"},
        {"code": "S72.001A", "description": "Fracture of unspecified part of neck of right femur, initial encounter for closed fracture", "long_description": "Fracture of unspecified part of neck of right femur, initial encounter for closed fracture", "category": "S72", "chapter": "Injury"},
        # External causes (V, W, X, Y)
        {"code": "Z87.891", "description": "Personal history of other specified conditions, nicotine dependence", "long_description": "Personal history of other specified conditions, nicotine dependence", "category": "Z87", "chapter": "Factors"},
        {"code": "Z79.4", "description": "Long-term (current) use of insulin", "long_description": "Long-term (current) use of insulin", "category": "Z79", "chapter": "Factors"},
        {"code": "Z87.39", "description": "Personal history of other endocrine, nutritional and metabolic diseases", "long_description": "Personal history of other endocrine, nutritional and metabolic diseases", "category": "Z87", "chapter": "Factors"},
        {"code": "Z96.641", "description": "Presence of right artificial hip joint", "long_description": "Presence of right artificial hip joint", "category": "Z96", "chapter": "Factors"},
    ]

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(sample_codes, f, indent=2)
    logger.info(f"Created sample ICD-10 data with {len(sample_codes)} codes at {output_file}")


def _get_icd10_chapter(code: str) -> str:
    """Map ICD-10-CM code prefix to chapter name."""
    prefix = code[0].upper()
    chapters = {
        "A": "Infectious and parasitic diseases", "B": "Infectious and parasitic diseases",
        "C": "Neoplasms", "D": "Neoplasms / Blood disorders",
        "E": "Endocrine, nutritional, metabolic",
        "F": "Mental and behavioral disorders",
        "G": "Nervous system",
        "H": "Eye and adnexa / Ear",
        "I": "Circulatory system",
        "J": "Respiratory system",
        "K": "Digestive system",
        "L": "Skin and subcutaneous tissue",
        "M": "Musculoskeletal and connective tissue",
        "N": "Genitourinary system",
        "O": "Pregnancy, childbirth and puerperium",
        "P": "Perinatal conditions",
        "Q": "Congenital malformations",
        "R": "Symptoms, signs, abnormal findings",
        "S": "Injury, poisoning",
        "T": "Injury, poisoning (continued)",
        "V": "External causes",
        "W": "External causes",
        "X": "External causes",
        "Y": "External causes",
        "Z": "Factors influencing health status",
    }
    return chapters.get(prefix, "Unknown")


def build_hcpcs_data():
    """Download HCPCS Level II data from CMS."""
    hcpcs_dir = Path(settings.hcpcs_data_dir)
    hcpcs_dir.mkdir(parents=True, exist_ok=True)
    output_file = hcpcs_dir / "hcpcs_codes.json"

    if output_file.exists():
        logger.info(f"HCPCS data already exists: {output_file}")
        return True

    zip_path = hcpcs_dir / "hcpcs_2025.zip"
    urls = [
        "https://www.cms.gov/files/zip/2025-alpha-numeric-hcpcs-file.zip",
        "https://www.cms.gov/files/zip/2024-alpha-numeric-hcpcs-file.zip",
    ]

    for url in urls:
        if download_file(url, zip_path, "HCPCS codes"):
            break

    if zip_path.exists():
        try:
            with zipfile.ZipFile(zip_path) as zf:
                files = zf.namelist()
                logger.info(f"ZIP contains: {files[:5]}")
                # CMS HCPCS file is usually a flat file
                for fname in files:
                    if fname.lower().endswith(".txt") or fname.lower().endswith(".csv"):
                        with zf.open(fname) as f:
                            codes = _parse_hcpcs_file(f.read().decode("utf-8", errors="replace"))
                        if codes:
                            with open(output_file, "w", encoding="utf-8") as out:
                                json.dump(codes, out, indent=2)
                            logger.info(f"Saved {len(codes)} HCPCS codes")
                            zip_path.unlink(missing_ok=True)
                            return True
        except Exception as e:
            logger.warning(f"HCPCS parsing failed: {e}")

    # Minimal fallback
    logger.info("Creating minimal HCPCS dataset")
    _create_sample_hcpcs(output_file)
    return True


def _parse_hcpcs_file(content: str) -> list:
    codes = []
    for line in content.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            code = parts[0].strip()
            desc = parts[1].strip() if len(parts) > 1 else ""
            if code and desc and len(code) == 5 and code[0].isalpha():
                codes.append({"code": code, "description": desc})
    return codes


def _create_sample_hcpcs(output_file: Path):
    sample = [
        {"code": "A0425", "description": "Ground mileage, per statute mile"},
        {"code": "A4253", "description": "Blood glucose test strips for home blood glucose monitor, per 50 strips"},
        {"code": "E0601", "description": "Continuous airway pressure (CPAP) device"},
        {"code": "E1390", "description": "Oxygen concentrator, single delivery port, capable of delivering 85 percent or greater oxygen concentration at the prescribed flow rate"},
        {"code": "J0696", "description": "Injection, ceftriaxone sodium, per 250 mg"},
        {"code": "J2788", "description": "Injection, rho D immune globulin, intravenous, human, solvent detergent, 100 IU"},
        {"code": "L3000", "description": "Foot insert, removable, molded to patient model, UCB type, Berkeley shell, each"},
        {"code": "G0008", "description": "Administration of influenza virus vaccine"},
        {"code": "G0009", "description": "Administration of pneumococcal vaccine"},
        {"code": "G0283", "description": "Electrical stimulation (unattended), to one or more areas for indication(s) other than wound care"},
        {"code": "G2066", "description": "Opioid treatment program, weekly bundle including drug testing, counseling, individual and group therapy, and toxicology testing"},
        {"code": "T1000", "description": "Private duty/independent nursing service(s), licensed, up to 15 minutes"},
        {"code": "S9083", "description": "Global fee urgent care centers"},
        {"code": "Q2017", "description": "Injection, teniposide, 50 mg"},
    ]
    with open(output_file, "w") as f:
        json.dump(sample, f, indent=2)
    logger.info(f"Created sample HCPCS data ({len(sample)} codes)")


def main():
    logger.info("=" * 60)
    logger.info("AI Medical Coder — Knowledge Base Builder")
    logger.info("=" * 60)

    print("\n1. Building ICD-10-CM database...")
    build_icd10_data()

    print("\n2. Building HCPCS database...")
    build_hcpcs_data()

    print("\n3. Building vector indices (this may take a few minutes)...")
    icd10_count = index_icd10_codes(force_rebuild=True)
    print(f"   ICD-10 indexed: {icd10_count} codes")

    cpt_count = index_cpt_codes(force_rebuild=True)
    print(f"   CPT indexed: {cpt_count} codes")

    hcpcs_count = index_hcpcs_codes(force_rebuild=True)
    print(f"   HCPCS indexed: {hcpcs_count} codes")

    print("\n" + "=" * 60)
    print(f"Knowledge base ready:")
    print(f"  ICD-10-CM: {icd10_count} codes")
    print(f"  CPT:       {cpt_count} codes")
    print(f"  HCPCS:     {hcpcs_count} codes")
    print("=" * 60)

    if icd10_count == 0:
        print("\nWARNING: ICD-10 knowledge base is empty!")
        print("For the full ICD-10-CM dataset (75,000+ codes), download manually from:")
        print("  https://www.cms.gov/medicare/coding-billing/icd-10-codes")
        print("Place the order file as: knowledge_base/data/icd10/icd10cm_codes.json")


if __name__ == "__main__":
    main()
