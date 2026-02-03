from typing import AsyncGenerator
from app.core.database import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session