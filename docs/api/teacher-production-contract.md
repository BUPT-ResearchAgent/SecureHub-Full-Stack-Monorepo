# T3 教师教学生产 API 契约

> Status: real implementation contract (T3, migration `20260715_1082`)

本契约覆盖 F1、FG-02、FG-05；所有时间为 UTC ISO 8601，所有 UUID 是既有资源的稳定 ID。所有教师路由均须由服务端同时验证教师角色和有效的 `course_teacher_assignments`，客户端传入的课程、班级或学生 ID 不能构成授权。

## 资产治理与工作台（FG-02）

| Route | 作用 | 持久化与限制 |
| --- | --- | --- |
| `GET /api/v1/teacher/production/dashboard` | 返回本人课程、在读学生、已治理资产、待审题、有效布置、待处理成绩及其查询口径 | 数字只来自 T1/T3 持久查询；不允许静态 KPI。 |
| `GET /api/v1/teacher/production/courses` | 列出本人可治理课程和班级/选课计数 | 只列有效教师归属。 |
| `GET/POST /api/v1/teacher/production/courses/{course_id}/assets` | 读取或绑定统一知识资产 | 仅绑定既有 `documents` 与匹配的 `document_assets`，写入 `course_document_bindings`、`course_asset_governance`。 |
| `POST /api/v1/teacher/production/assets/{asset_id}/{correct,withdraw,delete,restore}` | 更正、撤回、软删除或恢复 | 每项须有理由；资产状态由真实文档处理状态协调，并写业务审计。 |

`COURSE_ACCESS_DENIED`、`DOCUMENT_ACCESS_DENIED`、`ASSET_STATE_CONFLICT` 是确定性失败码。撤回和软删除可通过 `restore` 回滚；不会删除统一知识资产本体。

## 审题、薄弱点与教学建议（F1）

| Route | 作用 | 关键约束 |
| --- | --- | --- |
| `POST /api/v1/teacher/production/courses/{course_id}/quiz-items/{quiz_item_id}/review` | 发布、驳回或撤回教师审题决定 | 发布仅接受 T2 `websec-quiz-quality-v1` 的 `passed` 结果；教师决定记录在 `quiz_review_decisions`，不把 Codex 规则校验伪装为人工审核。 |
| `POST /api/v1/teacher/production/courses/{course_id}/weakness-snapshots` | 聚合请求中指定教学班的真实选课、答题、进度/能力上下文 | 保存输入指纹、聚合时间和知识点结果；跨班/跨课确定性拒绝。 |
| `POST /api/v1/teacher/production/courses/{course_id}/teaching-recommendations` | 新建 evidence-backed 或明确 curated 的教学建议 | 请求绑定一个已保存的 weakness snapshot；若引用生成建议，必须提供成功 AgentRun 和 Evidence Snapshot；建议只可由教师采纳/驳回，不会自动改写课程。 |
| `POST /api/v1/teacher/production/teaching-recommendations/{recommendation_id}/decision` | 记录采纳/驳回 | 必须带理由，写处置审计。 |

生成证据缺失时返回 `RECOMMENDATION_EVIDENCE_INSUFFICIENT`，不是降级成伪成功。

## 作业/考试、评分与成绩发布（FG-05）

| Route | 作用 | 关键约束 |
| --- | --- | --- |
| `POST /api/v1/teacher/production/courses/{course_id}/assessments` | 创建作业/试卷根对象 | 课程范围由教师归属决定。 |
| `POST /api/v1/teacher/production/assessments/{assessment_id}/versions` | 冻结版本及题目快照 | 只允许 T2 质量门通过的题目；已布置版本不可被原地篡改。 |
| `POST /api/v1/teacher/production/assessment-versions/{version_id}/assignments` | 向班级、分组或学生布置 | 保存范围、截止时间和状态；跨课程范围拒绝。 |
| `POST /api/v1/teaching/assessment-assignments/{assignment_id}/submit` | 学生提交答案 | 学生必须在布置范围内；过期或重复状态按稳定码拒绝。 |
| `POST /api/v1/teacher/production/assessment-submissions/{submission_id}/score-objective` | 确定性客观题评分 | 不调用 Provider。 |
| `POST /api/v1/teacher/production/assessment-submissions/{submission_id}/subjective-suggestion` | 记录主观题 AI 建议 | 仅接受既有成功 AgentRun 与 Evidence Snapshot；建议不能直接成为成绩。 |
| `POST /api/v1/teacher/production/assessment-submissions/{submission_id}/override` | 教师人工覆盖 | 人工理由必填，保留覆盖前后值。 |
| `POST /api/v1/teacher/production/assessment-submissions/{submission_id}/{publish,withdraw}` | 发布或撤回单个成绩 | 仅已教师确认的结果可发布；撤回后学生不可见。 |
| `GET /api/v1/teaching/assignments/{assignment_id}/result` | 学生读取成绩 | 只返回其本人且已发布的结果。 |

主要失败码：`ASSESSMENT_SCOPE_DENIED`、`ASSESSMENT_VERSION_LOCKED`、`GRADE_NOT_REVIEWABLE`、`GRADE_PUBLISH_FORBIDDEN`、`INSUFFICIENT_EVIDENCE`、`GRADE_NOT_PUBLISHED`。所有创建、评分、覆盖、发布和撤回动作都写入 T1 的 `governance_audit_events`，该表不替代 Runtime 审计。

## 回滚边界

- 资产：保留生命周期行和理由，通过 `restore` 反转撤回/软删除。
- 题目/建议：保留决定记录；建议采纳不会直接回写已发布课程。
- 测评：版本不可原地改写；通过撤回成绩停止学生可见性，人工覆盖保留理由。
- 本模块不触及 RuntimeEngine、Workflow 定义、SSE、`workflow_runs` 或 `agent_runs` 的写入权威。
