"""
Utility modules for AI Medical Coder.

Exports:
    get_logger         — structured logger factory
    run_sync           — run blocking functions in thread pool
    PHIEncryption      — AES-256-GCM encryption for PHI fields
    get_phi_encryption — get module-level PHI encryption singleton
"""
from app.utils.logging_config import configure_logging, get_logger
from app.utils.async_utils import run_sync, run_sync_with_executor
from app.utils.encryption import PHIEncryption, get_phi_encryption

__all__ = [
    "configure_logging",
    "get_logger",
    "run_sync",
    "run_sync_with_executor",
    "PHIEncryption",
    "get_phi_encryption",
]
