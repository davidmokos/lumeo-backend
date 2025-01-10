from src.database.base import Repository
from src.schema.lecture import Lecture


class LectureRepository(Repository[Lecture]):
    def __init__(self):
        super().__init__("lectures", Lecture) 