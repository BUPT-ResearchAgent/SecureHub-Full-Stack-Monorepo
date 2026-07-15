# T4 站内消息契约

人际消息使用 `messages` 与逐收件人 `message_deliveries`，绝不使用 Runtime `agent_messages`。

`POST /api/v1/messages` 支持：

- `course`：授权教师向本人课程的有效选课学生投递；
- `class`：授权教师向本人教学班的有效选课学生投递；
- `individual`：教师向本人课程学生，或有效选课学生向该课程授权教师投递。

发送以 `sender_user_id + idempotency_key` 去重；不同内容重用请求键返回 `MESSAGE_IDEMPOTENCY_CONFLICT`。服务端确定性内容安全规则拒绝脚本/HTML 注入标记，拒绝记录和审计仍持久化。

`GET /inbox` 返回当前账号投递状态；`POST /{id}/read` 只允许收件人标记已读；`POST /{id}/recall` 只允许发送人于 30 分钟内撤回，投递状态同步为 `recalled`。发送、投递、已读、撤回和拒绝均写 `governance_audit_events`。

主要失败码：`MESSAGE_SCOPE_DENIED`、`RECIPIENT_NOT_FOUND`、`MESSAGE_CONTENT_UNSAFE`、`MESSAGE_IDEMPOTENCY_CONFLICT`、`RECALL_WINDOW_EXPIRED`。
