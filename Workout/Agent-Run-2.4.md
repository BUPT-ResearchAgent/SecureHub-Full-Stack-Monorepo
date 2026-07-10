# Agent-Run-2.4 最终真实模型调用闭环

- 修复根因：Harness 此前构造了 QualityCheck `artifact`，但未把它投影进模型 prompt，导致真实判定以 `critical/relevance`、`accept=false` 拒绝；现已传入学习路径、课程文档和题目三项结构化输出，未放宽或跳过 QualityCheck。另为 `deepseek-v4-pro` 的 JSON object 请求显式关闭默认 thinking，收紧课程 Markdown 的 JSON 转义要求，并合并细碎 token 事件以保留完整 replay。
- Success root：`e467671e-52a8-408a-b8f7-68087b7cd366`，`mode=real`、`provider=deepseek`、`model=deepseek-v4-pro`、`status=succeeded`；QualityCheck 为 `accept=true`、`quality_score=0.92`、`defects=0`。
- Success SSE：共 `264` 条，`progress=25`、`evidence=5`、`token=228`、`trace=5`、`done=1`；`Last-Event-ID: 0` replay 同为 `264` 条且 event IDs 完全一致。
- Cancel root：`54d66622-d672-4ced-99ce-92d379eb42a0`，首条真实 token 的 cursor 为 `5`，取消响应为 `cancelling`，root 与 `done` 最终均为 `cancelled`；SSE 共 `6` 条（`progress=3`、`evidence=1`、`token=1`、`done=1`），cursor 后无 token 或 artifact。
- `agent_runs` 对齐：success root 恰好 `5` 条且均为 `success` / `persistence=agent_runs`，user/agent/skill 外键完整；status、SSE trace、PostgreSQL child UUID 集合一致，SSE 与 PostgreSQL evidence ID 集合一致（union `9`）。
- 实际 DeepSeek 模型调用：`12` 次（两次依据新诊断修复后的失败 workflow 各 `3` 次、最终 success `5` 次、first-token cancel `1` 次）。
- 实现 commit：`038af417`。
