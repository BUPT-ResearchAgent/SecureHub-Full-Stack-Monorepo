import type { AssessmentReport, LearningPath, LearningPersona, ResourceItem } from './types';
import { mockEvidenceChunks } from '@/lib/mock/evidence.mock';
import { mockResourceContent, mockResourceTitle } from '@/lib/mock/resources.mock';
import { demoCurrentKpId } from '@/lib/mock/storyline';

export const mockPersona: LearningPersona = {
  userId: 'demo-user',
  completeness: 0.86,
  updatedAt: '2026-06-05T00:00:00Z',
  dimensions: {
    base_knowledge: '了解 Python 基础语法和少量 HTTP 请求概念',
    cognitive_style: '先看案例，再做实操复盘',
    weak_points: 'SQL 注入判断流程和参数化查询边界',
    preferred_modality: '讲解文档、实操案例、练习题',
    time_budget: '每周 6 小时',
    target_direction: 'Web 安全入门与竞赛演示',
    motivation: '围绕软件杯 A3 主线完成可演示学习闭环',
  },
};

export const mockLearningPath: LearningPath = {
  courseId: '00000000-0000-0000-0000-000000000101',
  nodes: [
    { id: demoCurrentKpId, label: 'SQL 注入基础', status: 'active', priority: 1 },
    { id: 'xss', label: 'XSS 跨站脚本', status: 'ready', priority: 2 },
    { id: 'csrf', label: 'CSRF 请求伪造', status: 'ready', priority: 3 },
    { id: 'upload', label: '文件上传风险', status: 'locked', priority: 4 },
    { id: 'ssrf', label: 'SSRF 服务端请求伪造', status: 'locked', priority: 5 },
  ],
  edges: [
    { id: 'sql_injection-xss', source: demoCurrentKpId, target: 'xss' },
    { id: 'xss-csrf', source: 'xss', target: 'csrf' },
    { id: 'csrf-upload', source: 'csrf', target: 'upload' },
    { id: 'upload-ssrf', source: 'upload', target: 'ssrf' },
  ],
  milestones: [
    { id: 'm1', title: '完成 SQL 注入判断流程', week: 1 },
    { id: 'm2', title: '完成参数化查询修复实验', week: 2 },
  ],
};

const mockResourceTypes = [
  'doc',
  'ppt',
  'mindmap',
  'quiz',
  'lab',
  'video',
  'readings',
] as const;

export const mockResources: ResourceItem[] = mockResourceTypes.map((type) => ({
  id: `res-${type}-sqli`,
  type,
  title: mockResourceTitle[type],
  status: 'ready',
  content: mockResourceContent[type],
  evidenceRefs: mockEvidenceChunks,
}));

export const mockAssessment: AssessmentReport = {
  score: 0.82,
  scoreVector: { sql_injection: 0.52, secure_coding: 0.44, evidence: 0.48 },
  feedback: ['参数化查询理解较好，建议继续补充布尔盲注与时间盲注判断练习。', '完成一次修复前后对比复盘，可以提升实操维度置信度。'],
  updatedProfile: { weak_points: '布尔盲注与时间盲注判断步骤' },
  updatedCapabilities: [
    { dimension: 'SQL 注入识别', score: 0.52, confidence: 0.7, evidence_count: 4 },
    { dimension: '安全编码', score: 0.44, confidence: 0.62, evidence_count: 3 },
    { dimension: '实操复盘', score: 0.4, confidence: 0.58, evidence_count: 2 },
  ],
};
