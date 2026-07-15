# 公平监控与申诉契约（T6）

状态：`real`。本契约只覆盖教育评估的聚合公平监控、人工复核和申诉；它不创建敏感属性库，也不允许自动改变个人成绩、权限、排序或处分。

## 数据与隐私边界

- 成绩输入只来自 `assessment_grade_decisions.status = published` 且 `final_score` 已存在的 T3 记录。
- 用户、课程、画像和知识资产均只通过既有外键引用；不复制任何权威源。
- 默认允许的最小分组只有 RFC §8.1 的非敏感 `cohort` 和 `teaching_class`。请求 `gender` 等未许可字段固定拒绝为 `FAIRNESS_ATTRIBUTE_NOT_ALLOWED`。
- 每位参与者必须持有该 policy 的有效 `assessment_fairness` 同意。撤回和过期都使后续运行固定拒绝为 `FAIRNESS_CONSENT_REQUIRED`；历史审计保留。
- 若分组缺失则为 `FAIRNESS_DATA_MISSING`；任一组低于 policy 的 `minimum_sample` 时返回 `insufficient_sample / INSUFFICIENT_SAMPLE`，不写 metric cell、不显示群体结论。
- 所有 dashboard 读接口都要求服务端 `administrator` role grant；浏览器身份、URL 和前端状态不是授权来源。

## HTTP 面

| 路径 | 权限 | 行为 |
| --- | --- | --- |
| `POST /api/v1/fairness/consents` | 本人 | 授予可过期同意 |
| `POST /api/v1/fairness/consents/{policy_id}/withdraw` | 本人 | 撤回同意，保留审计 |
| `POST /api/v1/fairness/appeals` | 本人成绩 | 提交人工申诉，不触发自动重评分 |
| `GET /api/v1/fairness/appeals/me/grades` | 本人 | 仅列本人已发布且可申诉成绩 |
| `GET/POST /api/v1/fairness/policies` | 管理员 | 查看/创建 versioned policy |
| `POST /api/v1/fairness/policies/{id}/group-assignments` | 管理员 | 对已有效同意用户配置最小非敏感分组 |
| `POST /api/v1/fairness/policies/{id}/metric-runs` | 管理员 | 计算已发布成绩的聚合指标 |
| `GET /api/v1/fairness/dashboard` | 管理员 | 指标版本、样本量、限制、告警 |
| `POST /api/v1/fairness/alerts/{id}/reviews` | 管理员 | 记录人工复核与理由 |
| `GET /api/v1/fairness/appeals` / `POST .../resolve` | 管理员 | 读取/写入人工申诉说明 |

写操作均写入 `governance_audit_events`，含 actor、对象、理由、结果、UTC 时间；不写 Runtime `agent_runs`。

## 指标语义

- 每个 cell 固化样本量、均值、通过率、均值近似 95% 区间、Wilson 通过率 95% 区间和限制。
- 有真实 ground truth 标签时才适用 accuracy、FPR、FNR、机会均等；当前 T3 最终成绩没有该标签，字段为 `null` 并明确 `not_applicable_without_ground_truth_labels`。
- 差异相对样本量最大的稳定 reference group 计算；超过 versioned policy 阈值只创建 `fairness_alerts`，必须人工 review。
- 公平结果绝不回写 `assessment_grade_decisions`。申诉只形成 `fairness_appeals` 和人工说明。

## 回滚

关闭 `/fairness` 前端路由和 endpoint 挂载可停止展示/新运行；保留合法审计。数据库回滚只执行 `20260715_1085` downgrade，绝不删除用户、课程、已发布成绩、画像、知识资产或 Runtime 记录。
