import type { CourseCatalogItem } from './courseCatalog.types';

/**
 * 学生进入「课程学习」时可选的课程目录。
 *
 * 课程数据是前端 mock，演示用；接入真后端时由 `/api/v1/courses` 替换。
 * 真后端字段对齐 `docs/api/course-contract.md §1.1`：`id` / `title` / `description` / `progress`。
 * 其余字段（难度、知识点、工作流模板、配色）仍由前端补充以撑起多课程演示。
 */
export const courseCatalog: CourseCatalogItem[] = [
  {
    id: 'web-security-foundation',
    title: 'Web 安全基础',
    subtitle: 'OWASP Top 10 与实操化讲解',
    description:
      'HTTP/HTTPS、Cookie/Session、SQL 注入、XSS、CSRF、文件上传、SSRF、SSTI 与反序列化等核心 Web 攻防知识，配套案例驱动的实操与练习题。',
    currentKnowledgePoint: 'SQL 注入基础',
    difficulty: '入门',
    estimatedHours: 18,
    progressPercent: 35,
    tags: ['Web 攻防', 'OWASP', '案例驱动'],
    coverTone: 'blue',
    defaultWorkflowId: 'course_learning',
  },
  {
    id: 'crypto-foundation',
    title: '密码学基础',
    subtitle: '从经典到现代密码学',
    description:
      '对称加密、非对称加密、哈希算法、消息认证码、TLS 握手以及常见误用案例，配套加解密小练习与协议握手时序图。',
    currentKnowledgePoint: '对称加密与哈希',
    difficulty: '进阶',
    estimatedHours: 22,
    progressPercent: 12,
    tags: ['密码学', '协议', 'TLS'],
    coverTone: 'violet',
    defaultWorkflowId: 'course_learning',
  },
  {
    id: 'network-attack-defense',
    title: '网络攻防实训',
    subtitle: '面向 CTF 与红蓝对抗的实战训练',
    description:
      '端口扫描与服务识别、漏洞利用、横向移动、隧道穿透与流量分析；强调实验报告复盘与攻防 trace 留痕。',
    currentKnowledgePoint: '端口扫描与服务识别',
    difficulty: '实战',
    estimatedHours: 28,
    progressPercent: 8,
    tags: ['CTF', '红蓝对抗', '流量分析'],
    coverTone: 'amber',
    defaultWorkflowId: 'tutor_routing',
  },
  {
    id: 'secure-development-audit',
    title: '安全开发与代码审计',
    subtitle: 'SDL、依赖治理与白盒审计',
    description:
      '输入校验、依赖风险、密钥管理、SDL 流程与 Java / Python / JavaScript 常见代码缺陷模式，配套审计 checklist 与可复用修复模板。',
    currentKnowledgePoint: '输入校验与依赖风险',
    difficulty: '挑战',
    estimatedHours: 24,
    progressPercent: 0,
    tags: ['SDL', '审计', '依赖治理'],
    coverTone: 'green',
    defaultWorkflowId: 'resource_generate',
  },
];

export const courseCatalogById = Object.fromEntries(
  courseCatalog.map((course) => [course.id, course]),
) as Record<string, CourseCatalogItem>;

/** 默认课程：保持第一门 Web 安全基础不变，前几轮演示数据全部围绕它构建。 */
export const defaultCourseId: CourseCatalogItem['id'] = courseCatalog[0].id;

export function getCourseById(courseId: string | null | undefined): CourseCatalogItem | undefined {
  if (!courseId) return undefined;
  return courseCatalogById[courseId];
}

export function resolveCourseId(courseId: string | null | undefined): string {
  return getCourseById(courseId)?.id ?? defaultCourseId;
}

export const courseCoverGradient: Record<CourseCatalogItem['coverTone'], string> = {
  blue: 'from-brand-blue-500/15 via-brand-blue-500/5 to-transparent',
  green: 'from-emerald-500/15 via-emerald-500/5 to-transparent',
  amber: 'from-amber-500/15 via-amber-500/5 to-transparent',
  slate: 'from-slate-400/15 via-slate-400/5 to-transparent',
  violet: 'from-violet-500/15 via-violet-500/5 to-transparent',
};

export const courseCoverAccent: Record<CourseCatalogItem['coverTone'], string> = {
  blue: 'text-brand-blue-700',
  green: 'text-emerald-700',
  amber: 'text-amber-700',
  slate: 'text-slate-700',
  violet: 'text-violet-700',
};

export const courseDifficultyTone: Record<CourseCatalogItem['difficulty'], string> = {
  入门: 'bg-emerald-50 text-emerald-700',
  进阶: 'bg-brand-blue-50 text-brand-blue-700',
  实战: 'bg-amber-50 text-amber-700',
  挑战: 'bg-rose-50 text-rose-700',
};
