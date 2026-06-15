# Status: real

"""Import MediaCrawler JSON/JSONL/CSV exports into SecureHub data-layer v2.

Example:
    cd backend
    uv run python ../scripts/crawl/mediacrawler_export_import.py \
        ../data/raw/mediacrawler/xhs --platform xhs --domain course_websec
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import get_sessionmaker  # noqa: E402
from app.services.knowledge.crawling.mediacrawler_export_import import (  # noqa: E402
    import_mediacrawler_exports,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import offline MediaCrawler exports into SecureHub."
    )
    parser.add_argument("paths", nargs="+", type=Path, help="JSON/JSONL/CSV files or directories.")
    parser.add_argument("--platform", choices=["bili", "bilibili", "xhs", "zhihu"], default=None)
    parser.add_argument("--domain", default="course_websec")
    parser.add_argument("--storage-prefix", default="course_websec/mediacrawler")
    parser.add_argument(
        "--rights-note",
        default=None,
        help="Override source rights note for all imported rows.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        result = await import_mediacrawler_exports(
            args.paths,
            session=session,
            platform=args.platform,
            domain=args.domain,
            storage_prefix=args.storage_prefix,
            rights_note=args.rights_note,
        )
        await session.commit()
    print(
        "[mediacrawler_export_import] "
        f"documents={len(result.document_ids)} chunks={result.chunk_count} "
        f"assets={result.asset_count} contents={result.content_count} "
        f"comments={result.comment_count} domain={result.domain}"
    )


if __name__ == "__main__":
    asyncio.run(main())
