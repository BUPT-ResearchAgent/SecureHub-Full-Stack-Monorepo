# SecureHub Data-Layer v2 枚举 SSOT

> data-layer v2 里所有"字符串枚举字段"的 Single Source of Truth。
>
> 上游：`.codex/AGENTS.md §9` + `CompetitionTheme/A3赛题规划.md §5.2` + `Chat/SecureHub_Data_Layer_V2_工程化改造任务书.md`。
>
> 落地：`backend/app/db/models/_enums.py`（待 D15 实现） + `backend/app/schemas/*.py` Literal 类型 + `frontend/src/lib/sse.types.ts` 联合类型。三处必须 1:1。

---

## 0. 为什么需要这个文件

字符串枚举字段散落在 schema / models / docs / 前端各处，C 写 seed 时用 `markdown_chapter`、A 写代码时用 `markdown_section`、B 前端用 `chapter_md` —— 100% 会错位。本文件是唯一可引用源，**改值必须同时改本文件 + 后端 enums + 前端 sse.types.ts + 文档**。

---

## 1. `documents` 表枚举

### 1.1 `documents.domain` —— 知识库领域

```
course_websec       Web 安全课程
policy              政策法规
fund                科研基金
job                 招聘岗位
competition         专业竞赛
paper               学术论文
news                安全事件 / CVE / CNVD
```

**约束**：新增 domain 需 A + C 双签；不允许临时字符串如 `course_crypto_v2`。

### 1.2 `documents.source_type` —— 原始来源类型

```
manual              手工整理
pdf                 PDF 教材 / 书籍
book                纸质书
paper               学术论文
lecture_note        课堂讲义
report              行业报告
api                 官方 API（CTFtime / CVE / RSS）
rss                 RSS 订阅
official_doc        官方文档（OWASP / PortSwigger）
blog                技术博客
github_docs         GitHub README / Docs
media_post          中文社媒帖子（B站视频元数据 / 知乎答案 / 小红书笔记）
video_transcript    视频字幕 / 转写
hot_topic           舆情热点（MindSpider 参考）
```

### 1.3 `documents.status` —— 入库生命周期

```
pending             入库中（raw_text 未抓全 / asset 未齐）
ready               入库完成，chunks 已切
failed              入库失败（带 error_message in metadata）
archived            归档不再使用（演示删除项）
```

---

## 2. `document_assets` 表枚举

### 2.1 `document_assets.asset_type`

```
# PDF / 文档类
original_pdf
original_docx
markdown_full
markdown_chapter
page_text
page_image
cover_image
ocr_text
table_image
formula_image
raw_json

# 视频 / 媒体类
video_transcript
audio_transcript
screenshot

# 社媒类（MediaCrawler 适配）
media_item_json
media_comment_json
```

**约束**：新增类型必须由 C 在 `pdf_ingestion_service.py` 或 `media_source_normalizer.py` 中真实落库后，再补到本表。

---

## 3. `chunks` 表枚举

### 3.1 `chunks.embedding_status`

```
pending             未向量化
ready               已向量化（embedding 列非空）
failed              向量化失败（重试上限耗尽）
```

### 3.2 `chunks.metadata.source_type`（chunk 维度的来源标记）

继承 `documents.source_type`，但 PDF 流水线额外允许：

```
pdf_mineru          经 MinerU 处理后的 PDF 切片
pdf_manual          人工切片
```

---

## 4. `knowledge_nodes` / `knowledge_edges` 表枚举

### 4.1 `knowledge_nodes.node_type`

```
concept             概念（SQL 注入 / OAuth 流程）
skill               技能（信息收集 / 漏洞利用）
tool                工具（sqlmap / Burp Suite）
topic               主题（应急响应 / 红蓝对抗）
standard            标准 / 规范（OWASP Top 10 / NIST CSF）
```

### 4.2 `knowledge_edges.edge_type`

```
prerequisite        前置（A 是 B 的先修）
related_to          相关（无方向偏好）
requires            需要（A 操作需要 B 工具）
supports            支撑（A 支撑 B 的实施）
extends             延伸（A 是 B 的进阶 / 变种）
```

**约束**：`knowledge_edges` PK 是 `(source_id, target_id, edge_type)` 三元组；同一对节点可有多种关系。

---

## 5. `quiz_items` 表枚举

### 5.1 `quiz_items.type`

```
single_choice       单选题
multi_choice        多选题
fill                填空题
short_answer        简答题
code                代码题（输入代码片段 / 修复 bug）
true_false          判断题
```

---

## 6. `learning_events` 表枚举

### 6.1 `learning_events.event_type`

```
# 资源消费
view_doc            查看课程文档
view_ppt            查看 PPT
view_mindmap        查看思维导图
watch_video         观看视频
read_lab            阅读实操案例

# 测验
quiz_correct        答对题目
quiz_wrong          答错题目
quiz_skipped        跳过题目

# 学习进度
start_node          开始知识点
complete_node       完成知识点
revisit_node        重学知识点

# 辅导
ask_tutor           向辅导提问
get_tutor_answer    收到辅导回复

# 评估
assessment_done     完成阶段测评
```

---

## 7. `agents` / `agent_skills` / `agent_runs` 表枚举

### 7.1 `agents.name`（9 个固定值，不可增减）

```
policy_interpreter
hot_analyst
job_analyst
competition_advisor
career_planner
topic_explorer
doc_archivist
task_orchestrator
outcome_evaluator
```

### 7.2 `agents.risk_level`

```
low                 低风险（task_orchestrator / job_analyst / doc_archivist）
medium              中风险（policy_interpreter / competition_advisor / topic_explorer）
high                高风险（hot_analyst / career_planner / outcome_evaluator）
```

### 7.3 `agent_runs.workflow_name`

```
course_learning         A3 主战场：课程学习多智能体协同
tutor_routing           P1：智能辅导路由
fund_recommendation     P2：基金推荐
profile_building        画像构建独立调用
assessment              学习评估
```

### 7.4 `agent_runs.status`

```
success                 完成且 quality_check 通过
failed                  执行异常 / LLM 全链路失败
blocked                 guardrail 阻断 / 内容拒答 / 证据不足
timeout                 超过 HARNESS_TIMEOUT_SECONDS
```

---

## 8. `generated_resources` 表枚举

### 8.1 `generated_resources.resource_type`

```
course_doc          课程讲解文档
course_ppt          PPT 大纲 / reveal.js
mindmap             思维导图（markmap / mermaid）
quiz_set            题目集合（含多个 quiz_items）
hands_on_lab        实操案例
video_storyboard    视频脚本 / 分镜
reading_list        拓展阅读清单
assessment_report   评估报告
proposal            研究计划书（中枢延展）
```

**前端 SSE `artifact` 事件 / API `ResourceGenerateRequest.type` 与本枚举 1:1**。

### 8.2 `generated_resources.status`

```
generating          生成中（SSE 流式输出阶段）
ready               生成完成，可下载 / 展示
failed              生成失败（quality_check 不通过 / LLM 失败）
archived            归档
```

---

## 9. `storage_objects` 表枚举

### 9.1 `storage_objects.provider`

```
local               本地文件系统（P0 默认）
minio               MinIO（自建对象存储）
s3                  AWS S3
oss                 阿里云 OSS
cos                 腾讯云 COS
r2                  Cloudflare R2
```

### 9.2 `storage_objects.status`

```
ready               文件已写入，可读
pending             写入中
failed              写入失败
deleted             逻辑删除（物理文件可能仍在）
```

---

## 10. SSE 事件枚举（前后端共享）

```
progress            阶段切换
evidence            RAG 命中证据
token               LLM 流式 token
artifact            generated_resources / storage_objects 已落库
trace               agent_runs / skill 状态变化
done                工作流结束
error               异常
```

**与 `frontend/src/lib/sse.types.ts` 的 `SSEEvent` union 字面量值 1:1**。

---

## 11. 采集模式枚举

```
manual_import           人工整理 Markdown / PDF / HTML（P0）
api_rss_import          官方 API / RSS / GitHub raw（P0）
scrapling_public        Scrapling 公开网页（P1）
mediacrawler_export     MediaCrawler 离线导出（P1）
mindspider_reference    MindSpider 舆情流程参考（P2）
mindspider_adapter_test MindSpider test-mode 小规模映射（P2）
```

写入 `documents.metadata.collect_mode` 字段。

---

## 12. 落地清单

| 文件 | 状态 | 责任人 |
|---|---|---|
| `backend/app/db/models/_enums.py` —— Python `StrEnum` 集合 | 待 D15 创建 | 成员 A |
| `backend/app/schemas/*.py` Literal 类型 | B7 创建后引用 _enums | 成员 A |
| `frontend/src/lib/sse.types.ts` 联合字面量 | B8 创建后引用 | 成员 B |
| `backend/app/db/migrations/` 已有迁移 | 检查 String 字段长度 ≥ 最长枚举值 | 成员 A + C |
| `docs/api/course-contract.md` | A1 创建后引用本文件 | 成员 A |

---

*Last updated: 2026-06-09。修改任一枚举值必须：1）改本文件；2）改 `_enums.py`；3）改 schemas/SSE types；4）跑 `pytest backend/tests/db/test_enum_consistency.py`（如未实现则补一个）。否则前后端一定错位。*
