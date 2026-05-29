"""
FastAPI dependency injection for authentication and authorization.
Supports JWT Bearer tokens (primary) with optional static API key fallback (dev/service accounts).
"""
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.auth.jwt_handler import decode_access_token
from app.auth.rbac import Permission, UserRole, has_permission
from app.config import get_settings
from app.utils.logging_config import get_logger

settings = get_settings()
logger = get_logger(__name__)

# JWT Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser:
    """Represents the authenticated user in a request context."""
    def __init__(self, user_id: str, email: str, role: UserRole):
        self.user_id = user_id
        self.email = email
        self.role = role

    def require(self, permission: Permission) -> None:
        if not has_permission(self.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: requires '{permission}'",
            )


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> CurrentUser:
    """
    Dependency: validate JWT Bearer token and return CurrentUser.
    Falls back to API key auth if no JWT present and API keys are configured.
    In dev mode (ALLOWED_API_KEYS empty AND no credentials), returns a dev user without auth.
    """
    # Dev mode — no auth enforcement when nothing is configured
    if not settings.api_keys_list and not credentials:
        return CurrentUser(
            user_id="dev-user",
            email="dev@localhost",
            role=UserRole.ADMIN,
        )

    # JWT Bearer token path
    if credentials and credentials.scheme == "Bearer":
        try:
            payload = decode_access_token(credentials.credentials)
            return CurrentUser(
                user_id=payload["sub"],
                email=payload.get("email", ""),
                role=UserRole(payload.get("role", UserRole.CODER.value)),
            )
        except (JWTError, KeyError, ValueError) as exc:
            logger.warning("jwt_validation_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Static API key fallback (service accounts, legacy)
    api_key = request.headers.get(settings.api_key_header)
    if api_key and settings.api_keys_list and api_key in settings.api_keys_list:
        return CurrentUser(
            user_id="api-key-service",
            email="service@localhost",
            role=UserRole.CODER,
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


# Convenience dependency aliases for common role checks
async def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    user.require(Permission.SYSTEM_CONFIG)
    return user


async def require_reviewer(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    user.require(Permission.REVIEW_SUBMIT)
    return user


# Legacy alias for existing routes that used get_current_api_key
async def get_current_api_key(
    user: CurrentUser = Depends(get_current_user),
) -> str:
    """Legacy alias — returns user_id string. Existing routes use this for _ binding."""
    return user.user_id
