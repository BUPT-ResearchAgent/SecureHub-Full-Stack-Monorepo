#!/usr/bin/env sh
set -eu

# Status: real

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

cd "$REPO_ROOT/backend"
if command -v uv >/dev/null 2>&1; then
  uv run python -m app.db.seeds.seed_course_websec
else
  python -m app.db.seeds.seed_course_websec
fi
