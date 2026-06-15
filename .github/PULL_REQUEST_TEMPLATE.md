## 本 PR 做了什么 / Summary

-

## 属于哪个模块 / Module

- [ ] 后端 Agent / Workflow
- [ ] 前端 Course UI
- [ ] 知识库 / Seed / Test
- [ ] 文档 / CI / 集成

## 是否触碰铁律 / Architecture Checks

- [ ] 未新增第 10 个 agent / I did not add a 10th agent role.
- [ ] 未把跨领域基础设施建模成 agent / I did not model cross-cutting infrastructure as an agent.
- [ ] 未新增 domain 专用表（如 course_chunks / fund_chunks）
- [ ] 未新增 feature-local persona 存储；`user_profiles` 仍是唯一画像源。
- [ ] 新 endpoint / service / repository 文件已加 Status 注释。
- [ ] 生成式 skill 已先调用 `rag.retrieve()`。
- [ ] skill 返回前已调用 `ctx.log_run()`。
- [ ] 改 schema / 架构规则时已同步 `CLAUDE.md` 和 `AGENTS.md` 对应章节。

## 验收命令 / Checks

```bash

```

## 截图 / 日志

-
