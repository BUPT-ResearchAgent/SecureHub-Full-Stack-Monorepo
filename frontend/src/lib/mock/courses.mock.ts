// Status: mock
//
// 4-B-1：把课程演示数据从「只有 SQL 注入」扩展到 4 门课，
// 让评委切换课程时能看到不同主题的 evidence / 知识点 / 资源生成回放。
//
// 引用注意：所有 platform / source_url / author / rights_note 字段都按
// CLAUDE.md §2.1 多源合规要求填实；mock 也要保持这个口径，演示时不能掉。

import type { EvidenceChunkDTO } from '@/lib/sse.types';

export type CourseMockEvidence = EvidenceChunkDTO[];
export type CourseMockKpNode = { id: string; title: string; status: 'active' | 'ready' | 'locked' };

const websecEvidence: CourseMockEvidence = [
  {
    chunk_id: 'web-001',
    document_id: 'web-doc-001',
    source_url: 'https://owasp.org/www-community/attacks/SQL_Injection',
    platform: 'owasp',
    author: 'OWASP',
    published_at: null,
    fetched_at: '2026-06-09T00:00:00Z',
    rights_note: 'CC BY-SA 4.0',
    asset_type: 'web_article',
    chunk_text: 'SQL 注入通常发生在未受信任输入被拼接进查询语句时，攻击者可能读取或篡改数据库内容。',
    page_no: null,
    chapter: 'SQL 注入基础',
    timestamp: null,
    reliability: 0.92,
    collection_mode: 'scrapling',
    score: 0.85,
  },
  {
    chunk_id: 'web-002',
    document_id: 'web-doc-002',
    source_url: 'https://portswigger.net/web-security/sql-injection',
    platform: 'portswigger',
    author: 'PortSwigger Web Security Academy',
    published_at: null,
    fetched_at: '2026-06-09T00:00:00Z',
    rights_note: 'PortSwigger Academy 内容用于学习引用，保留原站链接',
    asset_type: 'web_article',
    chunk_text: '参数化查询会把用户输入作为数据绑定，避免输入内容被数据库解释为 SQL 语法片段。',
    page_no: null,
    chapter: '防御与参数化查询',
    timestamp: null,
    reliability: 0.9,
    collection_mode: 'scrapling',
    score: 0.85,
  },
  {
    chunk_id: 'web-003',
    document_id: 'web-doc-003',
    source_url: 'https://www.bilibili.com/video/BV1sql_demo',
    platform: 'bili',
    author: '网安教学演示账号',
    published_at: '2025-11-18T00:00:00Z',
    fetched_at: '2026-06-09T00:00:00Z',
    rights_note: '仅引用视频转写片段用于课堂演示，不搬运原视频',
    asset_type: 'video_transcript',
    chunk_text: '演示环境中先判断注入点，再用报错、布尔或时间盲注确认查询结构，最后说明修复方式。',
    page_no: null,
    chapter: 'SQL 注入演示转写',
    timestamp: 183,
    reliability: 0.78,
    collection_mode: 'mediacrawler',
    score: 0.82,
  },
];

const cryptoEvidence: CourseMockEvidence = [
  {
    chunk_id: 'crypto-001',
    document_id: 'crypto-doc-001',
    source_url: 'https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.180-4.pdf',
    platform: 'nist',
    author: 'NIST',
    published_at: '2015-08-01T00:00:00Z',
    fetched_at: '2026-06-10T00:00:00Z',
    rights_note: 'NIST 公开技术标准，引用需注明 FIPS 180-4',
    asset_type: 'pdf',
    chunk_text: 'SHA-2 系列输出长度固定，单向哈希不可逆，适合做完整性校验但不适合直接存储用户密码。',
    page_no: 5,
    chapter: '哈希算法基础',
    timestamp: null,
    reliability: 0.95,
    collection_mode: 'manual',
    score: 0.80,
  },
  {
    chunk_id: 'crypto-002',
    document_id: 'crypto-doc-002',
    source_url: 'https://owasp.org/www-project-cheat-sheets/cheatsheets/Password_Storage_Cheat_Sheet.html',
    platform: 'owasp',
    author: 'OWASP Cheat Sheet Series',
    published_at: null,
    fetched_at: '2026-06-10T00:00:00Z',
    rights_note: 'CC BY-SA 4.0',
    asset_type: 'web_article',
    chunk_text: '用户密码应当使用 bcrypt / argon2 等带 salt 的慢哈希；直接使用 MD5 / SHA-1 是已知误用。',
    page_no: null,
    chapter: '密钥与密码管理',
    timestamp: null,
    reliability: 0.9,
    collection_mode: 'scrapling',
    score: 0.85,
  },
  {
    chunk_id: 'crypto-003',
    document_id: 'crypto-doc-003',
    source_url: 'https://www.zhihu.com/question/aes-gcm-vs-aes-cbc',
    platform: 'zhihu',
    author: '密码学讨论账号',
    published_at: '2025-10-12T00:00:00Z',
    fetched_at: '2026-06-10T00:00:00Z',
    rights_note: '仅引用平台讨论摘要，作为补充阅读',
    asset_type: 'forum_post',
    chunk_text: 'AES-GCM 自带认证标签，比 AES-CBC + HMAC 更不容易写错；高并发场景下注意 nonce 唯一性。',
    page_no: null,
    chapter: 'AES 模式选择',
    timestamp: null,
    reliability: 0.72,
    collection_mode: 'mediacrawler',
    score: 0.82,
  },
];

const networkEvidence: CourseMockEvidence = [
  {
    chunk_id: 'net-001',
    document_id: 'net-doc-001',
    source_url: 'https://nmap.org/book/man-port-scanning-techniques.html',
    platform: 'nmap',
    author: 'Nmap Project',
    published_at: null,
    fetched_at: '2026-06-10T00:00:00Z',
    rights_note: 'GPLv2，引用作为教学说明',
    asset_type: 'web_article',
    chunk_text: '主动扫描的 TCP SYN 半连接最常用；UDP 扫描需要结合服务指纹和差速重试。',
    page_no: null,
    chapter: '端口扫描技术',
    timestamp: null,
    reliability: 0.93,
    collection_mode: 'scrapling',
    score: 0.85,
  },
  {
    chunk_id: 'net-002',
    document_id: 'net-doc-002',
    source_url: 'https://attack.mitre.org/tactics/TA0007/',
    platform: 'mitre',
    author: 'MITRE ATT&CK',
    published_at: null,
    fetched_at: '2026-06-10T00:00:00Z',
    rights_note: 'MITRE ATT&CK CC BY 4.0',
    asset_type: 'web_article',
    chunk_text: 'Discovery 阶段的服务识别需要关注误判：banner 伪装、honeypot、CDN 边缘会改变指纹。',
    page_no: null,
    chapter: '攻击链 Discovery 阶段',
    timestamp: null,
    reliability: 0.94,
    collection_mode: 'scrapling',
    score: 0.85,
  },
  {
    chunk_id: 'net-003',
    document_id: 'net-doc-003',
    source_url: 'https://space.bilibili.com/ctf-replay',
    platform: 'bili',
    author: 'CTF 复盘频道',
    published_at: '2026-02-08T00:00:00Z',
    fetched_at: '2026-06-10T00:00:00Z',
    rights_note: '引用赛后复盘视频转写片段，不搬运原视频',
    asset_type: 'video_transcript',
    chunk_text: '比赛中 nmap 服务识别误判把 MySQL 当成 PostgreSQL，应当再用 nmap -sV --version-all 复核。',
    page_no: null,
    chapter: 'CTF 服务识别复盘',
    timestamp: 412,
    reliability: 0.74,
    collection_mode: 'mediacrawler',
    score: 0.82,
  },
];

const sdlEvidence: CourseMockEvidence = [
  {
    chunk_id: 'sdl-001',
    document_id: 'sdl-doc-001',
    source_url: 'https://owasp.org/www-project-proactive-controls/',
    platform: 'owasp',
    author: 'OWASP Proactive Controls',
    published_at: null,
    fetched_at: '2026-06-10T00:00:00Z',
    rights_note: 'CC BY-SA 4.0',
    asset_type: 'web_article',
    chunk_text: '输入校验应当采用白名单：明确允许的字符集、长度与编码，再决定其它字段如何放行。',
    page_no: null,
    chapter: 'C5 校验输入',
    timestamp: null,
    reliability: 0.93,
    collection_mode: 'scrapling',
    score: 0.85,
  },
  {
    chunk_id: 'sdl-002',
    document_id: 'sdl-doc-002',
    source_url: 'https://www.cisa.gov/sbom',
    platform: 'cisa',
    author: 'CISA',
    published_at: '2025-09-15T00:00:00Z',
    fetched_at: '2026-06-10T00:00:00Z',
    rights_note: 'U.S. Government Work，引用注明来源',
    asset_type: 'web_article',
    chunk_text: 'SBOM 至少需要包含组件名称、版本、唯一标识、依赖关系与作者，便于供应链漏洞响应。',
    page_no: null,
    chapter: 'SBOM 字段最小集',
    timestamp: null,
    reliability: 0.91,
    collection_mode: 'scrapling',
    score: 0.85,
  },
  {
    chunk_id: 'sdl-003',
    document_id: 'sdl-doc-003',
    source_url: 'https://github.com/securehub-demo/code-audit-checklist',
    platform: 'github',
    author: 'SecureHub Demo',
    published_at: '2026-04-22T00:00:00Z',
    fetched_at: '2026-06-10T00:00:00Z',
    rights_note: 'MIT，仅用于演示引用',
    asset_type: 'repo_doc',
    chunk_text: 'Java 反序列化审计检查项：禁止 ObjectInputStream 直读外部输入，开启 JEP 290 过滤器，记录类白名单。',
    page_no: null,
    chapter: 'Java 反序列化 checklist',
    timestamp: null,
    reliability: 0.83,
    collection_mode: 'scrapling',
    score: 0.85,
  },
];

export const evidenceByCourse: Record<string, CourseMockEvidence> = {
  'web-security-foundation': websecEvidence,
  'crypto-foundation': cryptoEvidence,
  'network-attack-defense': networkEvidence,
  'secure-development-audit': sdlEvidence,
};

export const knowledgeNodesByCourse: Record<string, CourseMockKpNode[]> = {
  'web-security-foundation': [
    { id: 'sql_injection', title: 'SQL 注入基础', status: 'active' },
    { id: 'xss', title: 'XSS 跨站脚本', status: 'ready' },
    { id: 'csrf', title: 'CSRF 请求伪造', status: 'ready' },
    { id: 'upload', title: '文件上传风险', status: 'locked' },
    { id: 'ssrf', title: 'SSRF 服务端请求伪造', status: 'locked' },
  ],
  'crypto-foundation': [
    { id: 'symmetric', title: '对称加密与分组模式', status: 'active' },
    { id: 'hash', title: '哈希与 HMAC', status: 'ready' },
    { id: 'asymmetric', title: '非对称加密与签名', status: 'ready' },
    { id: 'tls', title: 'TLS 握手与会话', status: 'locked' },
    { id: 'misuse', title: '常见密码学误用', status: 'locked' },
  ],
  'network-attack-defense': [
    { id: 'port_scan', title: '端口扫描与服务识别', status: 'active' },
    { id: 'vuln_probe', title: '漏洞探测与利用', status: 'ready' },
    { id: 'privesc', title: '提权与持久化', status: 'ready' },
    { id: 'lateral', title: '横向移动与隧道', status: 'locked' },
    { id: 'traffic', title: '流量分析与复盘', status: 'locked' },
  ],
  'secure-development-audit': [
    { id: 'input_validation', title: '输入校验与白名单', status: 'active' },
    { id: 'dep_audit', title: '依赖审计与 CI 拦截', status: 'ready' },
    { id: 'secret_mgmt', title: '密钥管理与最小权限', status: 'ready' },
    { id: 'code_audit', title: '代码审计 checklist', status: 'locked' },
    { id: 'sbom', title: 'SBOM 与供应链响应', status: 'locked' },
  ],
};

export type CourseMockQuiz = {
  id: string;
  prompt: string;
  options: string[];
  answer: string;
  kp: string;
};

export const quizItemsByCourse: Record<string, CourseMockQuiz[]> = {
  'web-security-foundation': [
    {
      id: 'web-q1',
      prompt: '参数化查询如何抵御 SQL 注入？',
      options: ['把用户输入作为数据绑定', '只允许特定 IP 访问', '把数据库日志关掉'],
      answer: '把用户输入作为数据绑定',
      kp: 'SQL 注入基础',
    },
    {
      id: 'web-q2',
      prompt: '反射型 XSS 与存储型 XSS 的关键区别？',
      options: ['payload 是否被服务端持久化', '使用的浏览器内核不同', '只能在登录后触发'],
      answer: 'payload 是否被服务端持久化',
      kp: 'XSS 跨站脚本',
    },
    {
      id: 'web-q3',
      prompt: 'CSRF 防御常用做法是？',
      options: ['校验同源 token 或 SameSite Cookie', '禁用全部表单', '用 GET 提交表单'],
      answer: '校验同源 token 或 SameSite Cookie',
      kp: 'CSRF 请求伪造',
    },
  ],
  'crypto-foundation': [
    {
      id: 'crypto-q1',
      prompt: '为什么不要直接用 MD5 存储用户密码？',
      options: ['速度太快易被彩虹表 / GPU 枚举', '需要额外购买授权', '只能哈希 8 位字符串'],
      answer: '速度太快易被彩虹表 / GPU 枚举',
      kp: '哈希与 HMAC',
    },
    {
      id: 'crypto-q2',
      prompt: 'AES-GCM 相比 AES-CBC + HMAC 的优势？',
      options: ['内建认证 + 抗篡改更难写错', '密文体积更小', '可以省去密钥'],
      answer: '内建认证 + 抗篡改更难写错',
      kp: '对称加密与分组模式',
    },
    {
      id: 'crypto-q3',
      prompt: 'TLS 握手最关键的安全属性是？',
      options: ['密钥协商与身份认证', '让所有人都能解密流量', '加快页面加载'],
      answer: '密钥协商与身份认证',
      kp: 'TLS 握手与会话',
    },
  ],
  'network-attack-defense': [
    {
      id: 'net-q1',
      prompt: 'TCP SYN 扫描相比全连接扫描的特点？',
      options: ['不完成三次握手，留痕更少', '只能用于内网', '默认携带 payload'],
      answer: '不完成三次握手，留痕更少',
      kp: '端口扫描与服务识别',
    },
    {
      id: 'net-q2',
      prompt: '服务指纹误判最常见原因？',
      options: ['banner 伪装或代理重写', '操作系统升级', '使用 IPv6'],
      answer: 'banner 伪装或代理重写',
      kp: '端口扫描与服务识别',
    },
    {
      id: 'net-q3',
      prompt: '复盘报告必含的合规项是？',
      options: ['授权范围 + 数据脱敏说明', '所有原始日志全量公开', '攻击者真实身份调查'],
      answer: '授权范围 + 数据脱敏说明',
      kp: '流量分析与复盘',
    },
  ],
  'secure-development-audit': [
    {
      id: 'sdl-q1',
      prompt: '输入校验最稳妥的策略是？',
      options: ['白名单允许的字符集 + 长度', '把所有输入直接传给数据库', '改用更长密码'],
      answer: '白名单允许的字符集 + 长度',
      kp: '输入校验与白名单',
    },
    {
      id: 'sdl-q2',
      prompt: 'CI 中拦截已知依赖漏洞通常使用？',
      options: ['Dependency-Check / OSV-Scanner 等 SCA 工具', '把所有依赖删掉', '人工 review 全部 commit'],
      answer: 'Dependency-Check / OSV-Scanner 等 SCA 工具',
      kp: '依赖审计与 CI 拦截',
    },
    {
      id: 'sdl-q3',
      prompt: 'SBOM 最少应该包含的字段？',
      options: ['组件名 / 版本 / 唯一标识 / 依赖关系 / 作者', '只有作者邮箱', '只有依赖名称'],
      answer: '组件名 / 版本 / 唯一标识 / 依赖关系 / 作者',
      kp: 'SBOM 与供应链响应',
    },
  ],
};

export function getMockEvidenceForCourse(courseId: string | undefined | null): CourseMockEvidence {
  if (!courseId) return evidenceByCourse['web-security-foundation'];
  return evidenceByCourse[courseId] ?? evidenceByCourse['web-security-foundation'];
}

export function getMockKnowledgeNodesForCourse(courseId: string | undefined | null) {
  if (!courseId) return knowledgeNodesByCourse['web-security-foundation'];
  return knowledgeNodesByCourse[courseId] ?? knowledgeNodesByCourse['web-security-foundation'];
}

export function getMockQuizItemsForCourse(courseId: string | undefined | null): CourseMockQuiz[] {
  if (!courseId) return quizItemsByCourse['web-security-foundation'];
  return quizItemsByCourse[courseId] ?? quizItemsByCourse['web-security-foundation'];
}
