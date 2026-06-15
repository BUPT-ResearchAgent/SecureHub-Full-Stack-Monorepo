// Status: mock
// 多路径并存 / 节点难度热力 / 资源推送时间轴 / 完成率矩阵 mock 数据。

import type {
  CandidatePath,
  CandidatePathEdge,
  CandidatePathNode,
  ClassPathCompletionCell,
  ClassPathCompletionMatrix,
  PushScheduleSlot,
} from '@/lib/types/learning-path.types';

const baseNodes: Array<{
  kpId: string;
  label: string;
  mentorAgent: CandidatePathNode['mentorAgent'];
  mentorReason: string;
}> = [
  { kpId: 'sql_injection', label: 'SQL 注入基础', mentorAgent: 'doc_archivist', mentorReason: '概念问题找文档解读员' },
  { kpId: 'xss', label: 'XSS 跨站脚本', mentorAgent: 'topic_explorer', mentorReason: '实操问题找探索员' },
  { kpId: 'csrf', label: 'CSRF 请求伪造', mentorAgent: 'topic_explorer', mentorReason: '实操问题找探索员' },
  { kpId: 'upload', label: '文件上传风险', mentorAgent: 'doc_archivist', mentorReason: '概念问题找文档解读员' },
  { kpId: 'ssrf', label: 'SSRF 服务端伪造', mentorAgent: 'competition_advisor', mentorReason: '题目疑问找竞赛参谋' },
  { kpId: 'auth', label: '会话与认证', mentorAgent: 'doc_archivist', mentorReason: '概念问题找文档解读员' },
  { kpId: 'crypto', label: '加密基础', mentorAgent: 'doc_archivist', mentorReason: '概念问题找文档解读员' },
];

function diffByMastery(prereq: number): CandidatePathNode['difficulty'] {
  if (prereq >= 0.9) return 'easy';
  if (prereq >= 0.7) return 'fit';
  if (prereq >= 0.5) return 'challenge';
  return 'hard';
}

export function buildCandidatePaths(): CandidatePath[] {
  const sprintNodes: CandidatePathNode[] = baseNodes.slice(0, 5).map((node, idx) => ({
    id: `sprint-${node.kpId}`,
    label: node.label,
    knowledgePointId: node.kpId,
    status: idx === 0 ? 'active' : idx <= 1 ? 'ready' : 'locked',
    prerequisiteMastery: 0.95 - idx * 0.12,
    difficulty: diffByMastery(0.95 - idx * 0.12),
    importance: 0.65 + (5 - idx) * 0.05,
    estimateMinutes: 40 + idx * 5,
    mentorAgent: node.mentorAgent,
    mentorReason: node.mentorReason,
    scheduledFor: new Date(Date.parse('2026-06-15T20:00:00Z') + idx * 24 * 3600 * 1000).toISOString(),
  }));

  const deepNodes: CandidatePathNode[] = baseNodes.map((node, idx) => ({
    id: `deep-${node.kpId}`,
    label: node.label,
    knowledgePointId: node.kpId,
    status: idx === 0 ? 'active' : idx === 1 ? 'ready' : 'locked',
    prerequisiteMastery: 0.85 - idx * 0.09,
    difficulty: diffByMastery(0.85 - idx * 0.09),
    importance: 0.6 + (baseNodes.length - idx) * 0.05,
    estimateMinutes: 75 + idx * 8,
    mentorAgent: node.mentorAgent,
    mentorReason: node.mentorReason,
  }));

  const practiceOrder = [1, 2, 0, 3, 4, 5];
  const practiceNodes: CandidatePathNode[] = practiceOrder.map((idx, order) => {
    const node = baseNodes[idx];
    return {
      id: `practice-${node.kpId}`,
      label: node.label,
      knowledgePointId: node.kpId,
      status: order === 0 ? 'active' : order === 1 ? 'ready' : 'locked',
      prerequisiteMastery: 0.55 + Math.abs(0.5 - order / 6) * 0.4,
      difficulty: diffByMastery(0.55 + Math.abs(0.5 - order / 6) * 0.4),
      importance: 0.7,
      estimateMinutes: 55 + order * 6,
      mentorAgent: order < 3 ? 'topic_explorer' : 'competition_advisor',
      mentorReason: order < 3 ? '实战为主，找探索员' : '题目疑问找竞赛参谋',
    };
  });

  const buildEdges = (nodes: CandidatePathNode[]): CandidatePathEdge[] =>
    nodes.slice(0, -1).map((node, idx) => ({
      id: `${node.id}-${nodes[idx + 1].id}`,
      source: node.id,
      target: nodes[idx + 1].id,
    }));

  return [
    {
      id: 'path-sprint',
      strategy: 'sprint',
      label: '快速通关',
      description: '21 天每天 1 节点，覆盖 SQL/XSS/CSRF/上传/SSRF 5 个核心。',
      totalDays: 21,
      daily: '每天 1 节点 · 40-60 分钟',
      highlights: ['21 天闭环', '核心知识全覆盖', '面向竞赛演示'],
      recommendedForPersona: ['快速入门', '竞赛准备'],
      nodes: sprintNodes,
      edges: buildEdges(sprintNodes),
    },
    {
      id: 'path-deep',
      strategy: 'deep',
      label: '深度精通',
      description: '60 天慢节奏，覆盖 7 个章节，每个节点配双倍练习与复盘。',
      totalDays: 60,
      daily: '每天 0.5 节点 · 含双倍练习',
      highlights: ['60 天体系完整', '双倍练习', '强化复盘'],
      recommendedForPersona: ['理论扎实', '研究方向'],
      nodes: deepNodes,
      edges: buildEdges(deepNodes),
    },
    {
      id: 'path-practice',
      strategy: 'practice',
      label: '实战导向',
      description: '30 天先打靶场再补理论，从实战 case 反推知识点。',
      totalDays: 30,
      daily: '靶场为主 · 含 4 个 CVE 复盘',
      highlights: ['先实战', '后理论', '4 个 CVE 复盘'],
      recommendedForPersona: ['实战导向', '红队意向'],
      nodes: practiceNodes,
      edges: buildEdges(practiceNodes),
    },
  ];
}

export function buildPushTimeline(): PushScheduleSlot[] {
  const now = Date.parse('2026-06-15T18:00:00Z');
  const slots: PushScheduleSlot[] = [
    {
      id: 'slot-1',
      scheduledAt: new Date(now + 3 * 3600 * 1000).toISOString(),
      bucket: 'today',
      bucketLabel: '今晚 21:00',
      resourceType: 'doc',
      title: '《SQL 注入基础》案例版',
      agent: 'doc_archivist',
      rationale: '与你今天评估的 web_security 维度相关，AI 判断现在最适合阅读。',
      durationMinutes: 18,
      status: 'scheduled',
    },
    {
      id: 'slot-2',
      scheduledAt: new Date(now + 3 * 3600 * 1000 + 30 * 60 * 1000).toISOString(),
      bucket: 'today',
      bucketLabel: '今晚 21:30',
      resourceType: 'quiz',
      title: '5 道 SQL 注入识别题',
      agent: 'competition_advisor',
      rationale: '配套刚才的文档，趁热打铁。',
      durationMinutes: 12,
      status: 'scheduled',
    },
    {
      id: 'slot-3',
      scheduledAt: new Date(now + 15 * 3600 * 1000).toISOString(),
      bucket: 'tomorrow',
      bucketLabel: '明早 09:00',
      resourceType: 'video',
      title: '5 分钟视频 · SQL 注入原理',
      agent: 'doc_archivist',
      rationale: '上班通勤可以看的轻量视频。',
      durationMinutes: 5,
      status: 'scheduled',
    },
    {
      id: 'slot-4',
      scheduledAt: new Date(now + 27 * 3600 * 1000).toISOString(),
      bucket: 'tomorrow',
      bucketLabel: '明晚 21:00',
      resourceType: 'lab',
      title: 'DVWA Low 关靶场',
      agent: 'topic_explorer',
      rationale: '理论铺垫已完成，开始实操。',
      durationMinutes: 30,
      status: 'scheduled',
    },
    {
      id: 'slot-5',
      scheduledAt: new Date(now + 39 * 3600 * 1000).toISOString(),
      bucket: 'day_after',
      bucketLabel: '后天 09:00',
      resourceType: 'quiz',
      title: '阶段评估测试',
      agent: 'competition_advisor',
      rationale: 'SQL 注入基础阶段评估。',
      durationMinutes: 20,
      status: 'scheduled',
    },
    {
      id: 'slot-6',
      scheduledAt: new Date(now + 5 * 24 * 3600 * 1000).toISOString(),
      bucket: 'weekend',
      bucketLabel: '本周末',
      resourceType: 'reading',
      title: 'OWASP SQL 注入完整指南',
      agent: 'doc_archivist',
      rationale: '周末适合慢读官方文档。',
      durationMinutes: 60,
      status: 'scheduled',
    },
  ];
  return slots;
}

export function buildClassCompletionMatrix(): ClassPathCompletionMatrix {
  const nodeIds = ['sql_injection', 'xss', 'csrf', 'upload', 'ssrf', 'auth', 'crypto'];
  const nodeLabels = ['SQL 注入', 'XSS', 'CSRF', '文件上传', 'SSRF', '认证', '加密'];
  const studentIds = Array.from({ length: 24 }, (_, idx) => `stu-${1000 + idx}`);
  const cells: ClassPathCompletionCell[] = [];
  studentIds.forEach((studentId, sIdx) => {
    nodeIds.forEach((nodeId, nIdx) => {
      const base = nIdx < 3 ? 0.85 : nIdx < 5 ? 0.55 : 0.25;
      const noise = ((sIdx * 13 + nIdx * 7) % 9) / 30;
      const completion = Math.max(0, Math.min(1, base + noise - 0.15));
      cells.push({
        studentId,
        studentName: `学生${sIdx + 1}`,
        nodeId,
        completion,
        attemptedAt: completion > 0 ? '2026-06-14T10:00:00Z' : undefined,
      });
    });
  });
  return { nodeIds, nodeLabels, cells };
}
