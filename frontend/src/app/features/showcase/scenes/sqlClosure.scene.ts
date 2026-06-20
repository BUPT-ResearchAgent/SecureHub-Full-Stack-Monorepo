// Status: mock

import type { ShowcaseScene } from './types';

export const sqlClosureScene: ShowcaseScene = {
  id: 'sql-learning-loop',
  title: 'SQL 注入学习闭环',
  subtitle: 'persona → path → resources → assessment → trace 的 90 秒主线复盘',
  category: '课程学习',
  status: 'ready',
  domain: 'web-security-foundation',
  estimatedSeconds: 90,
  background: 'tech',
  steps: [
    { at: 0, narration: '演示从一句学习目标开始：学完 SQL 注入，并且能解释、修复、复盘。' },
    {
      at: 7,
      narration: 'career_planner 读取已有课程画像，确认基础薄弱点、偏好资源和目标方向。',
      highlight: { nodeIds: ['career_planner'], edgeIds: ['e1'] },
      agentMessage: { agentId: 'career_planner', text: 'persona ready · case_driven · web_security beginner' },
    },
    {
      at: 15,
      narration: 'task_orchestrator 把目标拆成 SQL 注入基础、盲注判断、参数化修复和回归验证。',
      highlight: { nodeIds: ['task_orchestrator'], edgeIds: ['e2', 'e3', 'e4'] },
      agentMessage: { agentId: 'task_orchestrator', text: 'path · 4 nodes · current kp SQL 注入基础' },
    },
    {
      at: 24,
      narration: 'doc_archivist 产出讲解文档，同时保留 evidence 引用，不把 fixture 伪装成真实生成。',
      highlight: { nodeIds: ['doc_archivist'], edgeIds: ['e8'] },
      artifact: { type: 'doc', title: 'SQL 注入基础讲解文档 · fixture preview' },
    },
    {
      at: 33,
      narration: 'topic_explorer 产出思维导图，把输入点、判断信号和防护手段串成结构图。',
      highlight: { nodeIds: ['topic_explorer'], edgeIds: ['e9'] },
      artifact: { type: 'mindmap', title: 'SQL 注入知识结构图 · fixture preview' },
    },
    {
      at: 42,
      narration: 'competition_advisor 产出练习题，覆盖单选、多选和代码修复题。',
      highlight: { nodeIds: ['competition_advisor'], edgeIds: ['e10'] },
      artifact: { type: 'quiz', title: 'SQL 注入三类题型练习 · fixture preview' },
    },
    {
      at: 51,
      narration: 'doc_archivist 继续补齐 lab 与 video_script，资源工作台可切换 7 类展示。',
      highlight: { nodeIds: ['doc_archivist'] },
      artifact: { type: 'lab', title: '参数化查询修复实验 · fixture preview' },
    },
    {
      at: 60,
      narration: 'outcome_evaluator 做质量闸门和答题评估，产出能力更新建议。',
      highlight: { nodeIds: ['outcome_evaluator'], edgeIds: ['e11'] },
      agentMessage: { agentId: 'outcome_evaluator', text: 'assessment · score 0.82 · capability delta ready' },
    },
    {
      at: 70,
      narration: 'trace 面板回放每个智能体调用：谁生成、谁校验、引用了哪些证据。',
      highlight: { nodeIds: ['task_orchestrator', 'doc_archivist', 'outcome_evaluator'] },
      artifact: { type: 'report', title: 'agent_runs trace 摘要 · 演示数据' },
    },
    {
      at: 81,
      narration: '闭环完成：课程画像回流到中枢，下一步可以延展到科研、就业和竞赛入口。',
      highlight: { nodeIds: ['career_planner'] },
      agentMessage: { agentId: 'career_planner', text: 'persona updated · next: research / career / competition' },
    },
    { at: 89, narration: '这是前端 mock 主题，只服务 7 分钟主线串场，不新增后端能力。' },
  ],
};
