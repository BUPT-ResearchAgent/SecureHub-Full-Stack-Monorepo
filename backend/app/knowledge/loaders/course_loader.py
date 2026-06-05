# Status: [planned]

from pathlib import Path
from uuid import UUID

from pydantic import BaseModel


class CourseLoadResult(BaseModel):
    document_ids: list[UUID]
    chunk_count: int
    domain: str = "course_websec"


async def load_course_materials(paths: list[Path], *, domain: str = "course_websec") -> CourseLoadResult:
    raise NotImplementedError("TODO: load course PDF/Markdown files into documents and chunks")
