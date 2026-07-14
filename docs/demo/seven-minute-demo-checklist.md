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

演示时还应展示：资源 fan-out 的 typed Evidence/Artifact lineage、QualityCheck
返工上限、暂停/恢复控件、SSE reconnect/replay 以及“讯飞星火主链”状态。未持有
双 Provider 与 RAG 凭据时，使用显式 fixture 演示并口头说明真实 fallback gate
为 pending；不得把 fixture 文本描述为 Spark 或 DeepSeek 的真实输出。

## C 负责状态

| Gate | 状态 | 说明 |
|---|---|---|
| WebSec seed | ready | `seed_course_websec.py` 幂等，覆盖 17 nodes、68 chunks、5 SQL 注入题目 |
| Evidence metadata | ready | seed / loader fixture 保留 `platform/source_url/author/rights_note/collection_mode/asset_type` |
| PDF / MinerU evidence | ready | SSRF seed fixture 使用 `platform=mineru`、`asset_type=pdf`、`page_no=12`；loader 测试覆盖 PDF + Markdown + page image |
| RAG smoke | ready | 覆盖 SQL 注入、XSS、文件上传、CSRF、SSRF、访问控制、命令执行、反序列化、安全编码 |
| no-evidence gate | ready | 空 domain、证据不足、metadata 缺 `source_url/rights_note` 均不进入 LLM / done |
| GitHub Docs fixture | ready | offline fixture 写入 `documents + document_assets + chunks + storage_objects`，`platform=github` 可召回 |
| Scrapling / 官方资料 fixture | ready | OWASP / PortSwigger 使用离线最小样例，不依赖外网跑 CI |
| MediaCrawler fixture | ready | B 站 export fixture → normalizer → unified tables → retrieval |
| demo_smoke | partial | 脚本覆盖 health、llm/health、courses、rag/search、course plan、resources/generate、agent_runs；若 A/B endpoint 未 ready，按依赖方标记失败 |
| live LLM gate | gated | 默认 skip；真实 DeepSeek/讯飞调用待项目负责人允许 API 消耗并提供 key 后验证 |

## P0 测试命令

```powershell
cd D:\Nnutural\Desktop\BUPT大全\BUPT竞赛\26软件杯\SecureHub-Full-Stack-Monorepo
.\scripts\demo_smoke.ps1
```

## 演示素材清单

| 素材 | 路径 / 表 | 状态 |
|---|---|---|
| Web 安全资料清单 | `docs/demo/websec_source_inventory.md` | ready |
| SQL 注入 / XSS / CSRF / 文件上传 / SSRF / 访问控制知识点 | `backend/app/db/seeds/seed_course_websec.py` | ready |
| PDF/MinerU 入库脚本 | `scripts/ingest_pdf_mineru.py` | ready |
| RAG smoke test | `backend/tests/rag/test_retrieve_course_websec.py` | ready |
| 无证据回归测试 | `backend/tests/hallucination/test_no_evidence_queries.py` | ready |
| live LLM 手动门禁 | `backend/tests/llm_live/test_p0_real_llm.py` / `docs/demo/llm_live_acceptance.md` | gated |
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
- live LLM 测试不进入普通 CI；无真实 key 时只报告门禁完成，不伪造真实调用通过。
