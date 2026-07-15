# T5 安全治理 API 契约

状态：`real`（20260715_1084）
范围：FG-07 弱口令策略/整改、FG-08 全站 API 风险审计/处置。
非范围：Runtime Provider limiter、Spark、LLM 调用、原始请求日志、密码恢复或用户密码哈希分析。

## 不可变安全边界

- `users.hashed_password` 仍是唯一密码哈希位置。`account_password_compliance` 仅保存策略版本、整改/豁免状态与期限，不能读取、扫描、反推或复制哈希。
- 请求风险层只保存路由模板、方法、结果码、可选用户 FK、HMAC 化 IP/设备标识、请求尺寸/速率桶、受限 correlation id、脱敏版本和保留截止时间。
- 禁止持久化 `Authorization`、`Cookie`、密码、token、原始 payload、完整 IP 或原始设备值。中间件仅短暂读取 bearer subject 以关联已有用户，绝不记录 credential。
- 仅 T4 的 active `user_role_grants -> role_definitions(code=administrator)` 可执行策略激活、管理员重置/解除、风险规则和风险事件处置。客户端 role、URL 或前端状态不构成权限。
- 全站风险中间件在 `/api/v1/*` 请求进入路由前执行；正常 allow 后补写实际响应状态，throttle/block 返回稳定拒绝而不会调用业务处理器。

## 状态机与回滚

| 资源 | 状态 | 关键约束 / 回滚 |
| --- | --- | --- |
| `password_policies` | `draft -> active -> retired` | 同一时刻仅一个 active；激活时保留旧版本，管理员获得最多 24 小时的显式 break-glass 豁免，不判读旧哈希。 |
| `account_password_compliance` | `compliant` / `remediation_required` / `remediated` / `temporarily_exempt` | 旧账号由记录的 `evaluated_policy_version` 判断；改密/重置只校验当次明文后写回唯一 hash；豁免到期后重新整改。 |
| `api_risk_rules` | `draft -> active -> retired` | 按 `user/ip/device/api` + 路由/方法谓词统计脱敏窗口；同 code 仅一个 active 版本。停用规则即停止新处置，但保留事件。 |
| `api_risk_events` | `observed` / `alerted` / `mitigated` / `released` / `false_positive` | 决定为 `allow` / `throttle` / `block` / `released`；人工 release/review 追加 action 和业务审计，不删除原始脱敏事件。 |

## 接口

所有错误均为 `{ "detail": { "code", "message" } }`。

| 方法 / 路径 | 权限 | 行为 |
| --- | --- | --- |
| `POST /api/v1/auth/register` | 匿名 | 用当前 active 版本实时校验请求明文；成功后创建 `compliant` 记录。 |
| `POST /api/v1/auth/login` | 匿名 | 仅根据已有合规记录版本判定旧策略；需要整改时持久化通知时间并返回 `PASSWORD_REMEDIATION_REQUIRED`，不签发 token。 |
| `POST /api/v1/auth/password/remediate` | 匿名（须验证当前密码） | 仅供 `PASSWORD_REMEDIATION_REQUIRED` 账号完成受限整改；校验当前密码与新策略后写唯一 hash、记录 `remediated` 与审计，不先签发 JWT。 |
| `POST /api/v1/auth/password/change` | 本人 | 验证当前密码、校验新策略、写唯一 hash、记录 `remediated` 与审计。 |
| `GET /api/v1/security/password-compliance/me` | 本人 | 返回 policy version、整改/通知/豁免期限和是否允许登录；不返回规则绕过信息或任何 hash。 |
| `POST /api/v1/security/password-policies` | 安全管理员 | 创建 draft 策略。 |
| `POST /api/v1/security/password-policies/{id}/activate` | 安全管理员 | 激活版本、退役前一版本并建立 bounded break-glass。 |
| `POST /api/v1/security/password-compliance/{user_id}/exemption` | 安全管理员 | 最多 24 小时的原因化解除；不得伪造 compliant。 |
| `POST /api/v1/security/password-compliance/{user_id}/reset` | 安全管理员 | 校验本次新密码并重置唯一 hash；请求明文不审计、不回显。 |
| `POST /api/v1/security/api-risk/rules` | 安全管理员 | 创建 draft 阈值规则。 |
| `POST /api/v1/security/api-risk/rules/{id}/activate` | 安全管理员 | 激活规则版本。 |
| `GET /api/v1/security/api-risk/events` | 安全管理员 | 返回可解释事件和 action 回放，不返回原始请求数据。 |
| `POST /api/v1/security/api-risk/events/{id}/release` | 安全管理员 | 追加人工解除并保留原 decision。 |
| `POST /api/v1/security/api-risk/events/{id}/review` | 安全管理员 | 记录 `false_positive`、`false_negative` 或 `confirmed` 的人工复核。 |

## 稳定失败码

- `PASSWORD_POLICY_VIOLATION`：新密码或策略规则不符合受控约束。
- `PASSWORD_REMEDIATION_REQUIRED`：账号记录版本落后于 active 策略，通知/整改状态已持久化。
- `PASSWORD_REMEDIATION_NOT_REQUIRED`：账号已经合规或处于有效 break-glass，不能使用匿名整改入口。
- `PASSWORD_CHANGE_FORBIDDEN`：当前密码校验失败或目标账号不可安全重置。
- `BREAK_GLASS_REQUIRED`：管理员解除目标不可用；策略切换保留时限恢复边界。
- `ADMIN_ROLE_REQUIRED`：非 active 治理管理员访问安全管理动作。
- `RISK_RULE_INVALID`：风险规则不存在、退役或无效。
- `API_RISK_RATE_LIMITED` / `API_RISK_EVENT_BLOCKED`：规则触发的 throttle / block。
- `RISK_RELEASE_FORBIDDEN`：风险事件不存在或不允许当前管理员处理。
- `REQUEST_AUDIT_REDACTION_FAILED`：安全审计元数据无法安全持久化，API 请求 fail-closed。

## 审计与验证口径

密码策略创建/激活、整改通知、本人改密、管理员重置/解除，以及风险规则激活、人工 release/review 均向 `governance_audit_events` 写入 actor、对象、理由、结果、UTC 时间和最小元数据。自动风险动作写入 `api_risk_actions(actor_user_id=null, result=automatic)`，其解释仅包含规则版本、计数、阈值、窗口、路由模板和方法。

`backend/tests/test_gap13_security.py` 固定最小正常与攻击样本：正常请求 allow；同一哈希 IP 的第二次攻击请求 block；管理员 release 后保留回放；复核分别记录误报和漏报标签。测试同时断言审计序列不包含原始 IP、设备、Authorization 或 Cookie。
