# SecureHub Env and Credentials

所有凭证只进入本机 `.env` 或团队密码库，禁止提交到 git。

| Key | 用途 | 谁负责申请 | 是否共享额度 | 本地 dev 是否可走 mock_mode | 是否进 git 仓库 |
| --- | --- | --- | --- | --- | --- |
| XFYUN_APPID | 讯飞星火应用标识 | member-a | Yes | Yes | No |
| XFYUN_API_KEY | 讯飞星火文本生成 API Key | member-a | Yes | Yes | No |
| XFYUN_API_SECRET | 讯飞星火文本生成 API Secret | member-a | Yes | Yes | No |
| XFYUN_SPARK_DOMAIN | 讯飞星火模型域名 | member-a | Yes | Yes | No |
| XFYUN_TTS_APP_ID | 讯飞 TTS 应用标识 | member-a | Yes | Yes | No |
| XFYUN_TTS_API_KEY | 讯飞 TTS API Key | member-a | Yes | Yes | No |
| XFYUN_TTS_API_SECRET | 讯飞 TTS API Secret | member-a | Yes | Yes | No |
| DEEPSEEK_API_KEY | DeepSeek fallback | member-a | Yes | Yes | No |
| QWEN_API_KEY | Qwen fallback | member-a | Yes | Yes | No |
| LLM_PRIMARY | 主 LLM provider 选择 | member-a | No | Yes | No |
| LLM_FALLBACK_CHAIN | fallback provider 顺序 | member-a | No | Yes | No |
| EMBEDDING_PROVIDER | embedding provider 选择 | member-c | No | Yes | No |
| EMBEDDING_MODEL | embedding 模型名 | member-c | No | Yes | No |
| EMBEDDING_DIM | embedding 向量维度 | member-c | No | Yes | No |
| DATABASE_URL | PostgreSQL / pgvector 连接串 | member-c | No | Yes | No |
| REDIS_URL | Redis 连接串 | member-c | No | Yes | No |
| STORAGE_PROVIDER | 生成物对象存储 provider | member-a | No | Yes | No |
| STORAGE_LOCAL_ROOT | 本地对象存储目录 | member-a | No | Yes | No |
| MINIO_ENDPOINT | MinIO endpoint | member-c | Yes | Yes | No |
| MINIO_ACCESS_KEY | MinIO access key | member-c | Yes | Yes | No |
| MINIO_SECRET_KEY | MinIO secret key | member-c | Yes | Yes | No |
| MINIO_BUCKET | MinIO bucket 名 | member-c | Yes | Yes | No |
| MINERU_MODE | MinerU 转换模式 | member-c | No | Yes | No |
| MINERU_API_BASE | MinerU API base | member-c | Yes | Yes | No |
| MINERU_API_KEY | MinerU API Key | member-c | Yes | Yes | No |
| MINERU_LOCAL_BIN | 本地 MinerU 可执行文件路径 | member-c | No | Yes | No |
| HARNESS_MIN_EVIDENCE | Harness 最小证据数 | member-a | No | Yes | No |
| HARNESS_TIMEOUT_SECONDS | Harness 默认超时 | member-a | No | Yes | No |
| HARNESS_DEFAULT_RETRY_MAX | Harness 默认重试次数 | member-a | No | Yes | No |
| HARNESS_MOCK_MODE | Harness 是否使用 fixtures | member-a | No | Yes | No |
| CRAWL_RESPECT_ROBOTS | 离线采集是否遵守 robots | member-c | No | Yes | No |
| CRAWL_DEFAULT_DELAY_SECONDS | 离线采集默认延迟 | member-c | No | Yes | No |
| CRAWL_MAX_CONCURRENCY | 离线采集最大并发 | member-c | No | Yes | No |
| CRAWL_USER_AGENT | 离线采集 user agent | member-c | No | Yes | No |
| APP_NAME | 应用名 | member-a | No | Yes | No |
| API_V1_PREFIX | API v1 前缀 | member-a | No | Yes | No |
| FRONTEND_ORIGINS | CORS 前端来源 | member-b | No | Yes | No |
| DEBUG | 调试模式 | member-a | No | Yes | No |
| VITE_API_BASE_URL | 前端请求后端 API base | member-b | No | Yes | No |

## 如何在三人之间安全共享凭证

使用 1Password 或 Bitwarden 团队保险库，条目统一用 `SecureHub/` 前缀命名，例如 `SecureHub/XFYUN Spark`、`SecureHub/MinIO Dev`。只共享最小必要权限；成员离队或 key 疑似泄漏时立即轮换，仓库历史中不得出现真实凭证。
