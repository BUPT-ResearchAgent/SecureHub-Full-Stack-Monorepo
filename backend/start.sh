#!/bin/bash
export HTTP_PROXY=""
export HTTPS_PROXY=""
export http_proxy=""
export https_proxy=""
export ALL_PROXY=""
export all_proxy=""
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy
exec uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 "$@"