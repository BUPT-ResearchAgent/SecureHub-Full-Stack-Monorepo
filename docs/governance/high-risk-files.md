# High-Risk Files Review Rules

以下文件或目录改动必须在 PR 中显式说明原因、风险和验收命令。

| 路径 | 签收规则 |
| --- | --- |
| `backend/app/db/models/` | 必经 `@member-a` + `@member-c` 双签 |
| `backend/app/db/migrations/` | 单 PR 单迁移 + 双签 + 命名 `YYYYMMDD_HHMM_<verb>_<noun>.py` |
| `frontend/src/lib/api.ts` | 必经 `@member-a` + `@member-b` |
| `frontend/src/lib/sse.ts` | 必经 `@member-a` + `@member-b`；SSE event 字段不可静默改 |
| `CLAUDE.md` / `.codex/AGENTS.md` | 必经 `@member-a` + `@member-c` + 项目负责人 |
| `docs/api/course-contract.md` | 必经全员评审 |
| `docker-compose.yml` / `pyproject.toml` / `frontend/package.json` | 依赖变动必须说明用途 |
