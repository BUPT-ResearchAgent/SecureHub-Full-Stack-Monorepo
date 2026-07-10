// Status: mock
// 资源生成产品化升级 mock：剧本台词 / 三变体 / 智能体辩论 / 溯源时间轴 / 版本 diff / 监督流 / 种子提示。
// 所有函数纯函数化：(resourceType | userContext) → 数据。

import type { ResourceType } from '@/lib/sse.types';
import { mockEvidenceChunks } from './evidence.mock';
import type {
  AgentDebate,
  ResourceReplayTimeline,
  ResourceScreenplay,
  ResourceSupervisionEntry,
  ResourceTeacherSeedPrompt,
  ResourceVariant,
  ResourceVersion,
  ScreenplayCue,
} from '@/lib/types/resource-variant.types';

const agentMeta: Record<string, { name: string; avatar: string }> = {
  career_planner: { name: '画像规划员', avatar: '🎯' },
  task_orchestrator: { name: '任务编排员', avatar: '🧭' },
  doc_archivist: { name: '资料编辑员', avatar: '📚' },
  topic_explorer: { name: '专题探索员', avatar: '🧪' },
  competition_advisor: { name: '竞赛参谋员', avatar: '🏆' },
  outcome_evaluator: { name: '成果评估员', avatar: '🛡️' },
  policy_interpreter: { name: '政策解读员', avatar: '📜' },
  hot_analyst: { name: '热点分析员', avatar: '🔥' },
  job_analyst: { name: '岗位分析员', avatar: '💼' },
};

function cue(actAt: number, agentId: string, line: string, durationMs = 3000): ScreenplayCue {
  const meta = agentMeta[agentId] ?? { name: agentId, avatar: '🤖' };
  return {
    id: `cue-${agentId}-${actAt}`,
    actAt,
    agentId,
    agentName: meta.name,
    avatar: meta.avatar,
    line,
    durationMs,
  };
}

const screenplayLibrary: Record<ResourceType, ResourceScreenplay> = {
  doc: {
    title: '为小李定制 SQL 注入入门讲解 · 第 1 幕',
    subtitle: '案例驱动 · 60 分钟可读',
    resourceType: 'doc',
    totalActs: 6,
    cues: [
      cue(0, 'career_planner', '已接到小李的请求，正在分析画像：偏好案例驱动，对盲注薄弱…'),
      cue(2, 'task_orchestrator', '基于知识图谱拆解 5 个学习节点：判别 → 探测 → 利用 → 修复 → 验证。'),
      cue(4, 'doc_archivist', '已检索 OWASP / PortSwigger 文献 3 条，正在撰写讲解第一段…'),
      cue(7, 'outcome_evaluator', '检测到第一段缺少真实漏洞案例，请补充。'),
      cue(9, 'doc_archivist', '收到，已补充 DVWA SQL 注入靶场示例及 SQLMap 命令片段。'),
      cue(11, 'outcome_evaluator', '质量评分 0.87，通过。文档已写入 generated_resources。'),
    ],
  },
  ppt: {
    title: 'SQL 注入精讲 · PPT 编排剧本',
    subtitle: '6 章 · 18 张 · 教学留白',
    resourceType: 'ppt',
    totalActs: 5,
    cues: [
      cue(0, 'task_orchestrator', '本次以 6 章框架展开：威胁面 → 风险点 → 攻击链 → 防御链 → 复盘 → 评估。'),
      cue(2, 'doc_archivist', '基于讲解文档抽取要点，每章 3 张幻灯片，留白处插入互动提问。'),
      cue(5, 'topic_explorer', '互动提问模板已就位：在第 8 张插入"判断这是哪类盲注"。'),
      cue(8, 'outcome_evaluator', '检查留白比例 24%，符合 A3 教学留白要求。'),
    ],
  },
  mindmap: {
    title: 'SQL 注入知识图谱 · 节点扩展剧本',
    subtitle: '3 层 · 18 节点',
    resourceType: 'mindmap',
    totalActs: 4,
    cues: [
      cue(0, 'topic_explorer', '从根节点 SQL 注入开始，按攻击类型 / 探测方法 / 防御措施 / 工具链分支。'),
      cue(3, 'doc_archivist', '每个叶子节点附上 1-2 条文献引用。'),
      cue(6, 'outcome_evaluator', '总节点数 18，覆盖率达 A3 标准。'),
    ],
  },
  quiz: {
    title: 'SQL 注入 5 题精选 · 题目设计剧本',
    subtitle: '3 单选 + 1 多选 + 1 代码题',
    resourceType: 'quiz',
    totalActs: 5,
    cues: [
      cue(0, 'competition_advisor', '本次以入门难度为主，引用 NSACTF 历届真题做参考。'),
      cue(3, 'doc_archivist', '已挑选 3 道真题模板进行改写。'),
      cue(6, 'outcome_evaluator', '答案对照证据，第 2 题二阶注入选项需要替换。'),
      cue(9, 'competition_advisor', '已替换为更准确的二阶注入触发场景。'),
    ],
  },
  lab: {
    title: 'SQL 注入实战靶场 · 任务设计剧本',
    subtitle: 'DVWA Low + Medium 三关',
    resourceType: 'lab',
    totalActs: 4,
    cues: [
      cue(0, 'topic_explorer', '本靶场基于 DVWA，第 1 关回显注入，第 2 关盲注，第 3 关修复后绕过。'),
      cue(3, 'task_orchestrator', '每关附带 hint 和评分点，学生需提交 payload。'),
      cue(6, 'outcome_evaluator', '通过质量检查。'),
    ],
  },
  video: {
    title: 'SQL 注入 5 分钟讲解 · 视频脚本',
    subtitle: '案例驱动 · 字幕分段',
    resourceType: 'video',
    totalActs: 4,
    cues: [
      cue(0, 'doc_archivist', '从一个真实 CVE 案例切入，5 段，每段 60 秒。'),
      cue(3, 'topic_explorer', '配套动画脚本：先页面演示，再代码透视。'),
      cue(6, 'outcome_evaluator', '字幕引用文献 3 处，引用完整。'),
    ],
  },
  readings: {
    title: '延伸阅读清单 · 资源策展剧本',
    subtitle: 'OWASP / PortSwigger / GitHub 案例',
    resourceType: 'readings',
    totalActs: 3,
    cues: [
      cue(0, 'hot_analyst', '检索最近 30 天讨论度最高的 SQL 注入文章 5 篇。'),
      cue(3, 'doc_archivist', '每篇配 30 字摘要，标注权威度。'),
    ],
  },
};

export function getScreenplay(resourceType: ResourceType): ResourceScreenplay {
  return screenplayLibrary[resourceType];
}

const variantTemplates: Record<ResourceType, ResourceVariant[]> = {
  doc: [
    {
      id: 'variant-doc-deep',
      resourceType: 'doc',
      kind: 'deep',
      title: '《SQL 注入入门》· 深入版',
      tagline: '原理 + 源码 + 案例',
      description: '从 SQL 解析层切入，覆盖 union/boolean/time-based 三类注入，配套 SQLMap 源码片段与 DVWA 实操。',
      estimateMinutes: 25,
      highlights: ['SQL 语法解析视角', 'SQLMap 关键源码', '修复方案前后对比'],
      preferredFor: ['理论推演', '基础扎实', '深度学习'],
      content: '# SQL 注入入门 · 深入版\n\n## 1. SQL 解析层视角\n\n...',
      evidenceRefs: mockEvidenceChunks,
    },
    {
      id: 'variant-doc-easy',
      resourceType: 'doc',
      kind: 'easy',
      title: '《SQL 注入入门》· 图解版',
      tagline: '图解 + 类比 + 一图掌握',
      description: '用"邮筒类比"理解参数化查询，所有概念配图解，无源码。',
      estimateMinutes: 12,
      highlights: ['一图理解注入', '生活化类比', '零代码门槛'],
      preferredFor: ['初学者', '案例驱动', '快速入门'],
      content: '# SQL 注入入门 · 图解版\n\n## 邮筒类比\n\n...',
      evidenceRefs: mockEvidenceChunks.slice(0, 2),
    },
    {
      id: 'variant-doc-case',
      resourceType: 'doc',
      kind: 'case',
      title: '《SQL 注入入门》· 案例版',
      tagline: '真实漏洞 + 复现步骤',
      description: '直接给出 4 个真实 CVE，每个配 5 分钟复现步骤；从攻击者视角讲。',
      estimateMinutes: 18,
      highlights: ['4 个真实 CVE', '5 分钟复现', '攻击者视角'],
      preferredFor: ['实战导向', '红队意向', '靶场练手'],
      content: '# SQL 注入入门 · 案例版\n\n## CVE-2023-XXXXX：登录绕过\n\n...',
      evidenceRefs: mockEvidenceChunks,
    },
  ],
  ppt: [
    {
      id: 'variant-ppt-deep',
      resourceType: 'ppt',
      kind: 'deep',
      title: 'SQL 注入精讲 · 课堂版',
      tagline: '18 张 · 含留白',
      description: '6 章框架，每章 3 张，含教师讲授留白与互动提问。',
      estimateMinutes: 45,
      highlights: ['6 章框架', '互动提问插页', '教学留白 24%'],
      preferredFor: ['课堂教学', '理论体系'],
      content: 'PPT 章节: 威胁面 / 风险点 / 攻击链 / 防御链 / 复盘 / 评估',
      evidenceRefs: mockEvidenceChunks,
    },
    {
      id: 'variant-ppt-easy',
      resourceType: 'ppt',
      kind: 'easy',
      title: 'SQL 注入精讲 · 自习版',
      tagline: '12 张 · 重点突出',
      description: '精简版，去掉互动留白，纯讲解，适合学生自学。',
      estimateMinutes: 20,
      highlights: ['12 张精简', '一页一概念'],
      preferredFor: ['自习', '复习'],
      content: 'PPT 章节: 5 类风险 + 5 类防御',
      evidenceRefs: mockEvidenceChunks.slice(0, 2),
    },
    {
      id: 'variant-ppt-case',
      resourceType: 'ppt',
      kind: 'case',
      title: 'SQL 注入精讲 · 案例版',
      tagline: '4 个真实漏洞 · 直击攻击链',
      description: '4 个真实 CVE 配截图与复现，重点呈现攻击链动效。',
      estimateMinutes: 25,
      highlights: ['真实截图', '攻击链动效'],
      preferredFor: ['实战导向'],
      content: 'PPT 章节: 4 个 CVE 案例 + 1 个综合复盘',
      evidenceRefs: mockEvidenceChunks,
    },
  ],
  mindmap: [
    {
      id: 'variant-mindmap-deep',
      resourceType: 'mindmap',
      kind: 'deep',
      title: 'SQL 注入知识图谱 · 完整版',
      tagline: '3 层 · 18 节点',
      description: '从根节点向下展开三层，覆盖攻击类型、探测方法、防御措施、工具链。',
      estimateMinutes: 10,
      highlights: ['18 节点', '3 层结构'],
      preferredFor: ['理论梳理'],
      content: '根节点: SQL 注入 → 类型 / 探测 / 防御 / 工具',
      evidenceRefs: mockEvidenceChunks,
    },
    {
      id: 'variant-mindmap-easy',
      resourceType: 'mindmap',
      kind: 'easy',
      title: 'SQL 注入知识图谱 · 精简版',
      tagline: '2 层 · 8 节点',
      description: '只保留核心节点，适合快速预习/复习。',
      estimateMinutes: 4,
      highlights: ['8 节点', '可印成一页 A4'],
      preferredFor: ['快速复习'],
      content: '根节点: SQL 注入 → 4 类攻击 + 4 类防御',
      evidenceRefs: mockEvidenceChunks.slice(0, 2),
    },
    {
      id: 'variant-mindmap-case',
      resourceType: 'mindmap',
      kind: 'case',
      title: 'SQL 注入知识图谱 · 案例版',
      tagline: '以漏洞为根',
      description: '每个真实 CVE 为根节点，向下展开成因 / 修复 / 类似案例。',
      estimateMinutes: 8,
      highlights: ['案例为根', '可关联实战'],
      preferredFor: ['实战导向'],
      content: '根节点: CVE-2023-XXXXX → 成因 / 修复 / 类似案例',
      evidenceRefs: mockEvidenceChunks,
    },
  ],
  quiz: [
    {
      id: 'variant-quiz-deep',
      resourceType: 'quiz',
      kind: 'deep',
      title: 'SQL 注入 5 题 · 深入难度',
      tagline: '含 1 代码题 + 2 高级题',
      description: '难度偏高，包含二阶注入与 WAF 绕过场景。',
      estimateMinutes: 30,
      highlights: ['代码题', '二阶注入', 'WAF 绕过'],
      preferredFor: ['进阶'],
      content: '5 题精选',
      evidenceRefs: mockEvidenceChunks,
    },
    {
      id: 'variant-quiz-easy',
      resourceType: 'quiz',
      kind: 'easy',
      title: 'SQL 注入 5 题 · 入门版',
      tagline: '5 单选 · 概念题',
      description: '全部为概念辨析单选题，适合入门。',
      estimateMinutes: 8,
      highlights: ['概念辨析', '一题一释'],
      preferredFor: ['入门'],
      content: '5 题概念辨析',
      evidenceRefs: mockEvidenceChunks.slice(0, 2),
    },
    {
      id: 'variant-quiz-case',
      resourceType: 'quiz',
      kind: 'case',
      title: 'SQL 注入 5 题 · 实战版',
      tagline: '5 题 · 全部来自真实漏洞场景',
      description: '5 道题全部来自真实漏洞案例的代码片段，需要判断风险与修复。',
      estimateMinutes: 20,
      highlights: ['真实代码片段', '判断 + 修复'],
      preferredFor: ['实战'],
      content: '5 题实战',
      evidenceRefs: mockEvidenceChunks,
    },
  ],
  lab: [
    {
      id: 'variant-lab-deep',
      resourceType: 'lab',
      kind: 'deep',
      title: 'SQL 注入 3 关靶场 · 完整版',
      tagline: 'DVWA Low / Medium / High',
      description: '从最低难度到 WAF 绕过 3 关，约 60 分钟通关。',
      estimateMinutes: 60,
      highlights: ['3 关递进', 'WAF 绕过', 'payload 提交评分'],
      preferredFor: ['深度实战'],
      content: '靶场: DVWA Low / Medium / High',
      evidenceRefs: mockEvidenceChunks,
    },
    {
      id: 'variant-lab-easy',
      resourceType: 'lab',
      kind: 'easy',
      title: 'SQL 注入 1 关靶场 · 体验版',
      tagline: 'DVWA Low · 入门一刻钟',
      description: '只保留入门关，15 分钟可完成。',
      estimateMinutes: 15,
      highlights: ['一刻钟', '步骤提示'],
      preferredFor: ['零基础'],
      content: '靶场: DVWA Low',
      evidenceRefs: mockEvidenceChunks.slice(0, 2),
    },
    {
      id: 'variant-lab-case',
      resourceType: 'lab',
      kind: 'case',
      title: 'SQL 注入靶场 · CVE 复现版',
      tagline: '复现 CVE-2023-XXXXX',
      description: '直接基于真实 CVE，搭建复现环境，需要在导师指导下完成。',
      estimateMinutes: 45,
      highlights: ['真实漏洞', '复现环境'],
      preferredFor: ['红队'],
      content: '靶场: CVE 复现',
      evidenceRefs: mockEvidenceChunks,
    },
  ],
  video: [
    {
      id: 'variant-video-deep',
      resourceType: 'video',
      kind: 'deep',
      title: '5 分钟视频 · 深入版',
      tagline: '原理动画 + 代码透视',
      description: '5 段，每段 60 秒，含 SQL 解析动画和 SQLMap 源码透视。',
      estimateMinutes: 5,
      highlights: ['原理动画', '源码透视'],
      preferredFor: ['理论'],
      content: '视频脚本: 5 段动画',
      evidenceRefs: mockEvidenceChunks,
    },
    {
      id: 'variant-video-easy',
      resourceType: 'video',
      kind: 'easy',
      title: '3 分钟视频 · 速懂版',
      tagline: '类比 + 一图',
      description: '只讲清"注入到底是什么"，3 分钟一气呵成。',
      estimateMinutes: 3,
      highlights: ['类比为主', '零代码'],
      preferredFor: ['入门'],
      content: '视频脚本: 3 段类比',
      evidenceRefs: mockEvidenceChunks.slice(0, 2),
    },
    {
      id: 'variant-video-case',
      resourceType: 'video',
      kind: 'case',
      title: '7 分钟视频 · 案例版',
      tagline: '真实 CVE 复现录屏',
      description: '基于真实 CVE，录屏复现 + 解说。',
      estimateMinutes: 7,
      highlights: ['真实复现', '录屏 + 解说'],
      preferredFor: ['实战'],
      content: '视频脚本: 真实 CVE 录屏',
      evidenceRefs: mockEvidenceChunks,
    },
  ],
  readings: [
    {
      id: 'variant-readings-deep',
      resourceType: 'readings',
      kind: 'deep',
      title: '阅读清单 · 深入版',
      tagline: '5 篇官方文档 + 论文',
      description: 'OWASP 全文 + 3 篇学术论文，体系完整。',
      estimateMinutes: 90,
      highlights: ['OWASP 全文', '学术论文'],
      preferredFor: ['理论'],
      content: '5 篇 · OWASP + 论文',
      evidenceRefs: mockEvidenceChunks,
    },
    {
      id: 'variant-readings-easy',
      resourceType: 'readings',
      kind: 'easy',
      title: '阅读清单 · 速读版',
      tagline: '3 篇精选博客',
      description: '3 篇精选博客，每篇配 30 字摘要，建议先看这版。',
      estimateMinutes: 15,
      highlights: ['速读', '摘要'],
      preferredFor: ['入门'],
      content: '3 篇博客',
      evidenceRefs: mockEvidenceChunks.slice(0, 2),
    },
    {
      id: 'variant-readings-case',
      resourceType: 'readings',
      kind: 'case',
      title: '阅读清单 · 案例版',
      tagline: '5 个 CVE 复盘',
      description: '5 篇真实 CVE 漏洞复盘文章。',
      estimateMinutes: 45,
      highlights: ['CVE 复盘'],
      preferredFor: ['实战'],
      content: '5 篇 CVE 复盘',
      evidenceRefs: mockEvidenceChunks,
    },
  ],
};

export function getResourceVariants(resourceType: ResourceType): ResourceVariant[] {
  return variantTemplates[resourceType];
}

export function buildReplayTimeline(
  resourceId: string,
  resourceType: ResourceType,
): ResourceReplayTimeline {
  const startedAt = '2026-06-14T10:00:00Z';
  const steps = [
    { id: 's1', offsetMs: 0, stage: 'request' as const, agent: 'career_planner', skill: 'RouteRequest', summary: '接收学生请求，开始路由', outcome: 'success' as const },
    { id: 's2', offsetMs: 1200, stage: 'rag' as const, agent: 'doc_archivist', skill: 'RetrieveChunks', summary: 'rag.retrieve 检索证据', detail: '命中 3 条 chunks（OWASP / DVWA / PortSwigger）', evidenceCount: 3, outcome: 'success' as const },
    { id: 's3', offsetMs: 2500, stage: 'llm' as const, agent: 'doc_archivist', skill: 'GenerateCourseDoc', summary: '讯飞星火 V3.5 流式生成', detail: 'temperature=0.4, top_p=0.9', outcome: 'success' as const },
    { id: 's4', offsetMs: 3800, stage: 'quality' as const, agent: 'outcome_evaluator', skill: 'QualityCheck', summary: 'QualityCheck 评分 0.72，未达 0.8，触发重生成', score: 0.72, outcome: 'retry' as const },
    { id: 's5', offsetMs: 5200, stage: 'llm' as const, agent: 'doc_archivist', skill: 'GenerateCourseDoc', summary: 'LLM 第二次生成（加入辩论意见）', outcome: 'success' as const },
    { id: 's6', offsetMs: 6500, stage: 'quality' as const, agent: 'outcome_evaluator', skill: 'QualityCheck', summary: 'QualityCheck 评分 0.87，通过', score: 0.87, outcome: 'success' as const },
    { id: 's7', offsetMs: 6800, stage: 'persist' as const, agent: 'doc_archivist', skill: 'PersistArtifact', summary: '写入 generated_resources + storage_objects', outcome: 'success' as const },
  ];
  return {
    resourceId,
    resourceType,
    startedAt,
    finishedAt: '2026-06-14T10:00:07Z',
    totalDurationMs: 6800,
    steps,
  };
}

export function buildAgentDebate(resourceType: ResourceType): AgentDebate {
  return {
    topic: `${resourceType.toUpperCase()} 资源质量复核`,
    versionFrom: 'v1',
    versionTo: 'v2',
    exchanges: [
      {
        id: 'd1',
        speakerAgent: 'outcome_evaluator',
        speakerLabel: '成果评估员',
        message: '你的解释里 "union-based" 没有具体例子，证据链支撑不足。',
        side: 'challenger',
        emittedAt: 0,
      },
      {
        id: 'd2',
        speakerAgent: 'doc_archivist',
        speakerLabel: '资料编辑员',
        message: '你说得对，我补一个 DVWA 实战案例，并引用 OWASP 文献。',
        side: 'defender',
        emittedAt: 2,
      },
      {
        id: 'd3',
        speakerAgent: 'outcome_evaluator',
        speakerLabel: '成果评估员',
        message: '案例可以，但请加一个修复前后的对比代码块。',
        side: 'challenger',
        emittedAt: 4,
      },
      {
        id: 'd4',
        speakerAgent: 'doc_archivist',
        speakerLabel: '资料编辑员',
        message: '已添加 vulnerable.py / safe.py 对比，并放在文档第 3 节末。',
        side: 'defender',
        emittedAt: 6,
      },
    ],
    resolution: '辩论结论：补充案例与代码对比后，质量分由 0.72 提升至 0.87。',
    diff: [
      { type: 'keep', text: '# SQL 注入入门\n\n## 1. 概念\n' },
      { type: 'remove', text: 'union-based 注入通过 UNION 语句拼接结果，常见于回显环境。\n' },
      {
        type: 'add',
        text:
          'union-based 注入通过 UNION 语句拼接结果，常见于回显环境。\n\n**示例**（DVWA Low 关）：在 id 参数后追加 ` UNION SELECT user, password FROM users-- `，即可拉出用户表。\n',
      },
      { type: 'keep', text: '\n## 2. 防御\n' },
      {
        type: 'add',
        text:
          '\n**修复前**（vulnerable.py）：\n```python\nquery = f"SELECT * FROM users WHERE id={uid}"\n```\n\n**修复后**（safe.py）：\n```python\nquery = "SELECT * FROM users WHERE id=%s"\ncursor.execute(query, (uid,))\n```\n',
      },
    ],
  };
}

export function buildResourceVersions(initialContent: string): ResourceVersion[] {
  return [
    {
      version: 1,
      createdAt: '2026-06-14T10:00:00Z',
      initiator: 'doc_archivist',
      content: initialContent,
      qualityScore: 0.72,
    },
    {
      version: 2,
      createdAt: '2026-06-14T10:08:00Z',
      initiator: 'student-self-iteration',
      prompt: '请加深，从攻击者视角讲，每个概念配一个真实漏洞案例。',
      content: `${initialContent}\n\n## 攻击者视角补充\n\n（已加入 4 个真实 CVE 案例）`,
      qualityScore: 0.86,
      diff: [
        { kind: 'keep', text: initialContent },
        { kind: 'add', text: '\n\n## 攻击者视角补充\n\n（已加入 4 个真实 CVE 案例）' },
      ],
    },
  ];
}

export function buildResourceSupervisionStream(): ResourceSupervisionEntry[] {
  const baseNames = ['李伟', '王芳', '张敏', '刘强', '陈静', '杨杰'];
  const kps = ['SQL 注入 · 盲注', 'XSS · DOM 型', 'CSRF · 防御组合', 'AES · 模式选择', 'OAuth 2.0', 'OWASP Top 10'];
  const agents = ['doc_archivist', 'topic_explorer', 'competition_advisor', 'outcome_evaluator'];
  const types: ResourceType[] = ['doc', 'ppt', 'quiz', 'lab', 'video'];
  return Array.from({ length: 18 }, (_, idx) => ({
    id: `sup-${idx}`,
    studentName: baseNames[idx % baseNames.length],
    resourceTitle: `${kps[idx % kps.length]} · ${types[idx % types.length].toUpperCase()}`,
    resourceType: types[idx % types.length],
    agent: agents[idx % agents.length],
    knowledgePoint: kps[idx % kps.length],
    qualityScore: 0.6 + (idx % 7) * 0.05,
    createdAt: new Date(Date.parse('2026-06-15T18:00:00Z') - idx * 25 * 60 * 1000).toISOString(),
  }));
}

export function defaultTeacherSeedPrompt(courseId: string): ResourceTeacherSeedPrompt {
  return {
    courseId,
    body: `## 本课程资源生成偏好\n\n- 风格：侧重红队思维\n- 避免：过于学术化表达\n- 必含：每个概念至少 1 个真实漏洞案例\n- 引用要求：优先 OWASP / PortSwigger 官方来源\n`,
    updatedAt: '2026-06-14T09:00:00Z',
    toneTags: ['红队思维', '案例驱动', '反学术化'],
  };
}
