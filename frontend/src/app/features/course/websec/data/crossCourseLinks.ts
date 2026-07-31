// Status: real

export type CrossCourseCode = 'CRYPTO-101' | 'NET-SEC-201' | 'SDL-201';
export type CrossCourseLinkType = 'prerequisite' | 'application' | 'extension';

export interface CrossCourseNode {
  id: string;
  courseCode: CrossCourseCode;
  title: string;
  chapter: string;
  linkedWebSecKpIds: string[];
  linkType: CrossCourseLinkType;
}

export const crossCourseNodes: readonly CrossCourseNode[] = [
  {
    id: 'crypto:symmetric-encryption',
    courseCode: 'CRYPTO-101',
    title: '对称加密与 AES',
    chapter: '密码学基础',
    linkedWebSecKpIds: ['cookie-session'],
    linkType: 'prerequisite',
  },
  {
    id: 'crypto:hash-functions',
    courseCode: 'CRYPTO-101',
    title: '哈希函数与消息认证',
    chapter: '密码学基础',
    linkedWebSecKpIds: ['csrf', 'auth-bypass'],
    linkType: 'prerequisite',
  },
  {
    id: 'crypto:tls-handshake',
    courseCode: 'CRYPTO-101',
    title: 'TLS 握手与证书链',
    chapter: '传输层安全',
    linkedWebSecKpIds: ['http-basics', 'same-origin'],
    linkType: 'prerequisite',
  },
  {
    id: 'crypto:public-key',
    courseCode: 'CRYPTO-101',
    title: '公钥密码体系',
    chapter: '密码学基础',
    linkedWebSecKpIds: ['auth-bypass'],
    linkType: 'prerequisite',
  },
  {
    id: 'netsec:firewall-rules',
    courseCode: 'NET-SEC-201',
    title: '防火墙规则与 ACL',
    chapter: '网络边界防护',
    linkedWebSecKpIds: ['ssrf', 'waf-bypass'],
    linkType: 'application',
  },
  {
    id: 'netsec:ids-ips',
    courseCode: 'NET-SEC-201',
    title: '入侵检测与防御系统',
    chapter: '网络边界防护',
    linkedWebSecKpIds: ['waf-bypass', 'rce'],
    linkType: 'application',
  },
  {
    id: 'netsec:dns-security',
    courseCode: 'NET-SEC-201',
    title: 'DNS 安全与 DNSSEC',
    chapter: '基础协议安全',
    linkedWebSecKpIds: ['http-basics', 'ssrf'],
    linkType: 'extension',
  },
  {
    id: 'sdl:secure-sdlc',
    courseCode: 'SDL-201',
    title: '安全开发生命周期',
    chapter: '安全开发流程',
    linkedWebSecKpIds: ['secure-coding', 'owasp-top10'],
    linkType: 'extension',
  },
  {
    id: 'sdl:code-review',
    courseCode: 'SDL-201',
    title: '代码审计与自动化扫描',
    chapter: '安全开发流程',
    linkedWebSecKpIds: ['sql-injection', 'xss-reflected', 'rce'],
    linkType: 'extension',
  },
  {
    id: 'sdl:threat-modeling',
    courseCode: 'SDL-201',
    title: '威胁建模与 STRIDE',
    chapter: '安全设计',
    linkedWebSecKpIds: ['csrf', 'ssrf', 'deserialization'],
    linkType: 'extension',
  },
] as const;

export const crossCourseNodesByCourse = {
  'CRYPTO-101': crossCourseNodes.filter((node) => node.courseCode === 'CRYPTO-101'),
  'NET-SEC-201': crossCourseNodes.filter((node) => node.courseCode === 'NET-SEC-201'),
  'SDL-201': crossCourseNodes.filter((node) => node.courseCode === 'SDL-201'),
} satisfies Record<CrossCourseCode, readonly CrossCourseNode[]>;
