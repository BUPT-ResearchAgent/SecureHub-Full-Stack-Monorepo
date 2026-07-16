import type { WebSecurityCurationMetadata, WebSecurityRouteLane, WebSecurityRouteNode, WebSecurityRouteTemplate } from '../types';
import { webSecurityKnowledgePointById } from './demoKnowledgePoints';
import { webSecurityPaperIds } from './demoQuestionBanks';

const routeMetadata: WebSecurityCurationMetadata = {
  source: 'curated',
  reviewer: 'SecureHub 课程内容组',
  reviewStatus: 'curated',
  sourceNote: '固定 DAG 与 WEBSEC-101 的 17 个冻结知识点对齐。状态只保存在当前浏览器，不宣称为后端持久化知识图谱。',
  updatedAt: '2026-07-16T00:00:00Z',
  sourceTitle: 'SecureHub WEBSEC-101 course roadmap',
  sourceUrl: 'https://roadmap.sh/',
};

type RouteNodeDefinition = {
  knowledgePointId: string;
  prerequisites: readonly string[];
  baseDurationMinutes: number;
  resourceIds: readonly string[];
  recommendedPaperId?: string;
  position: { x: number; y: number };
  foundationLane: WebSecurityRouteLane;
  sprintLane: WebSecurityRouteLane;
  practicalLane: WebSecurityRouteLane;
  foundationRationale: string;
  sprintRationale: string;
  practicalRationale: string;
};

const routeNodeDefinitions: readonly RouteNodeDefinition[] = [
  {
    knowledgePointId: 'http-basics',
    prerequisites: [],
    baseDurationMinutes: 35,
    resourceIds: ['res-doc-websec-foundations', 'res-ppt-websec-review'],
    recommendedPaperId: webSecurityPaperIds.diagnostic,
    position: { x: 0, y: 360 },
    foundationLane: 'main',
    sprintLane: 'review',
    practicalLane: 'main',
    foundationRationale: '先建立请求、响应与 HTTPS 的共同语言，后续边界判断才有落点。',
    sprintRationale: '快速校准传输层边界，避免把 HTTPS 误当成业务安全的全部。',
    practicalRationale: '把传输边界作为每个服务端接口审查的第一项基线。',
  },
  {
    knowledgePointId: 'same-origin',
    prerequisites: ['http-basics'],
    baseDurationMinutes: 38,
    resourceIds: ['res-doc-websec-foundations', 'res-mindmap-websec'],
    position: { x: 300, y: 110 },
    foundationLane: 'main',
    sprintLane: 'review',
    practicalLane: 'optional',
    foundationRationale: '先理解浏览器能否读取跨源响应，再学习 CORS 的最小授权配置。',
    sprintRationale: '作为容易混淆概念的复习支线，用选择题检验 CORS 与授权的边界。',
    practicalRationale: '前端接口跨域时回到此节点核对 Origin allowlist 和凭据策略。',
  },
  {
    knowledgePointId: 'cookie-session',
    prerequisites: ['http-basics'],
    baseDurationMinutes: 42,
    resourceIds: ['res-doc-websec-foundations', 'res-ppt-websec-review'],
    position: { x: 300, y: 330 },
    foundationLane: 'main',
    sprintLane: 'main',
    practicalLane: 'main',
    foundationRationale: '会话状态连接认证、CSRF 和授权，是早期主线节点。',
    sprintRationale: '优先复习 Secure、HttpOnly、SameSite 和会话轮换等高频概念。',
    practicalRationale: '用于审查服务端鉴权中间件与关键操作的会话生命周期。',
  },
  {
    knowledgePointId: 'sql-injection',
    prerequisites: ['http-basics'],
    baseDurationMinutes: 55,
    resourceIds: ['res-doc-input-output', 'res-lab-data-access'],
    position: { x: 300, y: 570 },
    foundationLane: 'main',
    sprintLane: 'main',
    practicalLane: 'main',
    foundationRationale: '以参数化查询建立“数据不能改变指令”的核心安全编码模型。',
    sprintRationale: '作为阶段测验的核心高频点，用代码审查和多选题快速回顾。',
    practicalRationale: '直接进入数据访问层审查任务，输出可验证的修复清单。',
  },
  {
    knowledgePointId: 'xss-reflected',
    prerequisites: ['http-basics', 'same-origin'],
    baseDurationMinutes: 48,
    resourceIds: ['res-doc-input-output', 'res-mindmap-websec'],
    position: { x: 610, y: 90 },
    foundationLane: 'main',
    sprintLane: 'main',
    practicalLane: 'main',
    foundationRationale: '将请求参数回显的风险与输出上下文编码建立一一对应。',
    sprintRationale: '把自动转义、危险 sink 和 CSP 的职责分开记忆。',
    practicalRationale: '在模板与前端渲染代码中检查是否绕过了默认安全机制。',
  },
  {
    knowledgePointId: 'csrf',
    prerequisites: ['same-origin', 'cookie-session'],
    baseDurationMinutes: 45,
    resourceIds: ['res-doc-websec-foundations', 'res-video-websec-overview'],
    position: { x: 610, y: 310 },
    foundationLane: 'main',
    sprintLane: 'main',
    practicalLane: 'main',
    foundationRationale: '用浏览器自动携带会话解释为什么状态变更需要 Token 和来源校验。',
    sprintRationale: '集中复盘 Token、SameSite 和关键操作确认的分工。',
    practicalRationale: '在修改资料、导入和删除等状态接口上检查服务端验证。',
  },
  {
    knowledgePointId: 'file-upload',
    prerequisites: ['http-basics'],
    baseDurationMinutes: 48,
    resourceIds: ['res-lab-service-boundaries', 'res-ppt-websec-review'],
    position: { x: 610, y: 550 },
    foundationLane: 'main',
    sprintLane: 'main',
    practicalLane: 'main',
    foundationRationale: '从存储位置、类型与解析流程理解上传不是单一扩展名问题。',
    sprintRationale: '将上传隔离、白名单和异步扫描纳入考前检查单。',
    practicalRationale: '作为导入和附件功能代码审查的真实服务端边界练习。',
  },
  {
    knowledgePointId: 'ssrf',
    prerequisites: ['http-basics'],
    baseDurationMinutes: 52,
    resourceIds: ['res-lab-service-boundaries', 'res-readings-owasp'],
    position: { x: 610, y: 770 },
    foundationLane: 'optional',
    sprintLane: 'main',
    practicalLane: 'main',
    foundationRationale: '基础主线完成后再补服务端替用户发请求的特殊信任边界。',
    sprintRationale: '作为综合场景题重点，复盘 allowlist、地址校验和出站隔离。',
    practicalRationale: '直接映射 URL 预览、导入外部资料等产品能力的风险审查。',
  },
  {
    knowledgePointId: 'sql-injection-blind',
    prerequisites: ['sql-injection'],
    baseDurationMinutes: 35,
    resourceIds: ['res-lab-data-access', 'res-quiz-defensive-checkpoint'],
    position: { x: 610, y: 980 },
    foundationLane: 'review',
    sprintLane: 'main',
    practicalLane: 'optional',
    foundationRationale: '放入复习支线，先牢固掌握参数化查询再理解不可见的异常信号。',
    sprintRationale: '补足阶段测验的时延、日志和统一错误响应辨析。',
    practicalRationale: '作为数据访问监控与异常查询告警的增强练习。',
  },
  {
    knowledgePointId: 'auth-bypass',
    prerequisites: ['cookie-session', 'sql-injection'],
    baseDurationMinutes: 46,
    resourceIds: ['res-lab-service-boundaries', 'res-quiz-defensive-checkpoint'],
    position: { x: 610, y: 1190 },
    foundationLane: 'main',
    sprintLane: 'main',
    practicalLane: 'main',
    foundationRationale: '把“用户是谁”和“用户能操作什么”明确分开，形成后续接口审查习惯。',
    sprintRationale: '重点练习对象级、批量接口和历史链接的服务端授权判断。',
    practicalRationale: '用于检查课程、作业、资源和教学班操作的对象级权限。',
  },
  {
    knowledgePointId: 'xss-stored',
    prerequisites: ['xss-reflected'],
    baseDurationMinutes: 40,
    resourceIds: ['res-doc-input-output', 'res-mindmap-websec'],
    position: { x: 920, y: 0 },
    foundationLane: 'optional',
    sprintLane: 'main',
    practicalLane: 'optional',
    foundationRationale: '作为反射型 XSS 的延伸，理解持久化内容和历史数据的额外治理。',
    sprintRationale: '用于区分提交入口修复与多个渲染点、历史数据迁移的考试考点。',
    practicalRationale: '当产品有评论、公告或富文本时，转入此支线补齐净化策略。',
  },
  {
    knowledgePointId: 'xss-dom',
    prerequisites: ['xss-reflected'],
    baseDurationMinutes: 45,
    resourceIds: ['res-doc-input-output', 'res-mindmap-websec'],
    position: { x: 920, y: 150 },
    foundationLane: 'review',
    sprintLane: 'main',
    practicalLane: 'main',
    foundationRationale: '在输出编码基础上补充浏览器端来源到 sink 的数据流视角。',
    sprintRationale: '将 location、postMessage 与安全 DOM API 列为高区分度复习点。',
    practicalRationale: '用于单页应用、URL 参数和跨窗口消息的代码审查。',
  },
  {
    knowledgePointId: 'deserialization',
    prerequisites: ['cookie-session', 'file-upload'],
    baseDurationMinutes: 50,
    resourceIds: ['res-lab-service-boundaries', 'res-readings-owasp'],
    position: { x: 920, y: 540 },
    foundationLane: 'optional',
    sprintLane: 'main',
    practicalLane: 'main',
    foundationRationale: '以对象边界为补充，不打断基础主线但保留完整课程覆盖。',
    sprintRationale: '通过“简单数据格式 + 类型校验”的原则收敛复杂概念。',
    practicalRationale: '用于审查导入、缓存、会话与消息传输中的对象恢复路径。',
  },
  {
    knowledgePointId: 'waf-bypass',
    prerequisites: ['sql-injection-blind', 'auth-bypass'],
    baseDurationMinutes: 32,
    resourceIds: ['res-readings-owasp', 'res-ppt-websec-review'],
    position: { x: 920, y: 990 },
    foundationLane: 'review',
    sprintLane: 'review',
    practicalLane: 'review',
    foundationRationale: '避免把规则拦截当作根因修复，作为纵深防御复盘节点。',
    sprintRationale: '提示考试中将检测、缓解与应用修复区分作答。',
    practicalRationale: '将告警回溯到输入、输出、权限和测试证据，而不新增绕过细节。',
  },
  {
    knowledgePointId: 'rce',
    prerequisites: ['file-upload', 'ssrf', 'deserialization'],
    baseDurationMinutes: 55,
    resourceIds: ['res-lab-service-boundaries', 'res-ppt-websec-review'],
    position: { x: 1230, y: 550 },
    foundationLane: 'optional',
    sprintLane: 'main',
    practicalLane: 'main',
    foundationRationale: '作为服务端边界的综合提高点，先完成输入、文件和对象边界。',
    sprintRationale: '连接文件、对象和外部工具场景，练习结构化 API 与运行时隔离。',
    practicalRationale: '用于审查转换、预览和自动化任务中的 shell 与运行权限边界。',
  },
  {
    knowledgePointId: 'secure-coding',
    prerequisites: ['sql-injection', 'xss-reflected', 'csrf', 'auth-bypass'],
    baseDurationMinutes: 42,
    resourceIds: ['res-lab-data-access', 'res-ppt-websec-review'],
    recommendedPaperId: webSecurityPaperIds.stageA,
    position: { x: 1230, y: 900 },
    foundationLane: 'main',
    sprintLane: 'main',
    practicalLane: 'main',
    foundationRationale: '把基础控制落实为代码审查、回归测试和发布前检查闭环。',
    sprintRationale: '以阶段测验复盘错题，把知识点收束成可执行的修复流程。',
    practicalRationale: '作为实操路线的核心交付，形成可审计的修复与验证记录。',
  },
  {
    knowledgePointId: 'owasp-top10',
    prerequisites: ['xss-stored', 'xss-dom', 'csrf', 'file-upload', 'ssrf', 'deserialization', 'rce', 'auth-bypass', 'waf-bypass', 'secure-coding'],
    baseDurationMinutes: 50,
    resourceIds: ['res-ppt-websec-review', 'res-mindmap-websec', 'res-readings-owasp'],
    recommendedPaperId: webSecurityPaperIds.sprint,
    position: { x: 1530, y: 560 },
    foundationLane: 'review',
    sprintLane: 'main',
    practicalLane: 'review',
    foundationRationale: '用综合回顾确认各条支线都回到风险、控制和验证证据。',
    sprintRationale: '作为冲刺模拟卷前的总复盘节点，串起 17 个知识点。',
    practicalRationale: '在实操交付后用风险分类复核是否遗漏资产、边界或验证。',
  },
];

type RouteProfile = {
  id: string;
  durationFactor: number;
  lane: (definition: RouteNodeDefinition) => WebSecurityRouteLane;
  rationale: (definition: RouteNodeDefinition) => string;
};

const routeProfiles: Record<'foundation' | 'sprint' | 'practical', RouteProfile> = {
  foundation: {
    id: 'route-foundation-clearance',
    durationFactor: 1,
    lane: (definition) => definition.foundationLane,
    rationale: (definition) => definition.foundationRationale,
  },
  sprint: {
    id: 'route-exam-sprint',
    durationFactor: 0.72,
    lane: (definition) => definition.sprintLane,
    rationale: (definition) => definition.sprintRationale,
  },
  practical: {
    id: 'route-secure-development-practice',
    durationFactor: 1.12,
    lane: (definition) => definition.practicalLane,
    rationale: (definition) => definition.practicalRationale,
  },
};

function buildRouteNodes(profile: RouteProfile): readonly WebSecurityRouteNode[] {
  return routeNodeDefinitions.map((definition) => {
    const knowledgePoint = webSecurityKnowledgePointById[definition.knowledgePointId];
    return {
      ...routeMetadata,
      id: `${profile.id}:${definition.knowledgePointId}`,
      title: knowledgePoint?.title ?? definition.knowledgePointId,
      knowledgePointId: definition.knowledgePointId,
      lane: profile.lane(definition),
      prerequisites: definition.prerequisites.map((knowledgePointId) => `${profile.id}:${knowledgePointId}`),
      durationMinutes: Math.max(15, Math.round(definition.baseDurationMinutes * profile.durationFactor)),
      resourceIds: definition.resourceIds,
      recommendedPaperId: definition.recommendedPaperId,
      rationale: profile.rationale(definition),
      position: definition.position,
    };
  });
}

export const webSecurityRouteTemplates: readonly WebSecurityRouteTemplate[] = [
  {
    ...routeMetadata,
    id: routeProfiles.foundation.id,
    courseCode: 'WEBSEC-101',
    title: '基础通关路线',
    summary: '面向首次系统学习 Web 安全的学生：先建立浏览器与服务端边界，再逐步进入综合复盘。',
    audience: '基础薄弱、希望按先修关系稳定推进的学习者',
    estimatedMinutes: 758,
    recommendedDiagnosticScore: { min: 0, max: 59 },
    nodes: buildRouteNodes(routeProfiles.foundation),
  },
  {
    ...routeMetadata,
    id: routeProfiles.sprint.id,
    courseCode: 'WEBSEC-101',
    title: '考试冲刺路线',
    summary: '面向已完成基础学习的学生：压缩讲解时间，突出高频易错点、阶段测验与综合模拟。',
    audience: '已学过核心概念、正在准备阶段测验或答辩演示的学习者',
    estimatedMinutes: 545,
    recommendedDiagnosticScore: { min: 60, max: 100 },
    nodes: buildRouteNodes(routeProfiles.sprint),
  },
  {
    ...routeMetadata,
    id: routeProfiles.practical.id,
    courseCode: 'WEBSEC-101',
    title: '安全开发实操路线',
    summary: '面向希望把概念落到代码、接口和服务端边界审查中的学习者，优先完成防御性检查单。',
    audience: '希望用代码审查和服务端边界检查完成实操复盘的学习者',
    estimatedMinutes: 850,
    recommendedDiagnosticScore: { min: 50, max: 100 },
    nodes: buildRouteNodes(routeProfiles.practical),
  },
] as const;

export const webSecurityRouteTemplateById = Object.fromEntries(
  webSecurityRouteTemplates.map((template) => [template.id, template]),
) as Record<string, WebSecurityRouteTemplate>;

export const webSecurityRouteNodeById = Object.fromEntries(
  webSecurityRouteTemplates.flatMap((template) => template.nodes.map((node) => [node.id, node])),
) as Record<string, WebSecurityRouteNode>;
