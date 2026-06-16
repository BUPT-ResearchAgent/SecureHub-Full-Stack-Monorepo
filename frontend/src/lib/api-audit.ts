// Status: real
//
// 11 个 A3 主路径端点的审计清单。
// 与 docs/api/course-contract.md §1 一一对应；BackendStatusPanel 的「契约对比」tab
// 渲染本表，前端 fallback 策略也以此表为权威。

export type EndpointMethod = 'GET' | 'POST' | 'PUT';
export type EndpointStatus = 'real' | 'partial-real' | 'mock' | 'planned';
export type EndpointOwner = 'A' | 'B' | 'C';

export type EndpointAudit = {
  /** 用于点击重新探测时唯一定位。 */
  id: string;
  path: string;
  method: EndpointMethod;
  owner: EndpointOwner;
  /** A3 主路径中的契约位置（如 1.1 / 1.3）。 */
  contractRef: string;
  status: EndpointStatus;
  /** 一句话功能描述，给评委 / 队友看，不是给前端逻辑用的。 */
  summary: string;
  /** partial-real 时哪些字段是真的，哪些是占位。 */
  realFields?: string[];
  /** 失败时前端会切回哪条 mock 路径；planned 状态下也填，便于演示。 */
  fallbackMock: string;
  /** 'YYYY-MM-DD'，最后一次人工/自动验证的日期。 */
  lastVerified?: string;
  /** 已知偏差或注意事项。 */
  knownIssues?: string[];
  /** SSE 类型默认不在 GET/POST 自检里覆盖。 */
  sse?: boolean;
};

export const ENDPOINT_AUDIT: EndpointAudit[] = [
  {
    id: 'courses-list',
    path: '/api/v1/courses',
    method: 'GET',
    owner: 'A',
    contractRef: '1.1',
    status: 'partial-real',
    summary: '课程目录列表（默认只返回 enabled 课程）',
    realFields: ['id', 'code', 'title', 'description', 'progress'],
    fallbackMock: 'mockCourse + courseCatalog',
    lastVerified: '2026-06-14',
    knownIssues: [
      '后端实际只有 1 门 Web 安全课，多课程演示由前端 courseCatalog 补齐',
      '`progress` 是用户级字段，未接入个性化时是常量',
    ],
  },
  {
    id: 'course-plan',
    path: '/api/v1/courses/{cid}/plan',
    method: 'POST',
    owner: 'A',
    contractRef: '1.2',
    status: 'partial-real',
    summary: '生成学习路径（依赖知识图谱）',
    fallbackMock: 'mockLearningPath',
    lastVerified: '2026-06-16',
    knownIssues: ['已接 real-first endpoint；A service 函数尚未交付时回退到 GenerateLearningPath skill'],
  },
  {
    id: 'course-resources-generate',
    path: '/api/v1/courses/{cid}/resources/generate',
    method: 'POST',
    owner: 'A',
    contractRef: '1.3',
    status: 'partial-real',
    summary: '生成 7 类学习资源（SSE，含 evidence/token/artifact）',
    fallbackMock: 'replayResourceGeneration（按 type 回放）',
    lastVerified: '2026-06-16',
    knownIssues: [
      '已接 real-first SSE endpoint；A service 函数尚未交付时回退到资源 skill map',
      '前端已从 isMockMode 守门改为 withMockFallback + mock SSE replay',
    ],
    sse: true,
  },
  {
    id: 'agent-runs',
    path: '/api/v1/agent-runs',
    method: 'GET',
    owner: 'A',
    contractRef: '1.4',
    status: 'partial-real',
    summary: '智能体调用历史（演示用 trace 数据流）',
    realFields: ['id', 'workflow_name', 'agent_name', 'skill_name', 'status'],
    fallbackMock: 'mockAgentRuns',
    lastVerified: '2026-06-14',
    knownIssues: ['`quality_score` 来自 outcome_evaluator，未接入时为常量'],
  },
  {
    id: 'agent-run-detail',
    path: '/api/v1/agent-runs/{run_id}',
    method: 'GET',
    owner: 'A',
    contractRef: '1.5',
    status: 'partial-real',
    summary: '单条 trace 详情（input/output/token_usage）',
    realFields: ['id', 'agent_name', 'skill_name', 'status'],
    fallbackMock: 'mockAgentRuns[0]',
    lastVerified: '2026-06-14',
    knownIssues: ['后端尚未把 token_usage 落库，前端展示用占位 0/0'],
  },
  {
    id: 'profile-chat',
    path: '/api/v1/profile/chat',
    method: 'POST',
    owner: 'A',
    contractRef: '1.6',
    status: 'partial-real',
    summary: '画像构建对话（SSE，写入 dimensions + capabilities）',
    fallbackMock: 'replayPersonaChat',
    lastVerified: '2026-06-16',
    knownIssues: ['已改为 SSE real-first；A service 函数尚未交付时回退到 BuildLearningPersona skill'],
    sse: true,
  },
  {
    id: 'profile-me',
    path: '/api/v1/profile/me',
    method: 'GET',
    owner: 'A',
    contractRef: '1.7',
    status: 'partial-real',
    summary: '当前用户画像（dimensions + capabilities）',
    realFields: ['user_id', 'dimensions'],
    fallbackMock: 'mockProfile',
    lastVerified: '2026-06-14',
    knownIssues: ['`capabilities` 仅在评估通过后才会更新，初始为空数组'],
  },
  {
    id: 'profile-me-put',
    path: '/api/v1/profile/me',
    method: 'PUT',
    owner: 'A',
    contractRef: '1.8',
    status: 'partial-real',
    summary: '更新画像维度（不改 capabilities）',
    realFields: ['dimensions'],
    fallbackMock: '前端 reducer 内更新',
    lastVerified: '2026-06-14',
  },
  {
    id: 'rag-search',
    path: '/api/v1/rag/search',
    method: 'POST',
    owner: 'C',
    contractRef: '1.9',
    status: 'partial-real',
    summary: 'RAG 检索（BM25 + 向量 + RRF）',
    realFields: ['chunks', 'total'],
    fallbackMock: 'mockEvidenceChunks',
    lastVerified: '2026-06-14',
    knownIssues: ['domain 过滤已生效；reranker 仍在调优'],
  },
  {
    id: 'tutor-ask',
    path: '/api/v1/tutor/ask',
    method: 'POST',
    owner: 'A',
    contractRef: '1.10',
    status: 'partial-real',
    summary: '辅导问答（career_planner 路由，SSE）',
    fallbackMock: 'replayTutorAsk',
    lastVerified: '2026-06-16',
    knownIssues: ['已改为 SSE real-first；A service 函数尚未交付时回退到 RouteTutorQuestion skill'],
    sse: true,
  },
  {
    id: 'assessment-run',
    path: '/api/v1/assessment/run',
    method: 'POST',
    owner: 'A',
    contractRef: '1.11',
    status: 'partial-real',
    summary: '评估提交，回流 learning_events 与 user_capabilities',
    fallbackMock: 'replayAssessment',
    lastVerified: '2026-06-16',
    knownIssues: ['已接 real-first endpoint；A service 函数尚未交付时回退到 RunAssessment skill'],
  },
];

export const ENDPOINT_BY_ID: Record<string, EndpointAudit> = Object.fromEntries(
  ENDPOINT_AUDIT.map((endpoint) => [endpoint.id, endpoint]),
);

export const STATUS_TONE: Record<EndpointStatus, { label: string; emoji: string; className: string }> = {
  real: { label: '真实', emoji: '✅', className: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  'partial-real': { label: '半真', emoji: '⚠️', className: 'bg-amber-50 text-amber-700 border-amber-200' },
  mock: { label: 'Mock', emoji: '🧪', className: 'bg-slate-50 text-slate-700 border-slate-200' },
  planned: { label: '未实现', emoji: '❌', className: 'bg-rose-50 text-rose-700 border-rose-200' },
};

export const OWNER_LABEL: Record<EndpointOwner, string> = {
  A: '成员 A（后端）',
  B: '成员 B（前端）',
  C: '成员 C（RAG/数据）',
};
