// Status: mock
// 学习效果评估产品化升级 mock：隐式信号 / 能力时间轴 / 病灶分析 / 同伴对比 / 效果预测 / 班级健康 / 风险预警。

import type {
  AtRiskStudent,
  CapabilityTimeline,
  ClassHealth,
  ImplicitAssessment,
  LearningForecast,
  PeerComparison,
  WeaknessDiagnosis,
} from '@/lib/types/assessment.types';

export function buildImplicitAssessment(explicitScore: number): ImplicitAssessment {
  const signals = [
    {
      kind: 'question_depth' as const,
      label: '提问深度',
      description: '近 24h 提问含 4 个关键词（参数化查询 / 二阶 / WAF / 白名单）',
      score: 0.84,
      weight: 0.25,
      evidenceLabels: ['提问 "参数化查询能否完全防注入"', '追问二阶注入触发条件'],
    },
    {
      kind: 'dwell_time' as const,
      label: '阅读停留',
      description: '《OWASP SQL Injection》一篇平均停留 9.2 分钟',
      score: 0.79,
      weight: 0.2,
      evidenceLabels: ['9.2 min / 一篇', '高于全班均值 6.4 min'],
    },
    {
      kind: 'reading_order' as const,
      label: '学习顺序',
      description: '按 AI 推荐顺序阅读 doc → quiz → lab，未跳过任一步',
      score: 0.88,
      weight: 0.15,
      evidenceLabels: ['完整 4 步序列', '无跳读行为'],
    },
    {
      kind: 'revisit_count' as const,
      label: '回访次数',
      description: '关键文档回看 3 次，最长间隔 12h',
      score: 0.76,
      weight: 0.15,
      evidenceLabels: ['关键章节 ×3', '随时回查'],
    },
    {
      kind: 'lab_attempts' as const,
      label: '实操尝试',
      description: 'DVWA Low 关一次通过；Medium 关 2 次尝试',
      score: 0.7,
      weight: 0.25,
      evidenceLabels: ['Low ×1', 'Medium ×2'],
    },
  ];
  const total = signals.reduce((sum, s) => sum + s.score * s.weight, 0);
  return {
    totalScore: total,
    signals,
    generatedAt: new Date().toISOString(),
    diffFromExplicit: total - explicitScore,
  };
}

export function buildCapabilityTimeline(): CapabilityTimeline {
  const dimensions = ['web_security', 'crypto', 'system_security', 'pentest'];
  const points = [
    {
      recordedAt: '2026-05-15T00:00:00Z',
      dimensions: { web_security: 0.25, crypto: 0.12, system_security: 0.18, pentest: 0.1 },
      highlightEvents: [
        { title: '完成新生入门测试', description: '识别基础知识缺口', dimension: 'web_security', delta: 0.25 },
      ],
    },
    {
      recordedAt: '2026-05-25T00:00:00Z',
      dimensions: { web_security: 0.34, crypto: 0.18, system_security: 0.22, pentest: 0.15 },
      highlightEvents: [
        { title: '完成 SQL 注入文档阅读', description: '+9% web_security', dimension: 'web_security', delta: 0.09 },
      ],
    },
    {
      recordedAt: '2026-06-05T00:00:00Z',
      dimensions: { web_security: 0.48, crypto: 0.25, system_security: 0.32, pentest: 0.22 },
      highlightEvents: [
        { title: '完成 DVWA Low 实操', description: '+14% web_security · 实操经验首次入账', dimension: 'web_security', delta: 0.14 },
      ],
    },
    {
      recordedAt: '2026-06-12T00:00:00Z',
      dimensions: { web_security: 0.62, crypto: 0.31, system_security: 0.42, pentest: 0.31 },
      highlightEvents: [
        { title: 'XSS 节点评估 82%', description: '+14% web_security', dimension: 'web_security', delta: 0.14 },
        { title: '密码学评估 42%', description: '回归至 31%（修正）', dimension: 'crypto', delta: -0.11 },
      ],
    },
    {
      recordedAt: '2026-06-15T00:00:00Z',
      dimensions: { web_security: 0.71, crypto: 0.36, system_security: 0.45, pentest: 0.38 },
      highlightEvents: [
        { title: '完成 SQL 注入综合评估', description: '+9% web_security · 进入熟练阶段', dimension: 'web_security', delta: 0.09 },
      ],
    },
  ];
  return { userId: 'demo-user', dimensions, points };
}

export function buildWeaknessDiagnosis(): WeaknessDiagnosis {
  return {
    userId: 'demo-user',
    generatedAt: new Date().toISOString(),
    meta: {
      incorrectCount: 5,
      coveredDimensions: ['web_security'],
    },
    rootCauses: [
      {
        id: 'rc-1',
        topic: '二阶注入概念混淆',
        affectedItemIds: ['q-003', 'q-007', 'q-011'],
        evidenceSnippet:
          '"二阶注入需要 payload 在数据库中持久化，二次取出时才被解析" —— 你的回答把它与盲注混淆。',
        suggestedResource: {
          type: 'doc',
          title: '《SQL 注入进阶 - 二阶注入篇》',
          agent: 'doc_archivist',
        },
        exerciseTitle: '二阶注入专项 5 题',
        exerciseCount: 5,
      },
      {
        id: 'rc-2',
        topic: '参数化查询白名单边界',
        affectedItemIds: ['q-009', 'q-015'],
        evidenceSnippet: '"我以为参数化能防一切注入" —— 实际上字段名 / 表名仍需白名单。',
        suggestedResource: {
          type: 'lab',
          title: '参数化 + 白名单组合实操',
          agent: 'topic_explorer',
        },
        exerciseTitle: '参数化边界 3 题',
        exerciseCount: 3,
      },
    ],
  };
}

export function buildPeerComparison(): PeerComparison {
  const dimensions = [
    { dimension: 'xss_defense', label: 'XSS 防护', selfScore: 0.78, classMedian: 0.62, betterThanRatio: 0.8 },
    { dimension: 'csrf_defense', label: 'CSRF', selfScore: 0.45, classMedian: 0.6, betterThanRatio: 0.35 },
    { dimension: 'sql_injection', label: 'SQL 注入', selfScore: 0.72, classMedian: 0.58, betterThanRatio: 0.74 },
    { dimension: 'auth', label: '认证', selfScore: 0.55, classMedian: 0.55, betterThanRatio: 0.5 },
  ];
  const overall = 0.7;
  return {
    userId: 'demo-user',
    generatedAt: new Date().toISOString(),
    dimensions,
    overallPercentile: overall,
    summary: '整体安全意识在班级前 30% 🏆',
  };
}

export function buildLearningForecast(): LearningForecast {
  const historical = [
    { recordedAt: '2026-05-25', expected: 0.34, lower: 0.34, upper: 0.34 },
    { recordedAt: '2026-06-01', expected: 0.42, lower: 0.42, upper: 0.42 },
    { recordedAt: '2026-06-08', expected: 0.55, lower: 0.55, upper: 0.55 },
    { recordedAt: '2026-06-15', expected: 0.71, lower: 0.71, upper: 0.71 },
  ];
  const forecast = [
    { recordedAt: '2026-06-21', expected: 0.78, lower: 0.74, upper: 0.83 },
    { recordedAt: '2026-06-27', expected: 0.84, lower: 0.78, upper: 0.9 },
    { recordedAt: '2026-07-04', expected: 0.9, lower: 0.83, upper: 0.96 },
    { recordedAt: '2026-07-11', expected: 0.93, lower: 0.86, upper: 0.98 },
  ];
  return {
    userId: 'demo-user',
    dimension: 'web_security',
    dimensionLabel: 'Web 安全主线',
    targetMastery: 0.9,
    expectedDays: 12,
    confidenceLowDays: 9,
    confidenceHighDays: 15,
    acceleration: {
      extraMinutesPerDay: 30,
      shavedDays: 3,
    },
    historical,
    forecast,
  };
}

export function buildClassHealth(): ClassHealth {
  return {
    overall: 82,
    metrics: [
      { key: 'activity', label: '活跃度', score: 86 },
      { key: 'completion', label: '完成率', score: 78 },
      { key: 'assessment_avg', label: '评估均分', score: 82 },
      { key: 'question_quality', label: '提问质量', score: 79 },
      { key: 'resource_usage', label: '资源使用', score: 85 },
    ],
    trend: Array.from({ length: 14 }, (_, idx) => ({
      recordedAt: new Date(Date.parse('2026-06-02T00:00:00Z') + idx * 86400 * 1000).toISOString(),
      score: 72 + Math.sin(idx / 2) * 4 + idx * 0.6,
    })),
    classification: 'healthy',
  };
}

export function buildAtRiskStudents(): AtRiskStudent[] {
  return [
    {
      studentId: 'stu-1006',
      studentName: '杨杰',
      avatar: '🐰',
      signals: [
        { kind: 'inactive', label: '连续未上线', detail: '已 3 天未与学习助手对话' },
      ],
      level: 'medium',
      lastActivityAt: '2026-06-12T20:00:00Z',
      suggestedAction: '发起一次主动关心私信',
    },
    {
      studentId: 'stu-1018',
      studentName: '李伟',
      avatar: '🦊',
      signals: [
        { kind: 'declining', label: '评估连续下滑', detail: '最近 3 次评估：72 → 65 → 54' },
        { kind: 'low_engagement', label: '资源停留过短', detail: '关键文档平均停留 < 2 min' },
      ],
      level: 'high',
      lastActivityAt: '2026-06-15T08:00:00Z',
      suggestedAction: '约 15 分钟一对一沟通；插入辅助节点',
    },
    {
      studentId: 'stu-1032',
      studentName: '王芳',
      avatar: '🐼',
      signals: [
        { kind: 'silent_struggle', label: '卡壳但不求助', detail: 'XSS 节点连续 3 次提交错误，无提问' },
      ],
      level: 'medium',
      lastActivityAt: '2026-06-15T16:00:00Z',
      suggestedAction: 'AI 已自动推送辅助资源，建议加教师评语',
    },
  ];
}
