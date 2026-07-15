# WEBSEC-101 题库质量契约

状态：`real`（T2，2026-07-15）

## 边界

- 只服务唯一 ready 课程 `WEBSEC-101` / `course_websec`；preview 课程、未知课程和 `applicable_domains` 均不在此契约范围。
- 题目实体仍是 `quiz_items`，知识点仍是 `knowledge_nodes`，Evidence 只经 `quiz_item_evidences -> chunks` 引用；不复制课程、用户、画像或知识正文。
- `curated` 表示课程内容的可发布来源状态，不表示人工审核。自动质量校验的 `reviewed_by` 保持空值；状态枚举没有人工批准值。

## 持久化状态与可发布条件

`quiz_items` 具有稳定唯一 `canonical_key`、`content_version`、题型、难度、答案、解析、`review_status` 和 `source_status`。允许的审核状态为：

`draft` / `pre-generated` / `curated` / `codex-reviewed-pending-human` / `rejected` / `withdrawn`。

`quiz_quality_reports` 以 `(quiz_item_id, validator_version, input_fingerprint)` 唯一保存可重复结果。学生课程读取条件必须同时满足：

1. `review_status == curated`；
2. 最新的 `websec-quiz-quality-v1` 报告为 `passed`；
3. 题目属于 `WEBSEC-101` 的既有知识点。

否则单题读取返回 `409 QUESTION_STATUS_NOT_PUBLISHABLE`，不会以空成功或前端 fallback 替代。

## 确定性校验

规则版本 `websec-quiz-quality-v1` 对冻结的数据库输入计算 SHA-256 指纹。检查项包括：

- 完全重复和近重复（归一化题干相似度阈值 `0.92`）；
- 空 Evidence、Evidence 不存在或与知识点不匹配；
- 单选/多选答案和选项矛盾、重复/不足选项；
- 缺失的 17 个知识点；
- 题型种类少于 3 类或单一题型超过 80%。

校验将规则、覆盖计数、题型分布、Evidence IDs 与失败码持久化。相同冻结输入不会创建第二条 report；相同输入须产生相同 result 和 fingerprint。

## 教师端 API

### `GET /api/v1/teacher/quiz-bank/websec`

需要 `users.role ∈ {course_teacher, hybrid}` 且存在有效 `course_teacher_assignments` 的 `WEBSEC-101` 归属。

返回每道题、知识点、Evidence、来源/审核状态、最近质量状态和 17 点覆盖计数。

- `403 TEACHER_ROLE_REQUIRED`：不是课程教师身份。
- `403 COURSE_SCOPE_DENIED`：没有 `WEBSEC-101` 课程归属。

### `POST /api/v1/teacher/quiz-bank/websec/validate`

使用同一课程教师授权执行并持久化确定性质量报告，同时向 `governance_audit_events` 写入操作者、规则版本、输入指纹和结果。它是**规则校验**，不是人工批准动作。

## 课程/评估消费 API

### `GET /api/v1/courses/{course_id}/quiz-items`

要求登录，并仅对 ready 课程返回已发布质量合格题目。可用 `?canonical_key=<stable-key>` 请求单题；不合格题目确定性拒绝。

- `403 COURSE_SCOPE_DENIED`：不是 `WEBSEC-101`。
- `409 COURSE_CONTENT_NOT_READY`：目标课程是 preview。
- `404 QUESTION_NOT_FOUND`：该稳定键不存在。
- `409 QUESTION_STATUS_NOT_PUBLISHABLE`：题目未精选、未通过或校验失败。

前端 `TeacherQuizBank.tsx`、`QuizResourceView.tsx` 和实时 `AssessmentPanel.tsx` 分别从上述 API 读取；正常模式不读取 `MOCK_QUIZ_ITEMS` 或固定练习题常量。

## 迁移与回滚

- 上行：`uv run alembic upgrade 20260715_1081`。
- 下行：`uv run alembic downgrade 20260715_1080`。

下行仅移除本阶段的题目质量列、Evidence 关联和报告表；不删除既有 `quiz_items`、历史作答、课程、知识节点、切片或 Runtime 审计。
