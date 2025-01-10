from typing import Optional

from src.database.base import Repository
from src.schema.user import User


class UserRepository(Repository[User]):
    def __init__(self):
        super().__init__("users", User)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email"""
        results = await self.list(filters={"email": email})
        return results[0] if results else None
    