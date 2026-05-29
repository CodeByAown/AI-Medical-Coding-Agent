"""Diagnostic: check DB tables and users."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def check():
    from app.models.database import async_session_maker, init_db, User
    from sqlalchemy import select, text

    await init_db()

    async with async_session_maker() as db:
        result = await db.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [r[0] for r in result.fetchall()]
        print("Tables:", tables)

        result = await db.execute(select(User))
        users = result.scalars().all()
        print("Users:", len(users))
        for u in users:
            print(f"  {u.email}  role={u.role}  active={u.is_active}")

asyncio.run(check())
