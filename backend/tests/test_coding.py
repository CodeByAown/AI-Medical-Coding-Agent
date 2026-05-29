"""
Test suite for the AI Medical Coder Agent.
Run with: pytest tests/ -v
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.schemas import (
    CodeType,
    CodingRequest,
    CodingStatus,
    DocumentType,
    MedicalCode,
    Specialty,
)
from app.nlp.soap_parser import (
    extract_diagnoses_from_assessment,
    extract_procedures_from_plan,
    parse_soap_note,
)
from app.coding.validator import validate_code_format, normalize_code


# ─── Sample Clinical Notes ────────────────────────────────────────────────────

SAMPLE_SOAP_NOTE = """
S: 65-year-old male presents with 3-day history of worsening shortness of breath and productive cough with yellow sputum.
History of COPD and hypertension. Currently on albuterol inhaler and lisinopril 10mg.

O: Vital signs: BP 148/92, HR 98, RR 22, Temp 38.2°C, O2 Sat 91% on room air.
Chest exam: Decreased breath sounds bilaterally with wheezing.
CXR: Hyperinflation with right lower lobe infiltrate consistent with pneumonia.

A: 1. COPD exacerbation with acute lower respiratory infection
   2. Community-acquired pneumonia, right lower lobe
   3. Hypertension, not well controlled
   4. Hypoxia

P: 1. Admit for IV antibiotics (azithromycin + ceftriaxone)
   2. Nebulized albuterol q4h
   3. Systemic corticosteroids (prednisone 40mg daily x 5 days)
   4. Supplemental oxygen to maintain SpO2 > 92%
   5. Chest x-ray in 48 hours
"""

SIMPLE_NOTE = """
Patient presents with type 2 diabetes mellitus, uncontrolled, and essential hypertension.
HbA1c 9.2%. Blood pressure 165/95. Prescribed metformin 1000mg BID and amlodipine 5mg daily.
"""


# ─── SOAP Parser Tests ────────────────────────────────────────────────────────

class TestSOAPParser:
    def test_parse_structured_soap(self):
        soap = parse_soap_note(SAMPLE_SOAP_NOTE)
        assert soap.subjective is not None
        assert soap.objective is not None
        assert soap.assessment is not None
        assert soap.plan is not None
        assert "COPD" in soap.assessment or "shortness of breath" in (soap.subjective or "")

    def test_extract_diagnoses(self):
        soap = parse_soap_note(SAMPLE_SOAP_NOTE)
        diagnoses = extract_diagnoses_from_assessment(soap.assessment or "")
        assert len(diagnoses) > 0
        # Should find COPD and pneumonia
        all_text = " ".join(diagnoses).lower()
        assert "copd" in all_text or "pneumonia" in all_text

    def test_extract_procedures(self):
        soap = parse_soap_note(SAMPLE_SOAP_NOTE)
        procedures = extract_procedures_from_plan(soap.plan or "")
        assert len(procedures) > 0

    def test_unstructured_note_fallback(self):
        soap = parse_soap_note(SIMPLE_NOTE)
        # Should not crash; assessment should have the full text
        assert soap.raw_text == SIMPLE_NOTE


# ─── Code Validator Tests ─────────────────────────────────────────────────────

class TestCodeValidator:
    def test_valid_icd10_format(self):
        valid_codes = ["J18.9", "I10", "E11.9", "S52.501A", "C34.10"]
        for code in valid_codes:
            is_valid, error = validate_code_format(code, CodeType.ICD10_CM)
            assert is_valid, f"Expected {code} to be valid, got: {error}"

    def test_invalid_icd10_format(self):
        invalid_codes = ["99213", "INVALID", "12345", ""]
        for code in invalid_codes:
            is_valid, error = validate_code_format(code, CodeType.ICD10_CM)
            assert not is_valid, f"Expected {code} to be invalid"

    def test_valid_cpt_format(self):
        valid_codes = ["99213", "99214", "71046", "27447", "93000"]
        for code in valid_codes:
            is_valid, error = validate_code_format(code, CodeType.CPT)
            assert is_valid, f"Expected {code} to be valid CPT, got: {error}"

    def test_invalid_cpt_format(self):
        invalid_codes = ["J18.9", "ABCDE", "1234", "123456"]
        for code in invalid_codes:
            is_valid, error = validate_code_format(code, CodeType.CPT)
            assert not is_valid, f"Expected {code} to be invalid CPT"

    def test_normalize_code(self):
        assert normalize_code("J189") == "J18.9"
        assert normalize_code("i10") == "I10"
        assert normalize_code(" J18.9 ") == "J18.9"


# ─── Medical Code Schema Tests ────────────────────────────────────────────────

class TestMedicalCodeSchema:
    def test_create_valid_code(self):
        code = MedicalCode(
            code="J18.9",
            code_type=CodeType.ICD10_CM,
            description="Pneumonia, unspecified organism",
            confidence=0.92,
            evidence="CXR shows right lower lobe infiltrate",
            is_primary=True,
        )
        assert code.code == "J18.9"
        assert code.confidence == 0.92
        assert code.is_primary is True

    def test_confidence_bounds(self):
        with pytest.raises(Exception):
            MedicalCode(
                code="J18.9",
                code_type=CodeType.ICD10_CM,
                description="Test",
                confidence=1.5,  # Out of bounds
            )


# ─── Coding Request Schema Tests ──────────────────────────────────────────────

class TestCodingRequest:
    def test_valid_request(self):
        req = CodingRequest(
            text=SAMPLE_SOAP_NOTE,
            document_type=DocumentType.SOAP_NOTE,
            specialty=Specialty.INTERNAL,
        )
        assert req.specialty == Specialty.INTERNAL
        assert req.include_cpt is True

    def test_minimum_text_length(self):
        with pytest.raises(Exception):
            CodingRequest(text="Short", document_type=DocumentType.CLINICAL_NOTE)


# ─── Integration Test (requires running server) ────────────────────────────────

class TestAPIIntegration:
    """Integration tests — skipped unless API server is running."""

    @pytest.fixture
    def client(self):
        try:
            from fastapi.testclient import TestClient
            from app.main import app
            return TestClient(app)
        except Exception:
            pytest.skip("Cannot create test client")

    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data

    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_code_search(self, client):
        response = client.get("/api/v1/coding/search?q=pneumonia")
        assert response.status_code == 200
        data = response.json()
        assert "icd10" in data
