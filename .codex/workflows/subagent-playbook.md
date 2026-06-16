# SecureHub Codex Subagent Playbook

## Cost-aware principle

Do not spawn all agents by default. Use the smallest agent set that can finish the task.

Default budget mode:
- Small frontend task: frontend_worker only.
- Small backend task: backend_rag_worker only.
- Review task: review_qa only.
- Complex feature: planner -> backend_rag_worker/frontend_worker -> review_qa.
- Docs task: docs_delivery only.

Keep `max_depth = 1`.
Avoid parallel write-heavy work on the same files.

## Workflow 1: Small frontend fix

Spawn:
- securehub_frontend_worker

Optional:
- securehub_review_qa after changes

Prompt:
请只使用 securehub_frontend_worker 修复该前端问题。不要启动 planner，除非发现涉及后端 API 契约或全局布局架构。完成后如改动超过 6 个文件，再使用 securehub_review_qa 做一次只读审查。

## Workflow 2: Small backend/API fix

Spawn:
- securehub_backend_rag_worker

Optional:
- securehub_review_qa

Prompt:
请只使用 securehub_backend_rag_worker 完成该后端接口/服务修复。不要启动 frontend_worker，除非接口返回字段需要前端同步。完成后使用 securehub_review_qa 检查 Status 标注、schema、测试和 Harness/RAG 约束。

## Workflow 3: Complex A3 vertical slice

Spawn:
- securehub_planner
- securehub_backend_rag_worker
- securehub_frontend_worker
- securehub_review_qa

Prompt:
这是复杂垂直切片任务。请先由 securehub_planner 只读拆解任务，再由 backend_rag_worker 和 frontend_worker 分边界实现，最后由 review_qa 审查契约、测试、SSE、agent_runs、generated_resources/storage_objects。不要启动 docs_delivery，除非本次任务明确要求更新交付文档。

## Workflow 4: PR review

Spawn:
- securehub_review_qa

Optional:
- securehub_planner if architecture or DB/Harness changed

Prompt:
请使用 securehub_review_qa 对当前分支相对 dev 的改动做只读审查。若发现涉及业务智能体边界、DB schema、Harness、RAG 或生成资源链路，再调用 securehub_planner 做架构级复核。

## Workflow 5: Delivery docs

Spawn:
- securehub_docs_delivery

Prompt:
请只使用 securehub_docs_delivery 更新交付文档，不修改业务代码，不新增产品运行时业务智能体，不把 Codex 子智能体写入 backend/app/agents。