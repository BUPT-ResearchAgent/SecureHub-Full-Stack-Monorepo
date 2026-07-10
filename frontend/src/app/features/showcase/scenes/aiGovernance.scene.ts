// Status: mock

import type { ShowcaseScene } from './types';

export const aiGovernanceScene: ShowcaseScene = {
  id: 'ai-governance',
  title: 'AI 安全治理框架生成',
  subtitle: '政策解读 + 舆情聚类 + 治理报告 + 判题闭环',
  category: '安全治理',
  status: 'ready',
  domain: 'ai-governance',
  estimatedSeconds: 90,
  background: 'governance',
  steps: [
    { at: 0, narration: '企业接入大模型，如何确保合规？让 9 智能体协同给出答案。' },
    {
      at: 8,
      narration: 'policy_interpreter 启动：解读 GB/T xxxxx 大模型安全标准与等保 2.0 关联条款。',
      highlight: { nodeIds: ['policy_interpreter'], edgeIds: ['e7'] },
      agentMessage: {
        agentId: 'policy_interpreter',
        text: 'ParsePolicy · 18 条核心要求 · 4 章节',
      },
    },
    {
      at: 18,
      narration: 'hot_analyst 并行启动：近 30 天 AI 安全事件聚类，识别 3 类典型场景。',
      highlight: { nodeIds: ['hot_analyst'], edgeIds: ['e6'] },
      agentMessage: {
        agentId: 'hot_analyst',
        text: 'ClusterIncidents · 提示词注入 / 数据泄露 / 模型滥用',
      },
    },
    {
      at: 28,
      narration: 'task_orchestrator 综合 2 路输入，编排治理框架生成路径。',
      highlight: { nodeIds: ['task_orchestrator'] },
    },
    {
      at: 32,
      narration: 'topic_explorer 输出治理能力图谱，job_analyst 输出对应岗位画像。',
      highlight: { nodeIds: ['topic_explorer', 'job_analyst'], edgeIds: ['e3', 'e5'] },
      agentMessage: {
        agentId: 'topic_explorer',
        text: 'GenerateMindmap · 6 大治理能力',
      },
    },
    {
      at: 42,
      narration: 'job_analyst 输出 AI 安全治理岗位需求趋势：合规 / 风控 / 红队。',
      agentMessage: {
        agentId: 'job_analyst',
        text: 'AnalyzeJobs · 治理岗位 ↑ 38% YoY',
      },
    },
    {
      at: 50,
      narration: 'doc_archivist 整合输入，生成《AI 安全治理框架报告》。',
      highlight: { nodeIds: ['doc_archivist'], edgeIds: ['e2'] },
      artifact: { type: 'report', title: '《AI 安全治理框架报告 v1.0》' },
      agentMessage: {
        agentId: 'doc_archivist',
        text: 'GenerateReport · 5 章 2.4 万字 · 引证 62 段',
      },
    },
    {
      at: 60,
      narration: 'outcome_evaluator 完成质量校验，引证完整率 98% · 政策符合度 0.92。',
      highlight: { nodeIds: ['outcome_evaluator'], edgeIds: ['e8'] },
      agentMessage: {
        agentId: 'outcome_evaluator',
        text: 'QualityCheck · 通过 · 0.92',
      },
    },
    {
      at: 70,
      narration: 'competition_advisor 顺势输出 5 道治理判题，反向校验报告理解度。',
      highlight: { nodeIds: ['competition_advisor'], edgeIds: ['e4'] },
      artifact: { type: 'quiz', title: '治理判题 5 道（多选 + 简答）' },
    },
    {
      at: 80,
      narration: 'career_planner 同步学生画像：governance / ai_security 双维度提升。',
      highlight: { nodeIds: ['career_planner'], edgeIds: ['e11'] },
      agentMessage: {
        agentId: 'career_planner',
        text: 'UpdatePersona · governance +14% · ai_security +9%',
      },
    },
    {
      at: 86,
      narration: '治理协作完成 · 9 智能体 8 次调用 · 全程留痕可追溯。',
    },
    {
      at: 89,
      narration: '从政策到代码，从舆情到岗位，安枢智梯让安全治理可计算、可教、可学。',
    },
  ],
};
