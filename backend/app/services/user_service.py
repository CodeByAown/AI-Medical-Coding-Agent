"""
User management service — CRUD for User accounts.
"""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.password import hash_password, verify_password
from app.auth.rbac import UserRole
from app.models.database import User
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


async def create_user(
    db: AsyncSession,
    email: str,
    password: str,
    role: UserRole = UserRole.CODER,
    full_name: Optional[str] = None,
) -> User:
    """Create a new user with hashed password."""
    user = User(
        email=email.lower().strip(),
        hashed_password=hash_password(password),
        role=role.value,
        full_name=full_name,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("user_created", email=email, role=role.value)
    return user


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Fetch a user by email address."""
    result = await db.execute(select(User).where(User.email == email.lower().strip()))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Fetch a user by primary key."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> Optional[User]:
    """Verify email + password. Returns User or None."""
    user = await get_user_by_email(db, email)
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    # Update last_login
    user.last_login = datetime.now(timezone.utc)
    await db.commit()
    return user


async def list_users(db: AsyncSession) -> List[User]:
    """List all users (admin only)."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return list(result.scalars().all())
