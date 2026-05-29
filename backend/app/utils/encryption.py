"""
PHI encryption utilities — AES-256-GCM for data at rest.
All clinical text and identifiable patient data must be encrypted
before storage to comply with HIPAA Technical Safeguards (164.312).
"""
import base64
import os
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class PHIEncryption:
    """
    AES-256-GCM encryption for PHI fields.
    Key must be 32 bytes (256 bits), stored in environment / secrets manager.
    """

    def __init__(self, key_b64: Optional[str] = None):
        self._ephemeral = False
        if key_b64:
            self._key = base64.b64decode(key_b64)
            if len(self._key) != 32:
                raise ValueError("Encryption key must be 32 bytes (256-bit AES)")
        else:
            # Development only — generate ephemeral key
            # In production, key must come from AWS KMS / Vault / env secret
            self._key = os.urandom(32)
            self._ephemeral = True

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string using AES-256-GCM.
        Returns base64-encoded nonce + ciphertext.
        """
        if not plaintext:
            return plaintext
        aesgcm = AESGCM(self._key)
        nonce = os.urandom(12)  # 96-bit nonce for GCM
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        combined = nonce + ciphertext
        return base64.b64encode(combined).decode("utf-8")

    def decrypt(self, ciphertext_b64: str) -> str:
        """
        Decrypt an AES-256-GCM encrypted string.
        Expects base64-encoded nonce + ciphertext.
        """
        if not ciphertext_b64:
            return ciphertext_b64
        try:
            combined = base64.b64decode(ciphertext_b64)
            nonce = combined[:12]
            ciphertext = combined[12:]
            aesgcm = AESGCM(self._key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode("utf-8")
        except Exception:
            # Return as-is if decryption fails (handles unencrypted legacy data)
            return ciphertext_b64

    @staticmethod
    def generate_key_b64() -> str:
        """Generate a new 256-bit key encoded as base64. Use once, store securely."""
        return base64.b64encode(os.urandom(32)).decode("utf-8")


# Module-level singleton, initialized from config
_phi_encryption: Optional[PHIEncryption] = None


def get_phi_encryption() -> PHIEncryption:
    """Get the module-level PHI encryption instance."""
    global _phi_encryption
    if _phi_encryption is None:
        from app.config import get_settings
        settings = get_settings()
        _phi_encryption = PHIEncryption(
            key_b64=settings.phi_encryption_key if settings.phi_encryption_key else None
        )
    return _phi_encryption
