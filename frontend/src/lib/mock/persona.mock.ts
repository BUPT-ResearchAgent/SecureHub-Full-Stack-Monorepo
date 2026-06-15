// Status: mock
// 画像产品化升级 mock 数据：树节点 / 挑战题库 / 班级聚类 / 教师维度。
// 纯函数化：buildXxx() 输入 seed → 输出固定结构，方便测试。

import type {
  PersonaChallengeQuestion,
  PersonaDimensionKey,
  PersonaDimensionNode,
  PersonaNarrativeSegment,
  ClassPersonaClusterPoint,
  TeacherPersonaDimension,
} from '@/lib/types/persona.types';

export const personaDimensionLabels: Record<PersonaDimensionKey, string> = {
  base_knowledge: '知识基础',
  cognitive_style: '认知风格',
  weak_points: '易错点',
  preferred_modality: '偏好学习方式',
  time_budget: '时间预算',
  target_direction: '目标方向',
  motivation: '学习动机',
};

const branchChildren: Partial<Record<PersonaDimensionKey, Array<{ key: string; label: string }>>> = {
  base_knowledge: [
    { key: 'base_knowledge.lang', label: '语言基础' },
    { key: 'base_knowledge.web', label: 'Web 基础' },
    { key: 'base_knowledge.crypto', label: '密码学基础' },
  ],
  cognitive_style: [
    { key: 'cognitive_style.pattern', label: '案例驱动' },
    { key: 'cognitive_style.theory', label: '理论推演' },
  ],
  weak_points: [
    { key: 'weak_points.sqli', label: '盲注判断' },
    { key: 'weak_points.crypto', label: '加密模式' },
  ],
  preferred_modality: [
    { key: 'preferred_modality.doc', label: '讲解文档' },
    { key: 'preferred_modality.lab', label: '实操靶场' },
    { key: 'preferred_modality.quiz', label: '错题回放' },
  ],
  time_budget: [
    { key: 'time_budget.weekly', label: '每周时长' },
    { key: 'time_budget.session', label: '单次时长' },
  ],
  target_direction: [
    { key: 'target_direction.web', label: 'Web 安全' },
    { key: 'target_direction.competition', label: '竞赛演示' },
  ],
};

export function buildPersonaTree(
  identified: Partial<Record<PersonaDimensionKey, string>>,
  challenged: Record<string, 'verified' | 'challenged'> = {},
): PersonaDimensionNode[] {
  const dimensions: PersonaDimensionKey[] = [
    'base_knowledge',
    'cognitive_style',
    'weak_points',
    'preferred_modality',
    'time_budget',
    'target_direction',
  ];
  return dimensions.map((key) => {
    const value = identified[key];
    const verifyState = challenged[key];
    const status: PersonaDimensionNode['status'] = !value
      ? 'unknown'
      : verifyState === 'verified'
      ? 'verified'
      : verifyState === 'challenged'
      ? 'challenged'
      : 'detected';
    const baseConfidence = !value ? 0.15 : verifyState === 'verified' ? 0.92 : verifyState === 'challenged' ? 0.35 : 0.62;
    const children = (branchChildren[key] ?? []).map<PersonaDimensionNode>((child, idx) => ({
      key: child.key,
      label: child.label,
      status: !value ? 'unknown' : 'detected',
      confidence: !value ? 0.1 : Math.min(0.9, baseConfidence - 0.06 - idx * 0.04),
      parentKey: key,
      evidenceMessageIds: value ? [`msg-${key}-${idx}`] : [],
    }));
    return {
      key,
      label: personaDimensionLabels[key],
      status,
      confidence: baseConfidence,
      value,
      evidenceMessageIds: value ? [`msg-${key}-root`] : [],
      children,
    };
  });
}

export const personaChallengeBank: PersonaChallengeQuestion[] = [
  {
    id: 'ch-sqli-1',
    dimension: 'weak_points',
    prompt: '在 SQL 注入中，union-based 和 boolean-based 适用场景有什么差别？请用 1-2 句话回答。',
    expectedKeywords: ['列数', '回显', '盲注', 'true', 'false'],
    difficulty: 'medium',
    rationale: '验证学生是否真正区分回显型与盲注型注入。',
  },
  {
    id: 'ch-crypto-1',
    dimension: 'base_knowledge',
    prompt: '为什么 AES 在 ECB 模式下不安全？',
    expectedKeywords: ['模式', '相同明文', '相同密文', '密文重复', '相同'],
    difficulty: 'easy',
    rationale: '验证基础密码学是否真的掌握。',
  },
  {
    id: 'ch-modality-1',
    dimension: 'preferred_modality',
    prompt: '你说自己偏好"案例驱动"，那么遇到一个新概念你会怎么开始学？',
    expectedKeywords: ['案例', '实操', '例子', '现象', '演练', '靶场'],
    difficulty: 'easy',
    rationale: '通过自由表达，识别真实学习习惯。',
  },
  {
    id: 'ch-target-1',
    dimension: 'target_direction',
    prompt: '你的目标是"红队岗位"，你认为红队和渗透测试岗位的主要差别是什么？',
    expectedKeywords: ['攻击链', '隐蔽', '战术', '横向', '后渗透', '态势'],
    difficulty: 'hard',
    rationale: '识别目标方向是否带有清晰的职业理解。',
  },
  {
    id: 'ch-time-1',
    dimension: 'time_budget',
    prompt: '你说每天 2 小时，请描述一天可执行的学习节奏（如何分块）？',
    expectedKeywords: ['番茄', '复盘', '专题', '练习', '休息', '复习'],
    difficulty: 'easy',
    rationale: '验证时间预算是否真的可执行。',
  },
];

export function pickChallengeFor(dimension: PersonaDimensionKey | string): PersonaChallengeQuestion | undefined {
  return personaChallengeBank.find((q) => q.dimension === dimension);
}

const NARRATIVE_HIGHLIGHT_RE = /\*\*(.+?)\*\*/g;

export function generatePersonaNarrative(
  studentName: string,
  identified: Partial<Record<PersonaDimensionKey, string>>,
): PersonaNarrativeSegment {
  const baseScore = identified.base_knowledge ? '中等基础（45%）' : '安全初学者（25%）';
  const modality = identified.preferred_modality
    ? '**案例驱动**'
    : '**讲解 + 实操**';
  const weakness = identified.weak_points ? '**盲注判断与参数化查询** 基础薄弱' : '尚未识别明显短板';
  const time = identified.time_budget ?? '每周 6 小时';
  const target = identified.target_direction ?? '**Web 安全基础**';

  const text =
    `**${studentName}**，${baseScore}，偏好 ${modality} 学习方式，` +
    `对 Web 漏洞敏感但 ${weakness}。每天可学 ${time}，目标进入 ${target} 方向。`;

  const highlights: string[] = [];
  let match: RegExpExecArray | null;
  const re = new RegExp(NARRATIVE_HIGHLIGHT_RE);
  while ((match = re.exec(text)) !== null) {
    highlights.push(match[1]);
  }
  return {
    text,
    highlights,
    generatedAt: new Date().toISOString(),
    dimensionKeys: Object.keys(identified) as PersonaDimensionKey[],
  };
}

export function buildClassPersonaClusters(): ClassPersonaClusterPoint[] {
  return [
    {
      id: 'cluster-case-driven',
      label: '案例驱动型',
      studentCount: 18,
      axisX: 0.55,
      axisY: 0.72,
      dominantDimension: 'cognitive_style',
      studentIds: Array.from({ length: 18 }, (_, idx) => `stu-${1000 + idx}`),
      color: '#2563eb',
    },
    {
      id: 'cluster-theory',
      label: '理论深度型',
      studentCount: 15,
      axisX: 0.78,
      axisY: 0.42,
      dominantDimension: 'base_knowledge',
      studentIds: Array.from({ length: 15 }, (_, idx) => `stu-${1018 + idx}`),
      color: '#7c3aed',
    },
    {
      id: 'cluster-practice',
      label: '实战导向型',
      studentCount: 12,
      axisX: 0.36,
      axisY: 0.81,
      dominantDimension: 'target_direction',
      studentIds: Array.from({ length: 12 }, (_, idx) => `stu-${1033 + idx}`),
      color: '#f59e0b',
    },
    {
      id: 'cluster-overview',
      label: '通识浏览型',
      studentCount: 9,
      axisX: 0.32,
      axisY: 0.28,
      dominantDimension: 'preferred_modality',
      studentIds: Array.from({ length: 9 }, (_, idx) => `stu-${1045 + idx}`),
      color: '#10b981',
    },
    {
      id: 'cluster-misc',
      label: '其他特征型',
      studentCount: 6,
      axisX: 0.68,
      axisY: 0.18,
      dominantDimension: 'motivation',
      studentIds: Array.from({ length: 6 }, (_, idx) => `stu-${1054 + idx}`),
      color: '#94a3b8',
    },
  ];
}

export function defaultTeacherDimensions(): TeacherPersonaDimension[] {
  return [
    {
      key: 'research_interest',
      label: '科研兴趣',
      description: '判断学生是否对漏洞研究、攻防博弈感兴趣，影响后续选题推送。',
      challenges: [
        {
          id: 'tch-ri-1',
          dimension: 'research_interest',
          prompt: '请举一个你觉得最有趣的安全漏洞或研究方向，并说说为什么。',
          expectedKeywords: ['有趣', '现象', '机制', '原理', '攻防'],
          difficulty: 'medium',
          rationale: '通过开放陈述识别真实兴趣。',
        },
      ],
      createdAt: '2026-06-13T10:00:00Z',
    },
  ];
}
