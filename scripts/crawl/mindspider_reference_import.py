# Status: real

"""Import MindSpider reference fixture topics into SecureHub data-layer v2."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import get_sessionmaker  # noqa: E402
from app.services.knowledge.crawling.mindspider_adapter import (  # noqa: E402
    import_mindspider_fixture,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import MindSpider reference fixture topics.")
    parser.add_argument(
        "--fixture",
        type=Path,
        default=REPO_ROOT / "data" / "raw" / "mindspider" / "hot_topics_fixture.json",
    )
    parser.add_argument("--domain", default="news")
    parser.add_argument("--storage-prefix", default="news/mindspider_reference")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        result = await import_mindspider_fixture(
            args.fixture,
            domain=args.domain,
            storage_prefix=args.storage_prefix,
            session=session,
        )
        await session.commit()
    print(
        "[mindspider_reference_import] "
        f"documents={len(result.document_ids)} chunks={result.chunk_count} "
        f"assets={result.asset_count} topics={result.topic_count} "
        f"domain={args.domain}"
    )


if __name__ == "__main__":
    asyncio.run(main())
