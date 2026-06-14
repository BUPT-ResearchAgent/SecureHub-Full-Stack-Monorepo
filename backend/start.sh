#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy

APP="${APP:-app.main:app}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

echo "Starting SecureHub backend at http://${HOST}:${PORT}"

if command -v uv >/dev/null 2>&1; then
  exec uv run uvicorn "${APP}" --host "${HOST}" --port "${PORT}" "$@"
fi

if command -v python >/dev/null 2>&1; then
  exec python -m uvicorn "${APP}" --host "${HOST}" --port "${PORT}" "$@"
fi

echo "Neither 'uv' nor 'python' was found in PATH." >&2
exit 127
