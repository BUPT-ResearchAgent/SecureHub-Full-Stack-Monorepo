import type { EducationalMediaAsset } from './educationalMedia.types';

const IMAGE_ROOT = '/assets/websec/generated/images';
const VIDEO_ROOT = '/assets/websec/generated/videos';

const curatedImageDefaults = {
  kind: 'image',
  source: 'curated',
  provider: 'openai-imagegen',
  model: 'Codex built-in image generation',
  updatedAt: '2026-07-31',
  dimensions: '1672 × 941',
} as const;

const curatedVideoDefaults = {
  kind: 'video',
  source: 'curated',
  provider: 'securehub-motion-diagram',
  model: 'canvas-motion-v1',
  updatedAt: '2026-07-31',
  dimensions: '1280 × 720',
  durationSeconds: 6.2,
} as const;

export const webSecurityEducationalMedia: readonly EducationalMediaAsset[] = [
  {
    ...curatedImageDefaults,
    id: 'websec-image-http-request-response',
    knowledgePointIds: ['http-basics'],
    title: 'HTTP 请求与响应',
    description: '把请求行、请求头、请求体与状态码、响应头、响应体放回同一条时序线上。',
    learningFocus: '辨认 HTTP 无状态边界，并理解每次请求都要重新经过安全校验。',
    src: `${IMAGE_ROOT}/http-request-response.png`,
    alt: 'HTTP 请求与响应时序图',
    promptSummary: '浏览器、网络边界与 Web 服务之间的请求—响应方向。',
  },
  {
    ...curatedImageDefaults,
    id: 'websec-image-same-origin-cors',
    knowledgePointIds: ['same-origin'],
    title: '同源策略与 CORS',
    description: '用协议、主机、端口三元组判断同源，再观察跨源预检与服务端授权。',
    learningFocus: 'CORS 是服务端授权、浏览器执行，不等于关闭同源策略。',
    src: `${IMAGE_ROOT}/same-origin-cors.png`,
    alt: '同源策略、CORS 预检与浏览器拦截示意图',
    promptSummary: '三元组判定尺、浏览器策略屏障和预检授权路径。',
  },
  {
    ...curatedImageDefaults,
    id: 'websec-image-cookie-session',
    knowledgePointIds: ['cookie-session'],
    title: 'Cookie 与 Session',
    description: '五步拆解登录、会话创建、Cookie 保存、自动携带与服务端校验。',
    learningFocus: '浏览器只保存会话标识，完整会话数据留在服务端。',
    src: `${IMAGE_ROOT}/cookie-session.png`,
    alt: 'Cookie 与 Session 五步交互时序图',
    promptSummary: 'Cookie 安全属性与服务端会话校验的职责分离。',
  },
  {
    ...curatedImageDefaults,
    id: 'websec-image-sql-injection',
    knowledgePointIds: ['sql-injection', 'sql-injection-blind'],
    title: 'SQL 注入与参数化查询',
    description: '左右对照字符串拼接污染查询结构，与 SQL 模板、参数绑定分离数据。',
    learningFocus: '参数化查询的核心不是过滤字符，而是让代码与数据不可混淆。',
    src: `${IMAGE_ROOT}/sql-injection-parameterized-query.png`,
    alt: 'SQL 字符串拼接与参数化查询防御对照图',
    promptSummary: '红色拼接链与蓝绿色参数绑定链。',
  },
  {
    ...curatedImageDefaults,
    id: 'websec-image-xss-reflected',
    knowledgePointIds: ['xss-reflected', 'xss-stored', 'xss-dom'],
    title: '反射型 XSS 与输出编码',
    description: '追踪不可信输入被浏览器解释的路径，并区分 HTML、属性、脚本上下文。',
    learningFocus: '输出编码必须匹配具体上下文，CSP 是纵深防御而非替代品。',
    src: `${IMAGE_ROOT}/xss-reflected-output-encoding.png`,
    alt: '反射型 XSS 攻击链与上下文输出编码防御图',
    promptSummary: '反射链、上下文矩阵、输出编码与 CSP。',
  },
  {
    ...curatedImageDefaults,
    id: 'websec-image-csrf',
    knowledgePointIds: ['csrf'],
    title: 'CSRF 与请求真实性',
    description: '展示跨站请求为何会自动携带 Cookie，以及服务端如何确认用户意图。',
    learningFocus: 'CSRF Token、SameSite 和来源校验共同建立请求真实性。',
    src: `${IMAGE_ROOT}/csrf-request-authenticity.png`,
    alt: 'CSRF 三方时序与三道真实性验证防线',
    promptSummary: '恶意站点、受害者浏览器、目标服务之间的请求路径。',
  },
  {
    ...curatedImageDefaults,
    id: 'websec-image-file-upload',
    knowledgePointIds: ['file-upload'],
    title: '文件上传安全流水线',
    description: '从大小、类型、签名、命名、扫描到隔离存储逐级验收上传文件。',
    learningFocus: '扩展名只是初筛，真实类型与文件签名必须独立校验。',
    src: `${IMAGE_ROOT}/file-upload-pipeline.png`,
    alt: '文件上传七级安全检查流水线',
    promptSummary: '七级检查站与类型伪装、危险内容拒绝路径。',
  },
  {
    ...curatedImageDefaults,
    id: 'websec-image-ssrf',
    knowledgePointIds: ['ssrf'],
    title: 'SSRF 与出站访问控制',
    description: '阻断环回、内网、云元数据路径，仅允许校验后的公网目标通过出站代理。',
    learningFocus: '连接前再次做 DNS 与地址段校验，防止 DNS 重绑定。',
    src: `${IMAGE_ROOT}/ssrf-egress-control.png`,
    alt: 'SSRF 私网阻断与出站访问控制架构图',
    promptSummary: '私网阻断、DNS 复核、地址段校验和统一出站。',
  },
  {
    ...curatedVideoDefaults,
    id: 'websec-video-http-lifecycle',
    knowledgePointIds: ['http-basics'],
    title: 'HTTP 请求生命周期',
    description: '6 秒静音动画，逐步点亮请求边界、安全校验、业务处理与可信响应。',
    learningFocus: '每一次请求，都要重新经过边界校验。',
    src: `${VIDEO_ROOT}/http-request-lifecycle.mp4`,
    poster: `${IMAGE_ROOT}/http-request-response.png`,
    alt: 'HTTP 请求生命周期精选教学动画',
    promptSummary: '浏览器到可信响应的五阶段动态图。',
  },
  {
    ...curatedVideoDefaults,
    id: 'websec-video-xss-defense',
    knowledgePointIds: ['xss-reflected', 'xss-stored', 'xss-dom'],
    title: 'XSS 分层防御链',
    description: '6 秒静音动画，展示不可信输入如何经输出编码与 CSP 变为安全文本。',
    learningFocus: '让输入保持为数据，阻断直接写入危险 DOM 接口的旁路。',
    src: `${VIDEO_ROOT}/xss-defense-chain.mp4`,
    poster: `${IMAGE_ROOT}/xss-reflected-output-encoding.png`,
    alt: 'XSS 分层防御链精选教学动画',
    promptSummary: '数据处理、上下文编码、CSP 与文本呈现。',
  },
  {
    ...curatedVideoDefaults,
    id: 'websec-video-ssrf-egress',
    knowledgePointIds: ['ssrf'],
    title: 'SSRF 出站控制',
    description: '6 秒静音动画，演示协议域名白名单、DNS 复核与统一出站代理。',
    learningFocus: '只放行校验后的公网目标，内网与元数据旁路在边界终止。',
    src: `${VIDEO_ROOT}/ssrf-egress-guard.mp4`,
    poster: `${IMAGE_ROOT}/ssrf-egress-control.png`,
    alt: 'SSRF 出站控制精选教学动画',
    promptSummary: '从用户 URL 到受控公网访问的动态路径。',
  },
];

export function educationalMediaForKnowledgePoint(
  knowledgePointId: string,
): EducationalMediaAsset[] {
  return webSecurityEducationalMedia.filter((asset) => (
    asset.knowledgePointIds.includes(knowledgePointId)
  ));
}
