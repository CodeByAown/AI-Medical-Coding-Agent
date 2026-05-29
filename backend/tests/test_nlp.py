"""Tests for clinical NLP components."""
import pytest
from app.nlp.soap_parser import parse_soap_note, get_coding_relevant_text
from app.nlp.entity_extractor import preprocess_clinical_text


CLINICAL_TEXT = """
The patient has HTN, DM type 2, and SOB.
History of MI 2 years ago. Currently on metformin and lisinopril.
CXR shows cardiomegaly. ECG normal sinus rhythm.
"""


def test_abbreviation_expansion():
    expanded = preprocess_clinical_text(CLINICAL_TEXT)
    assert "hypertension" in expanded.lower()
    assert "diabetes mellitus" in expanded.lower()
    assert "shortness of breath" in expanded.lower()
    assert "myocardial infarction" in expanded.lower()


def test_coding_relevant_text_extraction():
    soap = parse_soap_note(
        "A: Hypertension, well controlled\nP: Continue lisinopril 10mg"
    )
    relevant = get_coding_relevant_text(soap)
    assert "hypertension" in relevant.lower() or "lisinopril" in relevant.lower()
