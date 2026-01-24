import asyncio
import os
import sys

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from backend.app.db.session import AsyncSessionLocal
from backend.app.services.novel_service import NovelService
from backend.app.models.user import User
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as session:
        # Get a user (e.g., desktop_user)
        result = await session.execute(select(User).where(User.username == "desktop_user"))
        user = result.scalars().first()
        
        if not user:
            print("User 'desktop_user' not found.")
            # Try to create one if needed, or just pick the first user
            result = await session.execute(select(User))
            user = result.scalars().first()
            if not user:
                print("No users found.")
                return

        print(f"Testing list_novels for user: {user.username} ({user.id})")
        
        service = NovelService(session)
        try:
            summaries, total = await service.list_projects_for_user(user.id)
            print(f"Success! Total projects: {total}")
            for s in summaries:
                print(f"  - {s.title} ({s.id})")
        except Exception as e:
            print(f"Error calling list_projects_for_user: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
