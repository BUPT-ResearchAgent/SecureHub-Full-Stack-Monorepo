# Status: real

"""Repository-level wrapper for the public web importer.

Host-side usage:
    cd backend
    uv run python ../scripts/crawl/scrapling_public_import.py --preset websec-core --replace

Docker backend-container usage:
    docker compose exec backend sh -lc \
      "uv run python -m app.knowledge.loaders.scrapling_public_importer --preset websec-core --replace"

Source-file rows may be JSON/JSONL/CSV with these optional fields:
url,title,platform,author,published_at,license,rights_note,source_type,
asset_type,reliability,css_selector,xpath,metadata
"""

from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.knowledge.loaders.scrapling_public_importer import main  # noqa: E402


if __name__ == "__main__":
    main()
