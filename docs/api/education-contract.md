# Education Relationship API Contract（T1 · real）

状态：`real`。本契约只覆盖 FG-03 的教学班、课程选课、教师归属与分组；它不替代 Runtime、`agent_runs`、`workflow_audit_logs` 或任何知识资产表。

## 权威数据与授权

- 用户与基础教师身份：既有 `users`，其中 `role ∈ {course_teacher, hybrid}` 才可进入课程教学关系服务。
- 课程：既有 `courses`；本轮种子只使用 `WEBSEC-101`，不扩展其他课程内容。
- 教师课程范围：`course_teacher_assignments` 的有效记录。
- 教师教学班范围：`teaching_class_teachers` 的有效记录；客户端传入的 `course_id` / `class_id` 不构成授权。
- 学生有效选课：`course_enrollments.status = enrolled`；复合外键保证所填教学班属于同一课程。
- 分组成员变更同时保留最新状态（`student_group_members`）和追加式业务审计（`governance_audit_events`）。

所有读取和写入都要求 `Authorization: Bearer <jwt>`。非课程教师、未归属课程教师、跨班和跨课请求都返回稳定的失败码，绝不返回伪造的空成功。

## 读取接口

### `GET /api/v1/teacher/education/classes`

可选查询参数：`course_id`（UUID）。服务端仅返回当前教师同时拥有课程和教学班有效归属的 `active` 教学班。

```json
{
  "items": [
    {
      "id": "uuid",
      "course_id": "uuid",
      "code": "WEBSEC-2026-A",
      "name": "Web 安全基础 · 2026 春 A 班",
      "status": "active",
      "student_count": 1
    }
  ]
}
```

### `GET /api/v1/teacher/education/classes/{class_id}/roster`

只返回该教学班内 `enrolled` 的学生；用户画像、能力和密码均不在该接口输出。

```json
{
  "teaching_class": { "id": "uuid", "course_id": "uuid", "code": "WEBSEC-2026-A", "name": "...", "status": "active", "student_count": 1 },
  "students": [
    { "id": "uuid", "display_name": "陈同学", "enrollment_status": "enrolled", "enrolled_at": "2026-07-15T00:00:00Z" }
  ]
}
```

### `GET /api/v1/teacher/education/classes/{class_id}/groups`

返回该班所有分组及其成员的最新状态、最近变更时间；已移除成员保留为审计可见状态，不作为有效成员计数。

## 写入接口

### `POST /api/v1/teacher/education/classes/{class_id}/groups`

必须发送 `Idempotency-Key`（1–128 字符）。请求：

```json
{ "name": "实验 B 组", "reason": "第 3 周实验分组" }
```

成功创建分组后追加一条 `student_group.create` 业务审计。相同 actor + 相同请求键 + 相同请求安全重放原结果；相同键用于不同请求返回 `IDEMPOTENCY_CONFLICT`。

### `POST /api/v1/teacher/education/classes/{class_id}/groups/{group_id}/members`

同样必须发送 `Idempotency-Key`。请求：

```json
{ "student_id": "uuid", "action": "add", "reason": "课堂协作安排" }
```

`add` 只接受当前班级的有效选课学生；`remove` 不删除历史行，而是写成员状态 `removed`。每次有效操作或幂等 no-op 都写入 `governance_audit_events`，记录 actor、对象、理由、结果、请求键和 UTC 时间。

## 稳定错误码

| Code | HTTP | 含义 |
| --- | --- | --- |
| `AUTH_REQUIRED` | 401 | 缺少登录凭据。 |
| `TEACHER_ROLE_REQUIRED` | 403 | 当前账号不是课程教学身份。 |
| `COURSE_ACCESS_DENIED` | 403 | 无有效课程或教学班归属，包含跨班/跨课访问。 |
| `CLASS_NOT_FOUND` | 404 | 教学班不存在。 |
| `GROUP_SCOPE_DENIED` | 403 | 分组不属于已授权教学班。 |
| `ENROLLMENT_REQUIRED` | 403 | 学生未在当前班有效选课，或不是可变更成员。 |
| `IDEMPOTENCY_CONFLICT` | 409 | 请求键被用于不同操作，或同名创建无法安全重放。 |

## Seed、迁移与回滚

- 迁移：`20260715_1080_education_domain`，上行只创建本契约的七张关系/审计表、索引和约束；下行按依赖逆序仅删除这些对象，不触碰 `users`、`courses`、画像、知识资产、学习事实或 Runtime 审计。
- 最小 seed：先运行既有 demo 用户和 Web 安全课程 seed，再运行 `uv run python -m app.db.seeds.seed_education_domain`。所有行使用稳定 UUID，重复运行不重复插入。
- 前端：`frontend/src/app/features/teacher/pages/TeacherStudents.tsx` 只调用本契约的真实读取接口；接口失败或无授权时展示错误/空态，不回退 `MOCK_CLASSES` 或 `MOCK_STUDENTS`。
