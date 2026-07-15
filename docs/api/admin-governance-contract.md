# T4 管理员治理契约

`/api/v1/admin/*` 的所有请求都要求 active `user_role_grants -> role_definitions(code=administrator)`；浏览器路由、产品身份字段或 URL 不能替代该服务端校验。

- 用户列表与角色授予：只引用既有 `users`，授予/撤销写业务审计；撤销最后一位管理员返回 `LAST_ADMIN_PROTECTED`。
- 课程资源治理：只在 `course_asset_governance` 上增加 `course_resource_governance` 覆盖层；限制/撤下同步使资产不可见，恢复不复写知识资产正文。
- 全局 KPI：`kpi_definitions` 保存版本化查询口径，数值实时查询 `teaching_classes`、`course_enrollments`、已发布成绩、更新建议和消息投递，响应包含定义版本、来源关系和时间窗。

主要失败码：`ADMIN_ROLE_REQUIRED`、`ROLE_GRANT_FORBIDDEN`、`LAST_ADMIN_PROTECTED`、`RESOURCE_GOVERNANCE_DENIED`、`KPI_DEFINITION_UNKNOWN`。
