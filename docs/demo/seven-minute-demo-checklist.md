# 7 分钟演示素材与测试 Checklist

Status: real

## 分镜

| 时间 | 镜头 | 需要确认 |
|---:|---|---|
| 0:00-0:30 | 项目定位 + A3 主线 | 明确 9 个 agent 固定，不新增采集 agent |
| 0:30-1:20 | Demo user 画像 | `seed_demo_user` 有 6+ 画像维度和能力雷达数据 |
| 1:20-2:10 | SQL 注入学习路径 | `knowledge_nodes / knowledge_edges` 有 SQL 注入、XSS、CSRF、文件上传 |
| 2:10-4:20 | 5+ 资源生成 | 课程文档、PPT、思维导图、练习题、实操、视频脚本走 RAG evidence |
| 4:20-5:10 | 智能辅导 | 无证据时显示 InsufficientEvidence，不裸调 LLM |
| 5:10-5:50 | 测验与能力回流 | `user_capabilities` 可更新并保持幂等 |
| 5:50-6:30 | 多源采集证据 | Evidence 展示 platform、source_url、author、rights_note |
| 6:30-7:00 | 架构总结 | 统一进入 documents / document_assets / chunks / storage_objects |

## P0 测试命令

```powershell
cd F:\software_cup\SecureHub-Full-Stack-Monorepo
.\scripts\demo_smoke.ps1
```

## 演示素材清单

| 素材 | 路径 / 表 | 状态 |
|---|---|---|
| Web 安全资料清单 | `docs/demo/websec_source_inventory.md` | ready |
| SQL 注入 / XSS / CSRF / 文件上传知识点 | `backend/app/db/seeds/seed_course_websec.py` | ready |
| PDF/MinerU 入库脚本 | `scripts/ingest_pdf_mineru.py` | ready |
| RAG smoke test | `backend/tests/rag/test_retrieve_course_websec.py` | ready |
| 无证据回归测试 | `backend/tests/hallucination/test_no_evidence_queries.py` | ready |
| generated_resources 测试 | `backend/tests/resource/test_generated_resources.py` | ready |
| user_capabilities 测试 | `backend/tests/identity/test_user_capabilities.py` | ready |

## 铁律自检

- 未新增 crawler agent / media agent / mineru agent。
- 未新增 `bilibili_chunks`、`zhihu_chunks`、`course_chunks` 等平台或 domain 专用表。
- 采集资料进入 `documents / document_assets / chunks`。
- 文件资产通过 `storage_objects.object_key` 管理。
- 来源字段保留 `platform / source_url / author / published_at / fetched_at / rights_note`。
- 无证据测试确认不会进入生成步骤。
- MediaCrawler / MindSpider 仅作为 P1/P2 受控适配与参考说明。
