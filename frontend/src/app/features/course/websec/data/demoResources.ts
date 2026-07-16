import { WEB_SECURITY_RESOURCE_TYPES } from '../types';
import type { WebSecurityCurationMetadata, WebSecurityExternalUrlKind, WebSecurityResource } from '../types';

export const webSecurityAllowedExternalHosts = [
  'owasp.org',
  'cheatsheetseries.owasp.org',
  'portswigger.net',
  'developer.mozilla.org',
  'www.bilibili.com',
  'i0.hdslb.com',
  'i1.hdslb.com',
  'i2.hdslb.com',
  'search.bilibili.com',
  'player.bilibili.com',
  'roadmap.sh',
] as const;

const allowedHostSet = new Set<string>(webSecurityAllowedExternalHosts);

export function isAllowedWebSecurityExternalUrl(value: string, _kind?: WebSecurityExternalUrlKind): boolean {
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && allowedHostSet.has(url.hostname);
  } catch {
    return false;
  }
}

export function getAllowedWebSecurityExternalUrl(value: string, kind?: WebSecurityExternalUrlKind): string | undefined {
  return isAllowedWebSecurityExternalUrl(value, kind) ? value : undefined;
}

const resourceMetadata: WebSecurityCurationMetadata = {
  source: 'curated',
  reviewer: 'SecureHub 课程内容组',
  reviewStatus: 'curated',
  sourceNote: '课程整理资源目录。课程摘要、外部阅读和视频入口与真实 Artifact、学习记录保持隔离。',
  updatedAt: '2026-07-16T00:00:00Z',
  sourceTitle: 'SecureHub WEBSEC-101 course resource catalog',
};

export const webSecurityResources: readonly WebSecurityResource[] = [
  {
    ...resourceMetadata,
    id: 'res-doc-websec-foundations',
    courseCode: 'WEBSEC-101',
    type: 'doc',
    title: 'Web 请求、浏览器边界与会话安全速览',
    summary: '用一次状态变更请求串起 HTTPS、同源策略、Cookie 属性、CORS 与 CSRF 防御。',
    knowledgePointIds: ['http-basics', 'same-origin', 'cookie-session', 'csrf'],
    learningGoals: ['说明 TLS 保护的对象', '区分 CORS 与认证授权', '为状态变更接口选择组合防护'],
    estimatedMinutes: 18,
    preview: {
      kind: 'markdown',
      body: `## 一条安全请求的最小检查表\n\n1. 传输层：敏感会话和状态变更只走 HTTPS，并启用 HSTS。\n2. 浏览器边界：CORS 仅允许受信任 Origin；带凭据时不得使用通配 Origin。\n3. 会话边界：Cookie 组合使用 Secure、HttpOnly、SameSite 和合理过期时间。\n4. 状态变更：在服务端校验 CSRF Token，并按业务需要校验 Origin 或 Referer。\n\n提示：CORS 是服务端授予浏览器读取响应的规则，不是权限校验。`,
    },
    sourceUrl: 'https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS',
    author: 'MDN Web Docs',
    licenseNote: '外部阅读仅以链接形式展示。',
  },
  {
    ...resourceMetadata,
    id: 'res-doc-input-output',
    courseCode: 'WEBSEC-101',
    type: 'doc',
    title: '输入、查询与输出编码的防御式设计',
    summary: '将 SQL 注入、三类 XSS 和安全编码原则归并为可复用的输入到输出数据流检查法。',
    knowledgePointIds: ['sql-injection', 'sql-injection-blind', 'xss-reflected', 'xss-stored', 'xss-dom', 'secure-coding'],
    learningGoals: ['识别数据和指令混用的边界', '按 HTML、属性、URL 和 DOM 上下文选择安全 API', '写出可验证的修复措施'],
    estimatedMinutes: 24,
    preview: {
      kind: 'markdown',
      body: `## 三个固定问题\n\n- 数据是否会改变解释器或查询的结构？数据库场景默认使用参数化查询。\n- 不可信内容会进入哪一种输出上下文？优先模板自动转义和 context-aware 编码。\n- 修复能否被回归测试证明？覆盖入口、历史数据、错误路径和权限最小化。\n\n不要把 WAF、黑名单或前端限制当作唯一修复。`,
    },
    sourceUrl: 'https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html',
    author: 'OWASP Cheat Sheet Series',
    licenseNote: '外部阅读仅以链接形式展示。',
  },
  {
    ...resourceMetadata,
    id: 'res-ppt-websec-review',
    courseCode: 'WEBSEC-101',
    type: 'ppt',
    title: 'WebSec 关键风险与修复闭环讲义',
    summary: '七页课程讲义，适合在阶段测验前快速复盘风险、控制和验证证据。',
    knowledgePointIds: ['http-basics', 'cookie-session', 'sql-injection', 'xss-reflected', 'csrf', 'file-upload', 'ssrf', 'auth-bypass', 'secure-coding', 'owasp-top10'],
    learningGoals: ['建立漏洞到控制到验证的表达框架', '按风险优先级组织复盘', '为答题和代码审查准备证据'],
    estimatedMinutes: 15,
    preview: {
      kind: 'slides',
      slides: [
        { title: '从资产到边界', bullets: ['识别数据、会话、文件和出站网络资产', '把浏览器、服务端和依赖视为不同信任边界'] },
        { title: '输入不能变成指令', bullets: ['参数化查询隔离 SQL 结构', '避免把用户输入交给 shell、模板或对象恢复器'] },
        { title: '输出必须匹配上下文', bullets: ['模板自动转义优先', 'DOM 使用 textContent 等安全 API'] },
        { title: '认证不等于授权', bullets: ['每次资源操作均在服务端判定权限', '拒绝默认、记录关键审计事件'] },
        { title: '上传与出站请求', bullets: ['隔离存储、类型白名单、异步扫描', 'URL allowlist、DNS/IP 校验、出站隔离'] },
        { title: '纵深防御与检测', bullets: ['WAF 是补充而不是修复', '日志、告警、回归测试共同验证控制'] },
        { title: '修复闭环', bullets: ['复现边界、最小修复、回归验证', '记录剩余风险和版本证据'] },
      ],
    },
    sourceUrl: 'https://owasp.org/www-project-top-ten/',
    author: 'SecureHub 课程内容组',
  },
  {
    ...resourceMetadata,
    id: 'res-mindmap-websec',
    courseCode: 'WEBSEC-101',
    type: 'mindmap',
    title: 'WebSec 防御知识图复盘',
    summary: '以“输入、输出、身份、文件、出站、执行、治理”为主干的思维导图。',
    knowledgePointIds: ['same-origin', 'cookie-session', 'sql-injection', 'xss-reflected', 'xss-stored', 'xss-dom', 'csrf', 'file-upload', 'ssrf', 'deserialization', 'rce', 'auth-bypass', 'waf-bypass', 'secure-coding', 'owasp-top10'],
    learningGoals: ['定位知识点之间的先修关系', '建立防御策略的类别记忆', '选择下一步复习节点'],
    estimatedMinutes: 12,
    preview: {
      kind: 'mindmap',
      markdown: `# WebSec 防御\n## 输入与数据访问\n### 参数化查询\n### 类型与长度白名单\n## 浏览器输出\n### 模板转义\n### 安全 DOM API\n## 身份与权限\n### 会话属性\n### 服务端授权\n## 服务端边界\n### 文件隔离\n### 出站请求控制\n### 禁止不可信对象恢复\n## 修复闭环\n### 测试\n### 监控\n### 复盘`,
    },
    sourceUrl: 'https://owasp.org/www-project-top-ten/',
    author: 'SecureHub 课程内容组',
  },
  {
    ...resourceMetadata,
    id: 'res-quiz-defensive-checkpoint',
    courseCode: 'WEBSEC-101',
    type: 'quiz',
    title: '防御决策微测验',
    summary: '进入正式试卷前的三到五题判断练习，强调选择控制措施的理由。',
    knowledgePointIds: ['sql-injection', 'xss-reflected', 'csrf', 'auth-bypass', 'secure-coding'],
    learningGoals: ['在相似控制中选出主控制', '区分补充防护和根因修复', '识别需要回到讲义的薄弱点'],
    estimatedMinutes: 8,
    preview: {
      kind: 'checklist',
      items: ['数据库输入：是否有参数化查询和最小权限账号？', '页面输出：是否按输出上下文编码而非只过滤输入？', '状态变更：是否同时考虑 Token、Cookie 属性和来源校验？', '对象操作：是否在服务端按当前用户重新判定授权？'],
    },
    sourceUrl: 'https://owasp.org/www-project-top-ten/',
    author: 'SecureHub 课程内容组',
  },
  {
    ...resourceMetadata,
    id: 'res-lab-data-access',
    courseCode: 'WEBSEC-101',
    type: 'lab',
    title: '数据访问层防御性代码审查',
    summary: '围绕查询构造、错误处理、权限和回归测试完成一次安全代码审查。',
    knowledgePointIds: ['sql-injection', 'sql-injection-blind', 'secure-coding'],
    learningGoals: ['识别字符串拼接查询的风险', '选择参数化接口和最小权限数据库账户', '为修复补充可复现的回归检查'],
    estimatedMinutes: 28,
    preview: {
      kind: 'checklist',
      items: ['确认所有不可信值通过参数绑定传入查询。', '确认错误页面不暴露数据库实现细节和时延差异。', '确认数据库账户按业务动作最小授权。', '为合法输入、非法格式、权限拒绝和异常路径补充回归测试。'],
    },
    sourceUrl: 'https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html',
    author: 'OWASP Cheat Sheet Series',
  },
  {
    ...resourceMetadata,
    id: 'res-lab-service-boundaries',
    courseCode: 'WEBSEC-101',
    type: 'lab',
    title: '服务端边界审查任务',
    summary: '检查上传、远程 URL、对象解析、外部命令和对象级授权的防御控制。',
    knowledgePointIds: ['file-upload', 'ssrf', 'deserialization', 'rce', 'auth-bypass'],
    learningGoals: ['绘制服务端输入到执行的链路', '为每个高风险边界选择主控制', '补齐日志与失败路径的验证'],
    estimatedMinutes: 32,
    preview: {
      kind: 'checklist',
      items: ['上传对象是否存于 Web 根目录外并使用随机对象键？', '远程 URL 是否经 allowlist、DNS/IP 校验和出站隔离？', '是否拒绝反序列化不可信对象并使用简单数据格式？', '是否避免 shell，改用固定参数数组和超时？', '读取或修改资源前是否重新校验当前用户的对象级权限？'],
    },
    sourceUrl: 'https://portswigger.net/web-security/file-upload',
    author: 'PortSwigger Web Security Academy',
    licenseNote: '外部阅读仅以链接形式展示。',
  },
  {
    ...resourceMetadata,
    id: 'res-readings-owasp',
    courseCode: 'WEBSEC-101',
    type: 'readings',
    title: 'OWASP 与 Web Security Academy 精选阅读',
    summary: '把术语、推荐控制和实操验证锚定到可长期访问的公开学习资料。',
    knowledgePointIds: ['same-origin', 'file-upload', 'ssrf', 'deserialization', 'waf-bypass', 'secure-coding', 'owasp-top10'],
    learningGoals: ['从权威资料补全概念边界', '将课程结论映射到公开控制建议', '记录需要回到路线复习的主题'],
    estimatedMinutes: 20,
    preview: {
      kind: 'external_link',
      url: 'https://owasp.org/www-project-top-ten/',
      label: '查看 OWASP Top 10 公开页面',
    },
    sourceUrl: 'https://owasp.org/www-project-top-ten/',
    author: 'OWASP Foundation',
    licenseNote: '外部阅读仅以链接形式展示。',
  },
  {
    ...resourceMetadata,
    id: 'res-video-websec-overview',
    courseCode: 'WEBSEC-101',
    type: 'video',
    title: 'Web 安全公开视频目录',
    summary: '面向基础、代码审查和考前复盘的 Bilibili 公开视频入口；视频与封面均以原平台为准。',
    knowledgePointIds: ['http-basics', 'sql-injection', 'xss-reflected', 'csrf', 'auth-bypass', 'owasp-top10'],
    learningGoals: ['将视频片段与当前路线节点对应', '优先观看与薄弱点直接相关的内容', '通过外链在原平台继续学习'],
    estimatedMinutes: 16,
    preview: {
      kind: 'external_link',
      url: 'https://www.bilibili.com/video/BV1PyARzDEHA/',
      label: '在 Bilibili 查看课程视频',
    },
    videoId: 'video-bv1pyarzdeha',
    sourceUrl: 'https://www.bilibili.com/video/BV1PyARzDEHA/',
    author: 'Bilibili 公开视频目录',
    licenseNote: '仅提供原平台外链，不下载、转码或重传视频。',
  },
] as const;

export const webSecurityResourceById = Object.fromEntries(
  webSecurityResources.map((resource) => [resource.id, resource]),
) as Record<string, WebSecurityResource>;

export const webSecurityResourcesByType = WEB_SECURITY_RESOURCE_TYPES.reduce<Partial<Record<WebSecurityResource['type'], WebSecurityResource[]>>>(
  (resourcesByType, resourceType) => {
    resourcesByType[resourceType] = webSecurityResources.filter((resource) => resource.type === resourceType);
    return resourcesByType;
  },
  {},
);
