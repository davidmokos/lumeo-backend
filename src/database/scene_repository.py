from src.database.base import Repository
from src.schema.scene import Scene


class SceneRepository(Repository[Scene]):
    def __init__(self):
        super().__init__("scenes", Scene)
        
    async def list_by_lecture(self, lecture_id: str) -> list[Scene]:
        """Get all scenes for a specific lecture"""
        return await self.list(filters={"lecture_id": lecture_id}) 