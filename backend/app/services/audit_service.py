"""
Audit logging service — HIPAA-required PHI access tracking.
All PHI access, code submissions, and review decisions must be logged
with user identity, timestamp, action, and resource reference.
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AuditLog
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class AuditAction:
    # Authentication events
    LOGIN = "auth.login"
    LOGOUT = "auth.logout"
    LOGIN_FAILED = "auth.login_failed"
    TOKEN_REFRESHED = "auth.token_refreshed"

    # PHI access events
    NOTE_SUBMITTED = "phi.note_submitted"
    SESSION_VIEWED = "phi.session_viewed"
    SESSION_SEARCHED = "phi.session_searched"
    CODE_LOOKED_UP = "phi.code_lookup"

    # Review events
    REVIEW_APPROVED = "review.approved"
    REVIEW_REJECTED = "review.rejected"
    REVIEW_QUEUE_VIEWED = "review.queue_viewed"

    # Admin events
    USER_CREATED = "admin.user_created"
    USER_DEACTIVATED = "admin.user_deactivated"
    CONFIG_CHANGED = "admin.config_changed"

    # System events
    KB_REBUILT = "system.kb_rebuilt"
    ERROR_CRITICAL = "system.error_critical"


async def log_audit_event(
    db: AsyncSession,
    action: str,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Write an immutable audit log entry.
    Failures are logged but not raised — audit must not break primary flow.
    """
    try:
        entry = AuditLog(
            user_id=user_id or "anonymous",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=json.dumps(details) if details else None,
            created_at=datetime.now(timezone.utc),
        )
        db.add(entry)
        # Note: caller is responsible for commit — we don't commit here
        # to allow batching with primary operation
    except Exception as exc:
        logger.error("audit_log_write_failed", error=str(exc), action=action)
