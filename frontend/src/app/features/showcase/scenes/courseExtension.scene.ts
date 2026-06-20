// Status: mock

import type { ShowcaseScene } from './types';

export const courseExtensionScene: ShowcaseScene = {
  id: 'course-extension-roadmap',
  title: '课程画像驱动的就业/竞赛延展',
  subtitle: 'course outcome → job / competition / research recommendation mock',
  category: '行业洞察',
  status: 'ready',
  domain: 'course-extension',
  estimatedSeconds: 90,
  background: 'governance',
  steps: [
    { at: 0, narration: 'SQL 注入学习完成后，中枢不停止在课程页，而是把画像作为延展入口。' },
    {
      at: 8,
      narration: 'career_planner 汇总课程 outcome：SQL 注入识别、参数化修复、实验复盘三类能力。',
      highlight: { nodeIds: ['career_planner'], edgeIds: ['e1'] },
      agentMessage: { agentId: 'career_planner', text: 'course outcome · web_security + secure_coding' },
    },
    {
      at: 17,
      narration: 'job_analyst 用同一画像匹配安全开发、Web 安全测试和应用安全岗位方向。',
      highlight: { nodeIds: ['job_analyst'], edgeIds: ['e5'] },
      artifact: { type: 'report', title: '岗位匹配摘要 · mock' },
      agentMessage: { agentId: 'job_analyst', text: 'job mock · AppSec / WebSec / secure coding' },
    },
    {
      at: 27,
      narration: 'competition_advisor 把学习弱点映射到 CTF Web 题单和赛前 14 天训练节奏。',
      highlight: { nodeIds: ['competition_advisor'], edgeIds: ['e4'] },
      artifact: { type: 'lab', title: 'CTF Web 备赛任务清单 · mock' },
    },
    {
      at: 37,
      narration: 'topic_explorer 推荐研究 topic：SQL 注入检测、代码审计辅助和安全教学评估。',
      highlight: { nodeIds: ['topic_explorer'], edgeIds: ['e3'] },
      artifact: { type: 'topic', title: '课程画像驱动的研究选题 · mock' },
    },
    {
      at: 47,
      narration: 'policy_interpreter 只提供合规边界提示：岗位、基金和赛事入口不宣称 real-first。',
      highlight: { nodeIds: ['policy_interpreter'], edgeIds: ['e7'] },
      agentMessage: { agentId: 'policy_interpreter', text: 'demo scope · no real fund/job/competition API' },
    },
    {
      at: 56,
      narration: 'doc_archivist 生成一页串场讲稿，把 Research、Careers、Practice、Writing 四个现有入口串起来。',
      highlight: { nodeIds: ['doc_archivist'], edgeIds: ['e2'] },
      artifact: { type: 'ppt', title: '7 分钟演示串场页 · mock' },
    },
    {
      at: 66,
      narration: 'hot_analyst 补充行业热点视角：应用安全、AI 代码审计和高校竞赛仍是演示延展点。',
      highlight: { nodeIds: ['hot_analyst'], edgeIds: ['e6'] },
      agentMessage: { agentId: 'hot_analyst', text: 'trend mock · appsec / ai audit / ctf' },
    },
    {
      at: 76,
      narration: 'outcome_evaluator 检查演示口径：只跳现有页面，不新增后端 endpoint，不改 RAG/DB。',
      highlight: { nodeIds: ['outcome_evaluator'], edgeIds: ['e8', 'e10', 'e11'] },
      agentMessage: { agentId: 'outcome_evaluator', text: 'quality gate · mock clearly labelled' },
    },
    {
      at: 86,
      narration: '最终形成一条扩展叙事：课程学习是主战场，中枢延展服务 7 分钟主线。',
    },
    { at: 89, narration: '本主题是 mock 播放场景，不接真实 Fund / Job / Competition 数据。' },
  ],
};
