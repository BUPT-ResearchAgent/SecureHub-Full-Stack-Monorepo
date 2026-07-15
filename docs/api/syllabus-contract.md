# T3 Typed Syllabus API 契约

> Status: real implementation contract (FG-06, migration `20260715_1082`)

`course_syllabuses` 与 `course_syllabus_versions` 是 typed syllabus 的唯一版本层。它不是普通文档的别名，也不得自动覆盖既有 `courses` 或 ready 课程内容。所有教师路由都需要有效课程教师归属；学生只可读取已发布版本。

## 版本生命周期

| Route | 作用 | 状态/证据规则 |
| --- | --- | --- |
| `POST /api/v1/teacher/production/courses/{course_id}/syllabus/versions` | 人工创建或编辑 typed 版本 | 内容须符合 `TypedSyllabusContent`（目标、模块、知识点、活动、评估、资源）；知识点必须属于该课程。 |
| `POST /api/v1/teacher/production/courses/{course_id}/syllabus/generate` | 由既有生成结果建立 typed 版本 | 只接收成功 Runtime AgentRun 和其 Evidence Snapshot；缺证据返回 `SYLLABUS_EVIDENCE_INSUFFICIENT`。该路由不直接调用 Provider。 |
| `POST /api/v1/teacher/production/syllabus/versions/{version_id}/review` | 审核、发布、驳回或撤回 | 发布才可成为课程当前可见版本；审核决定和理由持久化。 |
| `GET /api/v1/teacher/production/syllabus/versions/{version_id}/compare?from_version_id=` | 比较 typed 字段/模块差异 | 比较对象必须属于同一课程 syllabus。 |
| `GET /api/v1/teacher/production/syllabus/versions/{version_id}/preview` | 预览任意授权版本 | 不改变状态。 |
| `POST /api/v1/teacher/production/syllabus/versions/{version_id}/export` | 导出已发布版本为 `json` 或 `markdown` | 创建 `syllabus_exports` 和既有 `generated_resources` 记录，不写回课程内容。 |
| `POST /api/v1/teacher/production/syllabus/versions/{version_id}/rollback` | 显式回滚到 published/superseded 历史版本 | 当前发布版本转为 `superseded`，目标转 `published`，理由必填。 |
| `GET /api/v1/teaching/courses/{course_id}/syllabus` | 学生读取 | 仅返回当前 `published` 版本。 |

## 稳定失败码与审计

- `COURSE_ACCESS_DENIED`：无有效教师归属、跨课程版本或学生无权访问。
- `SYLLABUS_EVIDENCE_INSUFFICIENT`：生成输入未关联已完成 AgentRun/Evidence Snapshot。
- `SYLLABUS_REVIEW_REQUIRED`：未发布版本导出或学生访问。
- `SYLLABUS_VERSION_CONFLICT`：无效状态转换或跨 syllabus 比较/回滚。

版本创建、审核、发布、导出和回滚均把操作者、对象、理由、结果写入 `governance_audit_events`。生成接受的上游 AgentRun 是既有 Runtime 的记录；本模块不会重写、伪造或绕开 Runtime 的执行与证据链。
