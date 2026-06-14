# Status: real

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select

from app.db.models.knowledge.course import Course
from app.repositories.base import UUIDPKRepository


class CourseRepository(UUIDPKRepository[Course]):
    model = Course

    async def get_by_code(self, code: str) -> Course | None:
        result = await self.session.execute(select(Course).where(Course.code == code))
        return result.scalar_one_or_none()

    async def list_by_domain(
        self, domain: str, *, limit: int = 50, offset: int = 0
    ) -> Sequence[Course]:
        stmt = (
            select(Course)
            .where(Course.domain == domain)
            .order_by(Course.code)
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_all(self, *, limit: int = 50, offset: int = 0) -> Sequence[Course]:
        stmt = select(Course).order_by(Course.code).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(
        self,
        *,
        course_id: UUID,
        code: str,
        title: str,
        domain: str = "course_websec",
        description: str | None = None,
    ) -> Course:
        row = Course(
            id=course_id,
            code=code,
            title=title,
            domain=domain,
            description=description,
        )
        self.session.add(row)
        await self.session.flush()
        return row
