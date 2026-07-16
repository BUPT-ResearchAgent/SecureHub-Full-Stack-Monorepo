# frontend/AGENTS.md — SecureHub 前端局部规则

> 父文档：仓库根 `AGENTS.md`；项目宪法：`CLAUDE.md`。
> 本文件只描述前端目录内的局部约束，不复述全局铁律。

---

## 1. 技术栈

| 层 | 选择 |
|---|---|
| 框架 | React 18 |
| 构建 | Vite 6 |
| 语言 | TypeScript（strict） |
| 样式 | Tailwind v4 + tw-animate-css |
| 组件库 | shadcn/ui（基于 Radix） |
| 路由 | React Router v7 |
| 状态 | `useReducer` + `localStorage`（per-feature） |
| 流式 | 自研 `lib/sse.ts`（含 `openSSEPost`） |
| 节点图 | reactflow ^11 |
| 动效 | motion ^12 |
| 图表 | recharts |
| Markdown | react-markdown + remark-gfm + react-syntax-highlighter |
| 思维导图 | markmap-lib + markmap-view |
| PPT 预览 | reveal.js |
| 流程图 | mermaid |

**禁止引入**：Redux / Zustand / Jotai / MUI（除已有 @mui/* 老代码维持现状）。

---

## 2. 目录边界

| 目录 | 用途 | 谁修改 |
|---|---|---|
| `src/app/pages/` | 路由页面 | B |
| `src/app/features/<name>/` | 功能模块（5 件套：api / store / types / utils / components） | B |
| `src/app/components/` | 全局组件（Layout / EvidenceDrawer / BrandFooter 等） | B |
| `src/app/components/ui/` | shadcn/ui 47 个原子组件 | B（不要乱改原子组件） |
| `src/lib/` | api / sse / mock / persist / 工具 | B |
| `src/lib/mock/` | mock 数据 | B |
| `src/styles/` | 全局 css | B |

---

## 3. 必须遵守

### 3.1 不扩展 legacy 页面（强制）

以下 7 个页面是早期 Figma 导出的静态原型，**不要在它们里面写新功能**：

```
Home / Planner / Assets / DataHub / DocStudio / IdeaLab / Opportunities / Recommender
```

新功能进入活跃页面：`Workspace / Practice / CourseStudy / Research / Writing / Chat / Forum / Careers / Tasks / Profile / Teacher / Showcase`。

### 3.2 API 调用必须走 lib/api.ts（强制）

```ts
// ❌ 不允许
fetch('http://localhost:8000/api/v1/courses')

// ✅ 必须用
import { apiGet, apiPost, apiStream } from '@/lib/api'
const courses = await apiGet<CourseListResponse>('/api/v1/courses')
```

后端地址通过 `VITE_API_BASE_URL` 环境变量配置，前端代码不硬编码。

### 3.3 mock fallback 必须用 withMockFallback（强制）

```ts
// ❌ 守门式（真后端 502 时不会自动降级）
if (isMockMode()) return mockData
return apiGet(...)

// ✅ 异常 catch 降级式
return withMockFallback(
  () => apiGet<T>('/api/v1/...'),
  () => mockData,
)
```

### 3.4 状态管理统一 useReducer + localStorage（强制）

每个 feature 自带：`store.ts`（reducer）+ `utils.ts`（持久化 helper）。

跨 feature 通信通过 `taskBridge.ts`（已有），不引入 Redux / Zustand。

### 3.5 全中文用户文案（强制）

所有用户可见 JSX 文本必须中文，包含：

- 按钮 / 标题 / 描述 / 占位符
- tooltip / aria-label
- 错误态文案
- empty state 文案

代码标识符（变量名、函数名）保持英文。

### 3.6 优先 shadcn/ui + Radix（强制）

新组件优先用 `src/app/components/ui/` 下的 shadcn 原子。若原子缺失，在 Radix 基础上自建，不要从零造轮子或换 UI 库。

### 3.7 WEBSEC-101 课程整理内容（强制）

- `features/course/websec/` 是只面向 `WEBSEC-101` 的 `curated-demo` 数据与界面；题库、课程路线和课程资料不得被 preview 课程复用，也不得冒充后端实时生成或已发布持久数据。
- `/course` 的入口不能静态依赖路线图、资源目录或题库等可选模块。新模块必须 `React.lazy` + 局部 ErrorBoundary；`localStorage` / `sessionStorage` 访问必须容错，URL 是存储不可用时的权威状态。
- 公共视频在运行时只显示 `public/assets/websec/bilibili/` 下已提交的封面、真实标题、BVID 和原平台外链；禁止 iframe、播放器和浏览器端 Bilibili API 请求。
- `scripts/fetch-websec-bilibili-covers.py` 是**人工触发的采集工具**，不是前端 API 调用的例外：仅在明确授权下访问白名单公开视频页，不携带 Cookie、不下载视频/音频/弹幕；不得在 React 组件中直接复用其 HTTP 逻辑。

---

## 4. 推荐验证命令

```bash
# 类型检查（必须 0 error）
pnpm typecheck

# 生产构建（必须成功；最大 chunk gzip 控制在 300 kB）
pnpm build

# 开发 server
pnpm dev    # 默认 5173

# 如有 lint
pnpm lint   # 可选
```

---

## 5. Codex 子智能体建议

修改本目录代码时优先：

- 主写：`securehub_frontend_worker`
- 收尾审查：`securehub_review_qa`
- 大规模 UI 重构前置规划：`securehub_planner`

不要默认调 `securehub_backend_rag_worker`，除非任务明确涉及前后端 endpoint 字段调整。

---

## 6. 引用

- 项目宪法：`CLAUDE.md`
- 课程契约：`docs/api/course-contract.md`
- 学习契约（产品化升级）：`docs/api/learning-contract.md`
- 教师契约：`docs/api/teacher-contract.md`
- B 角色后续收尾：`Plan/B角色后续收尾计划.md`
- 当前提示词：`Prompt/5-B-1.md`
- WebSec 演示数据边界：仓库根 `AGENTS.md` 的“WEBSEC-101 课程整理与公开视频封面”
