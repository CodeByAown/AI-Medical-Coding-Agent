"""
CLI script to create the initial admin user.

Usage:
    cd backend
    python scripts/create_admin.py --email admin@example.com --password SecurePass123!
"""
import argparse
import asyncio
import sys
from pathlib import Path

# Add backend root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.auth.rbac import UserRole
from app.models.database import init_db, get_async_session
from app.services.user_service import create_user, get_user_by_email


async def main(email: str, password: str):
    await init_db()
    async with get_async_session() as db:
        existing = await get_user_by_email(db, email)
        if existing:
            print(f"User {email} already exists (role: {existing.role})")
            return
        user = await create_user(db, email, password, UserRole.ADMIN, "System Admin")
        print(f"Created admin user: {user.email} (id: {user.id})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create admin user")
    parser.add_argument("--email", required=True, help="Admin email address")
    parser.add_argument("--password", required=True, help="Admin password")
    args = parser.parse_args()

    # Load .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    asyncio.run(main(args.email, args.password))
