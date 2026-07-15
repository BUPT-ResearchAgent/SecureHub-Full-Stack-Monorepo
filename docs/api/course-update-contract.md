# T4 课程更新建议契约

`/api/v1/course-updates` 只接收三种固定 Skill 的已成功 `AgentRun`：

- `policy_interpreter / InterpretPolicy`；
- `hot_analyst / AnalyzeHotEvent`；
- `job_analyst / AnalyzeJobMarket`。

`POST /signals` 校验 Agent ID、Skill ID、成功状态、Evidence Snapshot 关联和来源文档一致性后，才持久化 `external_signals`。该端点不调用 Provider，也不伪造 AgentRun。

`POST /suggestions` 需要当前课程教师归属、已验证信号和属于该课程的知识节点。建议保留 diff、影响点、AgentRun 与 Evidence 引用，状态为 `pending_teacher_decision`。

`POST /suggestions/{id}/decision` 只允许当前课程教师 `adopt` 或 `reject` 一次，持久化决定、理由和业务审计。`adopted` 仅表示采纳建议，绝不写入 `courses` 或自动发布课程内容。

主要失败码：`TEACHER_ROLE_REQUIRED`、`COURSE_ACCESS_DENIED`、`SIGNAL_SOURCE_UNTRUSTED`、`SIGNAL_EVIDENCE_MISSING`、`SUGGESTION_ALREADY_DECIDED`。
