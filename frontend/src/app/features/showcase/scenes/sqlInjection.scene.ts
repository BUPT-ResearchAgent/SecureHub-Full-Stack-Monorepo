// Status: mock

import type { ShowcaseScene } from './types';

export const sqlInjectionScene: ShowcaseScene = {
  id: 'sql-injection',
  title: 'SQL 注入完整学习路径',
  subtitle: '9 智能体协作 · 90 秒回放学生从入门到掌握',
  category: '课程学习',
  status: 'ready',
  domain: 'web-security-foundation',
  estimatedSeconds: 90,
  background: 'tech',
  steps: [
    { at: 0, narration: '学生发起学习请求：「想搞懂 SQL 注入是什么？」' },
    {
      at: 8,
      narration: 'career_planner 接收意图：识别为入门级学习目标，启动课程编排。',
      highlight: { nodeIds: ['career_planner'], edgeIds: ['e1'] },
      agentMessage: {
        agentId: 'career_planner',
        text: '识别为入门学习意图 · 调用 BuildLearningPersona',
      },
    },
    {
      at: 15,
      narration: 'task_orchestrator 启动：基于知识图谱拆解为 5 个节点的学习路径。',
      highlight: { nodeIds: ['task_orchestrator'] },
      agentMessage: {
        agentId: 'task_orchestrator',
        text: '生成 5 节点学习路径 · 关联 412 个 chunks',
      },
    },
    {
      at: 22,
      narration: '4 个生产者并行启动，分别产出讲解文档 / 思维导图 / 练习题 / 实操实验。',
      highlight: { nodeIds: ['doc_archivist', 'topic_explorer', 'competition_advisor'], edgeIds: ['e2', 'e3', 'e4'] },
    },
    {
      at: 30,
      narration: 'doc_archivist 完成《SQL 注入基础》讲解文档。',
      artifact: { type: 'doc', title: '《SQL 注入基础》讲解文档' },
      agentMessage: { agentId: 'doc_archivist', text: 'GenerateCourseDoc · 4 章 1.8 万字' },
    },
    {
      at: 38,
      narration: 'topic_explorer 输出思维导图，串起 12 个核心知识节点。',
      artifact: { type: 'mindmap', title: 'SQL 注入知识图谱' },
      agentMessage: { agentId: 'topic_explorer', text: 'GenerateMindmap · 12 节点' },
    },
    {
      at: 46,
      narration: 'competition_advisor 生成 8 道练习题：4 单选 + 2 多选 + 2 代码。',
      artifact: { type: 'quiz', title: '8 道练习题（含代码题）' },
      agentMessage: { agentId: 'competition_advisor', text: 'GenerateQuiz · 平均质量 0.86' },
    },
    {
      at: 54,
      narration: 'doc_archivist 同时生成动手实验脚本，可直接在靶场环境跑通。',
      highlight: { nodeIds: ['doc_archivist'] },
      artifact: { type: 'lab', title: 'DVWA SQL 注入实验脚本' },
    },
    {
      at: 62,
      narration: 'outcome_evaluator 闸门：对所有产出进行质量校验。',
      highlight: { nodeIds: ['outcome_evaluator'], edgeIds: ['e8', 'e9', 'e10'] },
      agentMessage: {
        agentId: 'outcome_evaluator',
        text: 'quality_check · 通过 4/4 · 平均 0.86',
      },
    },
    {
      at: 72,
      narration: 'career_planner 回收学生画像：能力维度 web_security +12%，pentest +8%。',
      highlight: { nodeIds: ['career_planner'], edgeIds: ['e11'] },
      agentMessage: { agentId: 'career_planner', text: 'UpdatePersona · web_security +12%' },
    },
    {
      at: 82,
      narration: '路径完成 · 推荐下一站「XSS 跨站脚本」，巩固 Web 攻击面知识网络。',
    },
    {
      at: 89,
      narration: '本次协作端到端耗时 86 秒 · 9 智能体调用 7 次 · 引用证据 38 段。',
    },
  ],
};
