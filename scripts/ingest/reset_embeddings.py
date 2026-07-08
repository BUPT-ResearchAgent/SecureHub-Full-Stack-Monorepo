# Status: real

"""Safely reset old chunk embeddings before rebuilding a target profile."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import text  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.session import get_sessionmaker  # noqa: E402
from app.knowledge.loaders.embed_chunks import EMBEDDING_METADATA_KEYS  # noqa: E402


async def profile_distribution() -> list[tuple[str, str, int]]:
    async with get_sessionmaker()() as session:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT COALESCE(metadata->>'embedding_profile', '<legacy-unprofiled>') AS profile,
                           embedding_status,
                           COUNT(*) AS count
                    FROM chunks
                    GROUP BY 1, 2
                    ORDER BY 1, 2
                    """
                )
            )
        ).all()
    return [(str(row.profile), str(row.embedding_status), int(row.count)) for row in rows]


async def status_distribution() -> list[tuple[str, int]]:
    async with get_sessionmaker()() as session:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT embedding_status, COUNT(*) AS count
                    FROM chunks
                    GROUP BY embedding_status
                    ORDER BY embedding_status
                    """
                )
            )
        ).all()
    return [(str(row.embedding_status), int(row.count)) for row in rows]


async def count_matches(
    *,
    from_profile: str | None,
    to_profile: str,
    include_legacy_unprofiled_ready: bool,
) -> dict[str, int]:
    async with get_sessionmaker()() as session:
        legacy = 0
        if include_legacy_unprofiled_ready:
            legacy = int(
                await session.scalar(
                    text(
                        """
                        SELECT COUNT(*) FROM chunks
                        WHERE embedding_status = 'ready'
                          AND embedding IS NOT NULL
                          AND metadata->>'embedding_profile' IS NULL
                        """
                    )
                )
                or 0
            )
        profiled = 0
        if from_profile:
            profiled = int(
                await session.scalar(
                    text(
                        """
                        SELECT COUNT(*) FROM chunks
                        WHERE embedding_status = 'ready'
                          AND embedding IS NOT NULL
                          AND metadata->>'embedding_profile' = :from_profile
                          AND metadata->>'embedding_profile' <> :to_profile
                        """
                    ),
                    {"from_profile": from_profile, "to_profile": to_profile},
                )
                or 0
            )
        pending = int(
            await session.scalar(
                text("SELECT COUNT(*) FROM chunks WHERE embedding_status = 'pending'")
            )
            or 0
        )
    return {"legacy_unprofiled_ready": legacy, "from_profile_ready": profiled, "pending": pending}


async def reset_embeddings(
    *,
    from_profile: str | None,
    to_profile: str,
    include_legacy_unprofiled_ready: bool,
    dry_run: bool,
) -> dict[str, Any]:
    before_status = await status_distribution()
    before_profiles = await profile_distribution()
    counts = await count_matches(
        from_profile=from_profile,
        to_profile=to_profile,
        include_legacy_unprofiled_ready=include_legacy_unprofiled_ready,
    )
    if dry_run:
        return {
            "dry_run": True,
            "counts": counts,
            "before_status": before_status,
            "before_profiles": before_profiles,
        }

    predicates: list[str] = []
    params: dict[str, Any] = {"to_profile": to_profile}
    if include_legacy_unprofiled_ready:
        predicates.append(
            """
            (embedding_status = 'ready'
             AND embedding IS NOT NULL
             AND metadata->>'embedding_profile' IS NULL)
            """
        )
    if from_profile:
        predicates.append(
            """
            (embedding_status = 'ready'
             AND embedding IS NOT NULL
             AND metadata->>'embedding_profile' = :from_profile
             AND metadata->>'embedding_profile' <> :to_profile)
            """
        )
        params["from_profile"] = from_profile
    if not predicates:
        raise ValueError("No reset selector supplied; use --from-profile and/or --include-legacy-unprofiled-ready")

    metadata_expr = "metadata"
    for key in sorted(EMBEDDING_METADATA_KEYS):
        metadata_expr = f"({metadata_expr} - '{key}')"

    async with get_sessionmaker()() as session:
        result = await session.execute(
            text(
                f"""
                UPDATE chunks
                SET embedding = NULL,
                    embedding_status = 'pending',
                    metadata = {metadata_expr}
                WHERE {' OR '.join(predicates)}
                """
            ),
            params,
        )
        await session.commit()
        updated = int(result.rowcount or 0)

    return {
        "dry_run": False,
        "updated": updated,
        "counts": counts,
        "before_status": before_status,
        "before_profiles": before_profiles,
        "after_status": await status_distribution(),
        "after_profiles": await profile_distribution(),
    }


def parse_args() -> argparse.Namespace:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Reset old chunk embeddings safely.")
    parser.add_argument("--from-profile", default=None)
    parser.add_argument("--to-profile", default=settings.EMBEDDING_PROFILE)
    parser.add_argument("--include-legacy-unprofiled-ready", action="store_true")
    parser.add_argument("--yes", action="store_true", help="Actually update rows. Default is dry-run.")
    parser.add_argument("--dry-run", action="store_true", help="Force dry-run even if --yes is absent.")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    dry_run = args.dry_run or not args.yes
    result = await reset_embeddings(
        from_profile=args.from_profile,
        to_profile=args.to_profile,
        include_legacy_unprofiled_ready=args.include_legacy_unprofiled_ready,
        dry_run=dry_run,
    )
    print("[reset_embeddings]")
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
