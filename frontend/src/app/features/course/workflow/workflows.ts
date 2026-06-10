import type { ResourceType } from '@/lib/sse.types';
import type { AgentId, AgentMeta, NodeStatus, WorkflowDefinition, WorkflowNode } from './types';

export const AGENT_CATALOG: Record<AgentId, AgentMeta> = {
  policy_interpreter: {
    id: 'policy_interpreter',
    label: '政策法规解读',
    shortLabel: '政策',
    role: '识别合规边界与政策约束',
    tools: ['rag.retrieve', 'llm.xfyun', 'guardrails.policy'],
    color: '#64748b',
  },
  hot_analyst: {
    id: 'hot_analyst',
    label: '热点舆情研判',
    shortLabel: '热点',
    role: '补充前沿案例与拓展阅读',
    tools: ['rag.retrieve', 'mediacrawler.export', 'kg.query'],
    color: '#f97316',
  },
  job_analyst: {
    id: 'job_analyst',
    label: '招聘需求分析',
    shortLabel: '岗位',
    role: '对齐岗位技能与能力差距',
    tools: ['rag.retrieve', 'job.skill_map', 'llm.xfyun'],
    color: '#475569',
  },
  competition_advisor: {
    id: 'competition_advisor',
    label: '专业竞赛指导',
    shortLabel: '竞赛',
    role: '生成练习题与竞赛化训练',
    tools: ['rag.retrieve', 'quiz.compose', 'llm.xfyun'],
    color: '#7c3aed',
  },
  career_planner: {
    id: 'career_planner',
    label: '发展方向规划',
    shortLabel: '规划',
    role: '对话入口、画像构建与编排中枢',
    tools: ['llm.xfyun', 'kg.query', 'profile.update'],
    color: '#003399',
  },
  topic_explorer: {
    id: 'topic_explorer',
    label: '选题与实操生成',
    shortLabel: '实操',
    role: '生成实验任务与拓展阅读协同',
    tools: ['rag.retrieve', 'lab.sandbox', 'llm.xfyun'],
    color: '#0891b2',
  },
  doc_archivist: {
    id: 'doc_archivist',
    label: '文档成果归档',
    shortLabel: '文档',
    role: '生成文档、PPT、思维导图与视频脚本',
    tools: ['rag.retrieve', 'llm.xfyun', 'tts.xfyun', 'storage.write'],
    color: '#0f766e',
  },
  task_orchestrator: {
    id: 'task_orchestrator',
    label: '任务路径编排',
    shortLabel: '路径',
    role: '按画像与知识图谱拆解学习路径',
    tools: ['kg.query', 'planner.cpm', 'llm.xfyun'],
    color: '#2563eb',
  },
  outcome_evaluator: {
    id: 'outcome_evaluator',
    label: '成果质量评价',
    shortLabel: '评价',
    role: '质量闸门、效果评估与画像回流',
    tools: ['rag.retrieve', 'quality.check', 'profile.capability'],
    color: '#16a34a',
  },
};

const positions: Record<AgentId, { x: number; y: number }> = {
  career_planner: { x: 30, y: 170 },
  task_orchestrator: { x: 240, y: 170 },
  doc_archivist: { x: 470, y: 30 },
  competition_advisor: { x: 470, y: 160 },
  topic_explorer: { x: 470, y: 290 },
  hot_analyst: { x: 470, y: 420 },
  outcome_evaluator: { x: 710, y: 190 },
  policy_interpreter: { x: 245, y: 30 },
  job_analyst: { x: 245, y: 330 },
};

const agentOrder: AgentId[] = [
  'career_planner',
  'task_orchestrator',
  'doc_archivist',
  'competition_advisor',
  'topic_explorer',
  'hot_analyst',
  'outcome_evaluator',
  'policy_interpreter',
  'job_analyst',
];

const defaultSkills: Record<AgentId, string> = {
  career_planner: 'BuildLearningPersona',
  task_orchestrator: 'GenerateLearningPath',
  doc_archivist: 'GenerateCourseDoc',
  competition_advisor: 'GenerateQuiz',
  topic_explorer: 'GenerateHandsOnLab',
  hot_analyst: 'RecommendReadings',
  outcome_evaluator: 'QualityCheck',
  policy_interpreter: 'AnswerPolicyQuestion',
  job_analyst: 'SkillGapAnalysis',
};

const defaultResources: Partial<Record<AgentId, ResourceType[]>> = {
  doc_archivist: ['doc', 'ppt', 'mindmap', 'video'],
  competition_advisor: ['quiz'],
  topic_explorer: ['lab', 'readings'],
  hot_analyst: ['readings'],
};

function makeNodes(
  overrides: Partial<Record<AgentId, { skillId?: string; status?: NodeStatus; group?: string; resourceTypes?: ResourceType[] }>>,
): WorkflowNode[] {
  return agentOrder.map((agentId) => {
    const meta = AGENT_CATALOG[agentId];
    const override = overrides[agentId] ?? {};
    return {
      id: agentId,
      agentId,
      label: meta.label,
      skillId: override.skillId ?? defaultSkills[agentId],
      position: positions[agentId],
      group: override.group,
      initialStatus: override.status ?? 'idle',
      resourceTypes: override.resourceTypes ?? defaultResources[agentId],
    };
  });
}

export const workflowDefinitions: WorkflowDefinition[] = [
  {
    id: 'course_learning',
    name: '课程学习编排',
    description: '画像、路径、七类资源、质量闸门、评估与画像回流的 A3 主链路',
    defaultEntry: 'career_planner',
    nodes: makeNodes({
      career_planner: { group: '入口' },
      task_orchestrator: { group: '路径' },
      doc_archivist: { skillId: 'GenerateCourseDoc / PPT / Mindmap / Video', group: '并行资源' },
      competition_advisor: { group: '并行资源' },
      topic_explorer: { skillId: 'GenerateHandsOnLab / RecommendReadings', group: '并行资源' },
      hot_analyst: { group: '并行资源' },
      outcome_evaluator: { group: '质量闸门' },
      policy_interpreter: { status: 'skipped', group: '本轮跳过' },
      job_analyst: { status: 'skipped', group: '本轮跳过' },
    }),
    edges: [
      { id: 'career-task', source: 'career_planner', target: 'task_orchestrator', dataLabel: 'persona' },
      { id: 'task-doc', source: 'task_orchestrator', target: 'doc_archivist', dataLabel: 'resource_plan' },
      { id: 'task-quiz', source: 'task_orchestrator', target: 'competition_advisor', dataLabel: 'quiz_goal' },
      { id: 'task-topic', source: 'task_orchestrator', target: 'topic_explorer', dataLabel: 'lab_goal' },
      { id: 'task-hot', source: 'task_orchestrator', target: 'hot_analyst', dataLabel: 'reading_query' },
      { id: 'task-policy', source: 'task_orchestrator', target: 'policy_interpreter', dataLabel: '本轮跳过' },
      { id: 'task-job', source: 'task_orchestrator', target: 'job_analyst', dataLabel: '本轮跳过' },
      { id: 'doc-outcome', source: 'doc_archivist', target: 'outcome_evaluator', dataLabel: '4 类资源' },
      { id: 'quiz-outcome', source: 'competition_advisor', target: 'outcome_evaluator', dataLabel: '题目' },
      { id: 'topic-outcome', source: 'topic_explorer', target: 'outcome_evaluator', dataLabel: '实操/阅读' },
      { id: 'hot-outcome', source: 'hot_analyst', target: 'outcome_evaluator', dataLabel: '热点阅读' },
      { id: 'outcome-career', source: 'outcome_evaluator', target: 'career_planner', dataLabel: '画像回流' },
    ],
  },
  {
    id: 'tutor_routing',
    name: '智能辅导路由',
    description: '学习助手识别意图后路由到政策、热点、实操或文档智能体回答',
    defaultEntry: 'career_planner',
    nodes: makeNodes({
      career_planner: { skillId: 'RouteTutorQuestion', group: '路由' },
      policy_interpreter: { skillId: 'AnswerPolicyQuestion', group: '候选回答' },
      hot_analyst: { skillId: 'AnswerHotQuestion', group: '候选回答' },
      topic_explorer: { skillId: 'AnswerLabQuestion', group: '候选回答' },
      doc_archivist: { skillId: 'AnswerCourseDocQuestion', group: '候选回答' },
      outcome_evaluator: { skillId: 'QualityCheck', group: '质量闸门' },
      task_orchestrator: { status: 'skipped', group: '本轮跳过' },
      competition_advisor: { status: 'skipped', group: '本轮跳过' },
      job_analyst: { status: 'skipped', group: '本轮跳过' },
    }),
    edges: [
      { id: 'career-policy', source: 'career_planner', target: 'policy_interpreter', dataLabel: '合规类' },
      { id: 'career-hot', source: 'career_planner', target: 'hot_analyst', dataLabel: '热点类' },
      { id: 'career-topic', source: 'career_planner', target: 'topic_explorer', dataLabel: '实操类' },
      { id: 'career-doc', source: 'career_planner', target: 'doc_archivist', dataLabel: '概念类' },
      { id: 'policy-outcome', source: 'policy_interpreter', target: 'outcome_evaluator', dataLabel: '答案' },
      { id: 'hot-outcome', source: 'hot_analyst', target: 'outcome_evaluator', dataLabel: '答案' },
      { id: 'topic-outcome', source: 'topic_explorer', target: 'outcome_evaluator', dataLabel: '答案' },
      { id: 'doc-outcome', source: 'doc_archivist', target: 'outcome_evaluator', dataLabel: '答案' },
    ],
  },
  {
    id: 'resource_generate',
    name: '资源生成流水线',
    description: '围绕当前知识点并行生产文档、PPT、导图、题目、实操、视频与阅读',
    defaultEntry: 'task_orchestrator',
    nodes: makeNodes({
      career_planner: { skillId: 'RecommendResources', group: '入口' },
      task_orchestrator: { skillId: 'GenerateResourcePlan', group: '入口' },
      doc_archivist: { skillId: 'GenerateCourseDoc / PPT / Mindmap / Video', group: '并行资源' },
      competition_advisor: { group: '并行资源' },
      topic_explorer: { skillId: 'GenerateHandsOnLab / RecommendReadings', group: '并行资源' },
      hot_analyst: { group: '并行资源' },
      outcome_evaluator: { group: '质量闸门' },
      policy_interpreter: { status: 'skipped', group: '本轮跳过' },
      job_analyst: { status: 'skipped', group: '本轮跳过' },
    }),
    edges: [
      { id: 'career-task', source: 'career_planner', target: 'task_orchestrator', dataLabel: '偏好' },
      { id: 'task-doc', source: 'task_orchestrator', target: 'doc_archivist', dataLabel: '格式矩阵' },
      { id: 'task-quiz', source: 'task_orchestrator', target: 'competition_advisor', dataLabel: '练习目标' },
      { id: 'task-topic', source: 'task_orchestrator', target: 'topic_explorer', dataLabel: '实操目标' },
      { id: 'task-hot', source: 'task_orchestrator', target: 'hot_analyst', dataLabel: '拓展主题' },
      { id: 'doc-outcome', source: 'doc_archivist', target: 'outcome_evaluator', dataLabel: '资源包' },
      { id: 'quiz-outcome', source: 'competition_advisor', target: 'outcome_evaluator', dataLabel: '题目' },
      { id: 'topic-outcome', source: 'topic_explorer', target: 'outcome_evaluator', dataLabel: '实验' },
      { id: 'hot-outcome', source: 'hot_analyst', target: 'outcome_evaluator', dataLabel: '阅读' },
    ],
  },
  {
    id: 'assessment_run',
    name: '学习效果评估',
    description: '练习题提交后进入评估、能力画像更新和下一轮推荐',
    defaultEntry: 'competition_advisor',
    nodes: makeNodes({
      competition_advisor: { skillId: 'GenerateQuiz', group: '题目' },
      outcome_evaluator: { skillId: 'RunAssessment / UpdateCapability', group: '评估' },
      career_planner: { skillId: 'UpdatePersona', group: '回流' },
      task_orchestrator: { skillId: 'AdjustLearningPath', group: '回流' },
      doc_archivist: { status: 'skipped', group: '本轮跳过' },
      topic_explorer: { status: 'skipped', group: '本轮跳过' },
      hot_analyst: { status: 'skipped', group: '本轮跳过' },
      policy_interpreter: { status: 'skipped', group: '本轮跳过' },
      job_analyst: { status: 'skipped', group: '本轮跳过' },
    }),
    edges: [
      { id: 'quiz-outcome', source: 'competition_advisor', target: 'outcome_evaluator', dataLabel: 'answers' },
      { id: 'outcome-career', source: 'outcome_evaluator', target: 'career_planner', dataLabel: 'capability_delta' },
      { id: 'career-task', source: 'career_planner', target: 'task_orchestrator', dataLabel: 'next_path' },
    ],
  },
];

export const workflowById = Object.fromEntries(
  workflowDefinitions.map((workflow) => [workflow.id, workflow]),
) as Record<WorkflowDefinition['id'], WorkflowDefinition>;
