"""Tests for PHI encryption utilities."""
import base64
import pytest
from app.utils.encryption import PHIEncryption


def test_encrypt_decrypt_roundtrip():
    phi = PHIEncryption()
    plaintext = "Patient has acute myocardial infarction with diabetes."
    ciphertext = phi.encrypt(plaintext)
    assert ciphertext != plaintext
    decrypted = phi.decrypt(ciphertext)
    assert decrypted == plaintext


def test_encrypt_empty_string():
    phi = PHIEncryption()
    assert phi.encrypt("") == ""
    assert phi.decrypt("") == ""


def test_different_nonces_each_time():
    phi = PHIEncryption()
    c1 = phi.encrypt("same text")
    c2 = phi.encrypt("same text")
    assert c1 != c2  # Different nonces → different ciphertext


def test_generate_key():
    key = PHIEncryption.generate_key_b64()
    assert len(key) > 0
    # Should be valid base64 and decode to 32 bytes
    raw = base64.b64decode(key)
    assert len(raw) == 32


def test_key_from_b64():
    key_b64 = PHIEncryption.generate_key_b64()
    phi = PHIEncryption(key_b64=key_b64)
    plaintext = "Sensitive PHI data"
    assert phi.decrypt(phi.encrypt(plaintext)) == plaintext


def test_wrong_key_returns_ciphertext():
    """Decryption with wrong key returns original input (legacy data handling)."""
    phi1 = PHIEncryption()
    phi2 = PHIEncryption()  # Different ephemeral key
    ciphertext = phi1.encrypt("some data")
    # Should not raise, returns ciphertext as-is
    result = phi2.decrypt(ciphertext)
    # Result is the ciphertext unchanged (legacy fallback behavior)
    assert result == ciphertext
