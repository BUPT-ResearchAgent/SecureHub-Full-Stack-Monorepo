# Status: real

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$Backend = Join-Path $Root "backend"
Set-Location $Backend

$count = 'import psycopg2; from app.core.config import get_settings; u=get_settings().DATABASE_URL.replace("postgresql+asyncpg://","postgresql://"); c=psycopg2.connect(u); cur=c.cursor(); cur.execute("SELECT count(*) FROM documents WHERE domain=%s AND metadata->>%s=%s AND metadata->>%s=%s", ("course_websec","collection_mode","scrapling","platform","github")); print(cur.fetchone()[0]); c.close()'
$before = uv run python -c $count
uv run python -m scripts.crawl.scrapling_public_import --platform github --dry-run
uv run python -m scripts.crawl.scrapling_public_import --platform github
$after = uv run python -c $count
Write-Host "GitHub documents delta: $([int]$after - [int]$before)"
