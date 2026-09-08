from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> Optional[User]:
        query = select(User).where(User.email == email.lower().strip())
        result = await self.session.execute(query)
        return result.scalars().first()

    async def exists_by_email(self, email: str) -> bool:
        user = await self.get_by_email(email)
        return user is not None
