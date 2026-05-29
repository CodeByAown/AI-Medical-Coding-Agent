"""
Authentication endpoints — login, refresh, logout, user management.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from app.auth.rbac import UserRole
from app.models.database import get_db
from app.services.audit_service import AuditAction, log_audit_event
from app.services.user_service import authenticate_user, create_user, get_user_by_id
from app.utils.logging_config import get_logger

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = get_logger(__name__)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    email: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str
    role: UserRole = UserRole.CODER
    full_name: Optional[str] = None


@router.post("/token", response_model=TokenResponse)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return JWT tokens."""
    ip = request.client.host if request.client else "unknown"
    user = await authenticate_user(db, form_data.username, form_data.password)

    if not user:
        await log_audit_event(
            db, AuditAction.LOGIN_FAILED,
            ip_address=ip,
            details={"email": form_data.username},
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        user_id=str(user.id),
        email=user.email,
        role=UserRole(user.role),
    )
    refresh_token = create_refresh_token(user_id=str(user.id))

    await log_audit_event(
        db, AuditAction.LOGIN,
        user_id=str(user.id),
        ip_address=ip,
    )
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=user.role,
        email=user.email,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Exchange a refresh token for a new access token."""
    try:
        user_id = decode_refresh_token(body.refresh_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = await get_user_by_id(db, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or deactivated")

    access_token = create_access_token(
        user_id=str(user.id),
        email=user.email,
        role=UserRole(user.role),
    )
    new_refresh_token = create_refresh_token(user_id=str(user.id))

    await log_audit_event(db, AuditAction.TOKEN_REFRESHED, user_id=str(user.id))
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        role=user.role,
        email=user.email,
    )


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_new_user(
    body: UserCreateRequest,
    db: AsyncSession = Depends(get_db),
    # In production, require admin token here — for now open for initial setup
):
    """Create a new user account. Restrict to admin in production."""
    try:
        user = await create_user(
            db,
            email=body.email,
            password=body.password,
            role=body.role,
            full_name=body.full_name,
        )
        return {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at.isoformat(),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
