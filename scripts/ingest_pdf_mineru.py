# Status: real

"""Import a PDF plus optional MinerU Markdown output into data-layer v2.

Example:
    uv run python ../scripts/ingest_pdf_mineru.py ../data/raw/pdf/demo.pdf \
        --mineru-output ../data/processed/mineru/demo \
        --title "SQL 注入教材节选"
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import get_sessionmaker  # noqa: E402
from app.knowledge.loaders.course_loader import pdf_mineru_import  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import PDF/MinerU output into SecureHub.")
    parser.add_argument("pdf", type=Path, help="Path to the original PDF file.")
    parser.add_argument("--mineru-output", type=Path, default=None, help="MinerU output directory.")
    parser.add_argument("--domain", default="course_websec", help="Target knowledge domain.")
    parser.add_argument("--title", default=None, help="Document title override.")
    parser.add_argument("--source-url", default=None, help="Original source URL.")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    if not args.pdf.exists():
        raise SystemExit(f"PDF not found: {args.pdf}")

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        result = await pdf_mineru_import(
            args.pdf,
            session=session,
            mineru_output_dir=args.mineru_output,
            domain=args.domain,
            title=args.title,
            source_url=args.source_url,
        )
        await session.commit()

    print(
        "[ingest_pdf_mineru] "
        f"documents={len(result.document_ids)} chunks={result.chunk_count} "
        f"assets={result.asset_count} domain={result.domain}"
    )


if __name__ == "__main__":
    asyncio.run(main())
