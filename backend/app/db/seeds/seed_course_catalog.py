# Status: real

"""Idempotently seed the four durable course product rows.

Only the ``courses`` table is touched here.  The ready Web security graph,
documents and evidence continue to be owned by ``seed_course_websec``; preview
courses deliberately receive no generated content or knowledge assets.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seeds._constants import COURSE_PRODUCTS
from app.repositories.knowledge.courses import CourseRepository


async def run(session: AsyncSession) -> dict[str, int]:
    """Upsert the fixed product list without changing a row's canonical UUID."""
    repository = CourseRepository(session)
    created = 0
    updated = 0

    for product in COURSE_PRODUCTS:
        existing = await repository.get_by_code(product.code)
        if existing is None:
            await repository.create(
                course_id=product.id,
                code=product.code,
                title=product.title,
                domain=product.domain,
                description=product.description,
            )
            created += 1
            continue

        # A code is the durable row identity in the existing schema.  Moving
        # its UUID would strand nodes/resources, so surface drift explicitly.
        if existing.id != product.id:
            raise RuntimeError(
                f"course {product.code} has unexpected id {existing.id}; expected {product.id}"
            )
        if (
            existing.title != product.title
            or existing.domain != product.domain
            or existing.description != product.description
        ):
            existing.title = product.title
            existing.domain = product.domain
            existing.description = product.description
            updated += 1

    await session.flush()
    return {"course_products_created": created, "course_products_updated": updated}


__all__ = ["run"]
